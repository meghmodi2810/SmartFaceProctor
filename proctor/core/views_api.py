from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import traceback
import sys

def get_semesters(request, department_id):
    """API endpoint to fetch semesters for a department"""
    # Manual authentication check for API
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    try:
        # Import models inside function to catch import errors
        try:
            from .models import Department, Semester
        except ImportError as ie:
            return JsonResponse({
                'success': False,
                'error': f'Import Error: {str(ie)}',
                'traceback': traceback.format_exc()
            })
        
        try:
            department = Department.objects.get(id=department_id, is_active=True)
        except Department.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Department with id {department_id} not found'
            })
        
        semesters = Semester.objects.filter(department=department, is_active=True).order_by('name')
        
        semester_list = [
            {'id': sem.id, 'name': sem.name}
            for sem in semesters
        ]
        
        return JsonResponse({
            'success': True,
            'semesters': semester_list,
            'count': len(semester_list)
        })
    except Exception as e:
        # Catch all exceptions and return JSON
        return JsonResponse({
            'success': False,
            'error': f'{type(e).__name__}: {str(e)}',
            'traceback': traceback.format_exc(),
            'exception_type': str(type(e))
        })

def get_divisions(request, department_id, semester_id):
    """API endpoint to fetch divisions for a department and semester"""
    # Manual authentication check for API
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    try:
        # Import models inside function to catch import errors
        try:
            from .models import Department, Semester, Division
        except ImportError as ie:
            return JsonResponse({
                'success': False,
                'error': f'Import Error: {str(ie)}',
                'traceback': traceback.format_exc()
            })
        
        try:
            department = Department.objects.get(id=department_id, is_active=True)
        except Department.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Department with id {department_id} not found'
            })
        
        try:
            semester = Semester.objects.get(id=semester_id, department=department, is_active=True)
        except Semester.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Semester with id {semester_id} not found for department {department_id}'
            })
        
        divisions = Division.objects.filter(
            department=department, 
            semester=semester, 
            is_active=True
        ).order_by('name')
        
        division_list = [
            {'id': div.id, 'name': div.name}
            for div in divisions
        ]
        
        return JsonResponse({
            'success': True,
            'divisions': division_list,
            'count': len(division_list)
        })
    except Exception as e:
        # Catch all exceptions and return JSON
        return JsonResponse({
            'success': False,
            'error': f'{type(e).__name__}: {str(e)}',
            'traceback': traceback.format_exc(),
            'exception_type': str(type(e))
        })

@login_required
def search_results(request):
    """API endpoint for searching exam results on homepage"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    from .models import Submission
    
    # Only show limited public results (for privacy)
    submissions = Submission.objects.filter(
        Q(student__username__icontains=query) |
        Q(exam__title__icontains=query)
    ).select_related('student', 'exam').order_by('-submitted_on')[:10]
    
    results = []
    for submission in submissions:
        grade = calculate_grade(submission.score)
        grade_class_map = {'O': 'primary', 'A': 'success', 'B': 'info', 'C': 'warning', 'F': 'danger'}
        
        results.append({
            'exam_title': submission.exam.title,
            'student_username': submission.student.username,
            'score': f"{submission.score:.1f}",
            'grade': grade,
            'grade_class': grade_class_map.get(grade, 'secondary'),
            'date': submission.submitted_on.strftime('%b %d, %Y %H:%M')
        })
    
    return JsonResponse({'results': results})

@login_required
def search_student_results(request):
    """API endpoint for searching student's own results"""
    query = request.GET.get('q', '').strip()
    
    if request.user.role != 'Student':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    from .models import Submission
    
    submissions = Submission.objects.filter(
        student=request.user,
        exam__title__icontains=query
    ).select_related('exam').order_by('-submitted_on')
    
    results = []
    for submission in submissions:
        grade = calculate_grade(submission.score)
        results.append({
            'exam_id': submission.exam.id,
            'exam_title': submission.exam.title,
            'score': f"{submission.score:.1f}",
            'grade': grade,
            'date': submission.submitted_on.strftime('%b %d, %Y %H:%M')
        })
    
    return JsonResponse({'results': results})

def calculate_grade(score):
    """Calculate letter grade from percentage score"""
    if score >= 90:
        return 'O'
    elif score >= 70:
        return 'A'
    elif score >= 50:
        return 'B'
    elif score >= 34:
        return 'C'
    else:
        return 'F'

@login_required
def admin_search_users(request):
    """API endpoint for searching users in admin panel"""
    if request.user.role != 'Admin':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    
    from .models import User
    
    users = User.objects.all()
    
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    
    if role:
        users = users.filter(role=role)
    
    users = users.order_by('-date_joined')[:50]  # Limit to 50 results
    
    user_list = []
    for user in users:
        user_list.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'role': user.role,
            'is_active': user.is_active,
            'date_joined': user.date_joined.strftime('%b %d, %Y'),
            'last_login': user.last_login.strftime('%b %d, %Y %H:%M') if user.last_login else None
        })
    
    return JsonResponse({'users': user_list})
