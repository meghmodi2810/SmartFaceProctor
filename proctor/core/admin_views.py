from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
import json
import csv

from .models import User, Exam, Question, Submission, Violation, BugReport, PasswordResetOTP, ExamAssignment
from .Modules.send_email_using_sheets import SmartFaceProctorMailer


def admin_required(view_func):
    """Decorator to ensure only admin users can access admin views"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        if request.user.role != 'Admin':
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_login(request):
    """Custom admin login view"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.role == 'Admin':
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Access denied. Admin privileges required.')
        else:
            messages.error(request, 'Invalid credentials')
        return redirect('admin_login')
    
    return render(request, 'admin_login.html')


@admin_required
def admin_dashboard(request):
    """Main admin dashboard with statistics"""
    # Get statistics
    total_users = User.objects.count()
    total_students = User.objects.filter(role='Student').count()
    total_faculty = User.objects.filter(role='Faculty').count()
    total_admins = User.objects.filter(role='Admin').count()
    
    total_exams = Exam.objects.count()
    active_exams = Exam.objects.filter(
        date__lte=timezone.now(),
        date__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    total_submissions = Submission.objects.count()
    total_violations = Violation.objects.count()
    open_bug_reports = BugReport.objects.filter(status='open').count()
    
    # Recent activities
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_exams = Exam.objects.order_by('-date')[:5]
    recent_violations = Violation.objects.order_by('-timestamp')[:5]
    recent_bugs = BugReport.objects.order_by('-created_at')[:5]
    
    context = {
        'admin': request.user,
        'stats': {
            'total_users': total_users,
            'total_students': total_students,
            'total_faculty': total_faculty,
            'total_admins': total_admins,
            'total_exams': total_exams,
            'active_exams': active_exams,
            'total_submissions': total_submissions,
            'total_violations': total_violations,
            'open_bug_reports': open_bug_reports,
        },
        'recent_users': recent_users,
        'recent_exams': recent_exams,
        'recent_violations': recent_violations,
        'recent_bugs': recent_bugs,
    }
    return render(request, 'admindash.html', context)


@admin_required
def admin_users(request):
    """Manage users"""
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    
    users = User.objects.all()
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    users = users.order_by('-date_joined')
    
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'admin': request.user,
        'users': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'roles': User.ROLE_CHOICES,
    }
    return render(request, 'admin_users.html', context)


@admin_required
def admin_user_detail(request, user_id):
    """View/Edit user details"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update':
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.role = request.POST.get('role', '')
            user.is_active = request.POST.get('is_active') == 'on'
            user.save()
            messages.success(request, f'User {user.username} updated successfully.')
        
        elif action == 'reset_password':
            new_password = request.POST.get('new_password')
            if new_password:
                user.set_password(new_password)
                user.save()
                messages.success(request, f'Password reset for {user.username}.')
        
        elif action == 'delete':
            username = user.username
            user.delete()
            messages.success(request, f'User {username} deleted successfully.')
            return redirect('admin_users')
    
    # Get user's submissions and violations
    submissions = Submission.objects.filter(student=user).order_by('-submitted_on')[:10]
    violations = Violation.objects.filter(student=user).order_by('-timestamp')[:10]
    exams_created = Exam.objects.filter(created_by=user).order_by('-date')[:10]
    
    context = {
        'admin': request.user,
        'user_obj': user,
        'submissions': submissions,
        'violations': violations,
        'exams_created': exams_created,
        'roles': User.ROLE_CHOICES,
    }
    return render(request, 'admin_user_detail.html', context)


@admin_required
def admin_user_create(request):
    """Create new user"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        role = request.POST.get('role')
        password = request.POST.get('password')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
                return redirect('admin_users')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists.')
                return redirect('admin_users')
            
            # Create new user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=is_active
            )
            
            messages.success(request, f'User {username} created successfully.')
            return redirect('admin_users')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('admin_users')
    
    return redirect('admin_users')


@admin_required
def admin_create_user(request):
    """Create new user"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        role = request.POST.get('role')
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role
            )
            messages.success(request, f'User {username} created successfully.')
            return redirect('admin_user_detail', user_id=user.id)
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
    
    context = {
        'admin': request.user,
        'roles': User.ROLE_CHOICES,
    }
    return render(request, 'admin_create_user.html', context)


@admin_required
def admin_import_users(request):
    """Import users from CSV"""
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if csv_file:
            try:
                mailer = SmartFaceProctorMailer()
                mailer.import_users_from_csv(csv_file)
                messages.success(request, 'Users imported successfully.')
            except Exception as e:
                messages.error(request, f'Error importing users: {str(e)}')
    
    return render(request, 'admin_import_users.html')


@admin_required
def admin_exams(request):
    """Manage exams"""
    search_query = request.GET.get('search', '')
    
    exams = Exam.objects.select_related('created_by').all()
    
    if search_query:
        exams = exams.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(created_by__username__icontains=search_query)
        )
    
    exams = exams.order_by('-date')
    
    paginator = Paginator(exams, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'admin': request.user,
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'admin_exams.html', context)


@admin_required
def admin_exam_create(request):
    """Create new exam"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        date = request.POST.get('date')
        time = request.POST.get('time')
        duration_minutes = request.POST.get('duration_minutes')
        sheet_url = request.POST.get('sheet_url', '').strip()
        
        try:
            # Combine date and time
            from datetime import datetime
            exam_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            
            # Create the exam
            exam = Exam.objects.create(
                title=title,
                description=description,
                date=exam_datetime,
                duration_minutes=int(duration_minutes),
                created_by=request.user,
                sheet_url=sheet_url if sheet_url else None
            )
            
            messages.success(request, f'Exam "{title}" created successfully.')
            return redirect('admin_exam_detail', exam_id=exam.id)
            
        except ValueError as e:
            messages.error(request, 'Invalid date/time format or duration.')
        except Exception as e:
            messages.error(request, f'Error creating exam: {str(e)}')
    
    return redirect('admin_exams')


@admin_required
def admin_exam_detail(request, exam_id):
    """View/Edit exam details"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update':
            exam.title = request.POST.get('title', '')
            exam.description = request.POST.get('description', '')
            exam.duration_minutes = int(request.POST.get('duration_minutes', 0))
            exam.sheet_url = request.POST.get('sheet_url', '')
            exam.save()
            messages.success(request, f'Exam {exam.title} updated successfully.')
        
        elif action == 'delete':
            title = exam.title
            exam.delete()
            messages.success(request, f'Exam {title} deleted successfully.')
            return redirect('admin_exams')
    
    # Get exam statistics
    questions = Question.objects.filter(exam=exam)
    submissions = Submission.objects.filter(exam=exam).order_by('-submitted_on')
    violations = Violation.objects.filter(exam=exam).order_by('-timestamp')
    
    context = {
        'admin': request.user,
        'exam': exam,
        'questions': questions,
        'submissions': submissions,
        'violations': violations,
    }
    return render(request, 'admin_exam_detail.html', context)


@admin_required
def admin_exam_assignments(request, exam_id):
    """Manage student assignments for a specific exam"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Get search and filter parameters
    search_query = request.GET.get('search', '').strip()
    assignment_filter = request.GET.get('assignment_status', 'all')
    
    # Base queryset for students
    students_query = User.objects.filter(role='Student')
    
    # Apply search filter
    if search_query:
        students_query = students_query.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Get assigned student IDs for this exam
    assigned_student_ids = ExamAssignment.objects.filter(
        exam=exam, is_active=True
    ).values_list('student_id', flat=True)
    
    # Apply assignment status filter
    if assignment_filter == 'assigned':
        students_query = students_query.filter(id__in=assigned_student_ids)
    elif assignment_filter == 'unassigned':
        students_query = students_query.exclude(id__in=assigned_student_ids)
    
    # Paginate students
    paginator = Paginator(students_query, 20)
    page_number = request.GET.get('page')
    students = paginator.get_page(page_number)
    
    # Add assignment status to each student
    for student in students:
        student.is_assigned = student.id in assigned_student_ids
    
    # Get current assignments for display
    current_assignments = ExamAssignment.objects.filter(
        exam=exam, is_active=True
    ).select_related('student').order_by('-assigned_at')
    
    # Handle POST requests for assignment actions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'assign_selected':
            student_ids = request.POST.getlist('student_ids')
            assigned_count = 0
            
            for student_id in student_ids:
                student = get_object_or_404(User, id=student_id, role='Student')
                assignment, created = ExamAssignment.objects.get_or_create(
                    exam=exam,
                    student=student,
                    defaults={
                        'assigned_by': request.user,
                        'is_active': True
                    }
                )
                if created:
                    assigned_count += 1
            
            messages.success(request, f'Successfully assigned {assigned_count} students to the exam.')
            
        elif action == 'assign_single':
            student_id = request.POST.get('student_id')
            student = get_object_or_404(User, id=student_id, role='Student')
            assignment, created = ExamAssignment.objects.get_or_create(
                exam=exam,
                student=student,
                defaults={
                    'assigned_by': request.user,
                    'is_active': True
                }
            )
            if created:
                messages.success(request, f'Successfully assigned {student.username} to the exam.')
            else:
                messages.info(request, f'{student.username} is already assigned to this exam.')
                
        elif action == 'remove_assignment':
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(ExamAssignment, id=assignment_id, exam=exam)
            student_name = assignment.student.username
            assignment.delete()
            messages.success(request, f'Removed {student_name} from the exam.')
        
        # Mark exam as selective if it has assignments
        if ExamAssignment.objects.filter(exam=exam, is_active=True).exists():
            exam.is_selective = True
            exam.save()
        
        return redirect('admin_exam_assignments', exam_id=exam.id)
    
    # Calculate statistics
    total_students = User.objects.filter(role='Student').count()
    assigned_count = len(assigned_student_ids)
    unassigned_count = total_students - assigned_count
    assignment_percentage = (assigned_count / total_students * 100) if total_students > 0 else 0
    
    context = {
        'exam': exam,
        'students': students,
        'current_assignments': current_assignments,
        'search_query': search_query,
        'assignment_filter': assignment_filter,
        'total_students': total_students,
        'assigned_count': assigned_count,
        'unassigned_count': unassigned_count,
        'assignment_percentage': round(assignment_percentage, 1),
    }
    
    return render(request, 'admin_exam_assignments.html', context)


@admin_required
def admin_submissions(request):
    """Manage submissions"""
    search_query = request.GET.get('search', '')
    
    submissions = Submission.objects.select_related('student', 'exam').all()
    
    if search_query:
        submissions = submissions.filter(
            Q(student__username__icontains=search_query) |
            Q(exam__title__icontains=search_query)
        )
    
    submissions = submissions.order_by('-submitted_on')
    
    paginator = Paginator(submissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'admin': request.user,
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'admin_submissions.html', context)


@admin_required
def admin_violations(request):
    """Manage violations"""
    search_query = request.GET.get('search', '')
    violation_type = request.GET.get('type', '')
    
    violations = Violation.objects.select_related('student', 'exam').all()
    
    if search_query:
        violations = violations.filter(
            Q(student__username__icontains=search_query) |
            Q(exam__title__icontains=search_query)
        )
    
    if violation_type:
        violations = violations.filter(type=violation_type)
    
    violations = violations.order_by('-timestamp')
    
    paginator = Paginator(violations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'admin': request.user,
        'page_obj': page_obj,
        'search_query': search_query,
        'violation_type': violation_type,
        'violation_types': Violation.VIOLATION_TYPES,
    }
    return render(request, 'admin_violations.html', context)


@admin_required
def admin_bug_reports(request):
    """Manage bug reports"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    
    bugs = BugReport.objects.select_related('reporter').all()
    
    if search_query:
        bugs = bugs.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(reporter__username__icontains=search_query)
        )
    
    if status_filter:
        bugs = bugs.filter(status=status_filter)
    
    if priority_filter:
        bugs = bugs.filter(priority=priority_filter)
    
    bugs = bugs.order_by('-created_at')
    
    paginator = Paginator(bugs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'admin': request.user,
        'bugs': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'statuses': BugReport.STATUS_CHOICES,
        'priorities': BugReport.PRIORITY_CHOICES,
    }
    return render(request, 'admin_bug_reports.html', context)


@admin_required
def admin_bug_detail(request, bug_id):
    """View/Edit bug report details"""
    bug = get_object_or_404(BugReport, id=bug_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update':
            bug.status = request.POST.get('status', '')
            bug.priority = request.POST.get('priority', '')
            bug.save()
            messages.success(request, f'Bug report updated successfully.')
        
        elif action == 'delete':
            title = bug.title
            bug.delete()
            messages.success(request, f'Bug report "{title}" deleted successfully.')
            return redirect('admin_bug_reports')
    
    context = {
        'admin': request.user,
        'bug': bug,
        'statuses': BugReport.STATUS_CHOICES,
        'priorities': BugReport.PRIORITY_CHOICES,
    }
    return render(request, 'admin_bug_detail.html', context)


@admin_required
def admin_system_settings(request):
    """System settings and maintenance"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'cleanup_otps':
            # Clean up expired OTPs
            expired_count = 0
            expired_otps = PasswordResetOTP.objects.filter(is_used=False)
            for otp_obj in expired_otps:
                if otp_obj.is_expired():
                    otp_obj.delete()
                    expired_count += 1
            
            # Clean up used OTPs
            used_count = PasswordResetOTP.objects.filter(is_used=True).count()
            PasswordResetOTP.objects.filter(is_used=True).delete()
            
            messages.success(request, f'Cleaned up {expired_count} expired and {used_count} used OTPs.')
        
        elif action == 'send_bulk_emails':
            # This would integrate with the existing email system
            messages.info(request, 'Bulk email functionality can be implemented here.')
    
    # System statistics
    otp_count = PasswordResetOTP.objects.count()
    expired_otp_count = sum(1 for otp in PasswordResetOTP.objects.filter(is_used=False) if otp.is_expired())
    
    context = {
        'admin': request.user,
        'otp_count': otp_count,
        'expired_otp_count': expired_otp_count,
    }
    return render(request, 'admin_system_settings.html', context)


@admin_required
def admin_export_data(request):
    """Export data as CSV"""
    data_type = request.GET.get('type', 'users')
    
    response = HttpResponse(content_type='text/csv')
    
    if data_type == 'users':
        response['Content-Disposition'] = 'attachment; filename="users.csv"'
        writer = csv.writer(response)
        writer.writerow(['Username', 'Email', 'Role', 'First Name', 'Last Name', 'Date Joined', 'Is Active'])
        
        for user in User.objects.all():
            writer.writerow([
                user.username, user.email, user.role, user.first_name, 
                user.last_name, user.date_joined, user.is_active
            ])
    
    elif data_type == 'exams':
        response['Content-Disposition'] = 'attachment; filename="exams.csv"'
        writer = csv.writer(response)
        writer.writerow(['Title', 'Created By', 'Date', 'Duration (minutes)', 'Description'])
        
        for exam in Exam.objects.select_related('created_by').all():
            writer.writerow([
                exam.title, exam.created_by.username, exam.date, 
                exam.duration_minutes, exam.description
            ])
    
    elif data_type == 'submissions':
        response['Content-Disposition'] = 'attachment; filename="submissions.csv"'
        writer = csv.writer(response)
        writer.writerow(['Student', 'Exam', 'Score', 'Submitted On'])
        
        for submission in Submission.objects.select_related('student', 'exam').all():
            writer.writerow([
                submission.student.username, submission.exam.title, 
                submission.score, submission.submitted_on
            ])
    
    elif data_type == 'violations':
        response['Content-Disposition'] = 'attachment; filename="violations.csv"'
        writer = csv.writer(response)
        writer.writerow(['Student', 'Exam', 'Type', 'Timestamp'])
        
        for violation in Violation.objects.select_related('student', 'exam').all():
            writer.writerow([
                violation.student.username, violation.exam.title, 
                violation.type, violation.timestamp
            ])
    
    return response


def admin_logout(request):
    """Admin logout"""
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('admin_login')
