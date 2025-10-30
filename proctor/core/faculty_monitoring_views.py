from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q, Avg, F
from django.db import models
from .models import Exam, User, Violation, ExamAttempt, Submission, ExamAssignment
import json


@login_required
def faculty_live_monitoring(request):
    """View for faculty to monitor ongoing exams in real-time"""
    if request.user.role != 'Faculty':
        return redirect('login')
    
    # Get all ongoing exams created by this faculty
    from django.utils import timezone
    from django.db.models import Count, Q
    current_time = timezone.now()
    
    # Get all exams that are currently ongoing
    all_exams = Exam.objects.filter(
        created_by=request.user,
        date__lte=current_time
    ).prefetch_related(
        'attempts__student',
        'violations__student',
        'assignments__student'
    ).order_by('-date')
    
    ongoing_exams = []
    for exam in all_exams:
        exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
        if current_time <= exam_end_time:
            ongoing_exams.append(exam)
    
    # Get all students for each exam (from attempts, assignments, or submissions)
    exam_students_data = []
    for exam in ongoing_exams:
        exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
        
        # Get all students taking this exam (attempts, assignments, or anyone with violations)
        attempt_students = set(exam.attempts.filter(is_active=True).values_list('student_id', flat=True))
        assignment_students = set(exam.assignments.filter(is_active=True).values_list('student_id', flat=True))
        violation_students = set(Violation.objects.filter(exam=exam).values_list('student_id', flat=True))
        
        all_student_ids = attempt_students | assignment_students | violation_students
        
        # Get all students taking this exam
        students = User.objects.filter(
            id__in=all_student_ids,
            role='Student'
        ).distinct()
        
        student_list = []
        for student in students:
            # Get violations
            violations = Violation.objects.filter(exam=exam, student=student).order_by('-timestamp')
            violation_count = violations.count()
            is_frozen = violations.filter(is_frozen=True, freeze_cancelled_by__isnull=True).exists()
            
            # Get attempt info
            attempt = ExamAttempt.objects.filter(exam=exam, student=student, is_active=True).first()
            started_at = attempt.started_at if attempt else None
            
            # Get submission status
            has_submitted = Submission.objects.filter(exam=exam, student=student).exists()
            
            # Get latest violations/warnings
            recent_violations = violations[:5]  # Last 5 violations
            
            student_list.append({
                'student': student,
                'violation_count': violation_count,
                'is_frozen': is_frozen,
                'started_at': started_at,
                'has_submitted': has_submitted,
                'recent_violations': recent_violations,
                'warnings': violation_count  # Using violation count as warnings
            })
        
        exam_students_data.append({
            'exam': exam,
            'students': student_list,
            'exam_end_time': exam_end_time
        })
    
    context = {
        'exam_students_data': exam_students_data,
        'faculty': request.user,
        'current_time': current_time
    }
    
    return render(request, 'faculty_live_monitoring.html', context)


@login_required
def cancel_freeze(request):
    """Cancel freeze timer for a student - faculty override"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    if request.user.role != 'Faculty':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        exam_id = data.get('exam_id')
        student_id = data.get('student_id')
        
        exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
        student = get_object_or_404(User, id=student_id, role='Student')
        
        # Mark frozen violations as cancelled by faculty
        frozen_violations = Violation.objects.filter(
            exam=exam,
            student=student,
            is_frozen=True,
            freeze_cancelled_by__isnull=True
        )
        
        violations_count = frozen_violations.count()
        frozen_violations.update(
            freeze_cancelled_by=request.user,
            is_frozen=False  # Unfreeze the violations
        )
        
        # Clear freeze state in student's session
        # This will be checked on next distraction detection cycle
        from django.contrib.sessions.models import Session
        from django.contrib.auth import get_user_model
        
        # Signal the freeze cancellation via creating a special session flag
        # The student's session will pick this up on next check_distraction call
        
        return JsonResponse({
            'success': True,
            'message': f'Freeze cancelled for {student.get_full_name() or student.username}',
            'violations_updated': violations_count,
            'student_name': student.get_full_name() or student.username
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def reset_exam_attempt(request):
    """Allow faculty to reset a student's exam attempt for reappearing"""
    if request.user.role != 'Faculty':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        exam_id = data.get('exam_id')
        student_id = data.get('student_id')
        
        exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
        student = get_object_or_404(User, id=student_id, role='Student')
        
        # Clear previous submission if exists
        Submission.objects.filter(exam=exam, student=student).delete()
        
        # Reset violations
        Violation.objects.filter(exam=exam, student=student).update(is_frozen=False)
        
        # Update or create exam attempt
        attempt, created = ExamAttempt.objects.get_or_create(
            exam=exam,
            student=student,
            defaults={
                'is_active': True,
                'can_reattempt': True,
                'reset_by': request.user,
                'reset_at': timezone.now()
            }
        )
        
        if not created:
            attempt.is_active = True
            attempt.can_reattempt = True
            attempt.reset_by = request.user
            attempt.reset_at = timezone.now()
            attempt.save()
        
        # Log the reset action
        from django.contrib.admin.models import LogEntry, CHANGE
        from django.contrib.contenttypes.models import ContentType
        LogEntry.objects.create(
            user_id=request.user.id,
            content_type_id=ContentType.objects.get_for_model(exam).id,
            object_id=exam.id,
            object_repr=str(exam),
            action_flag=CHANGE,
            change_message=f'Reset exam attempt for student {student.username}'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Exam reset successful for {student.get_full_name() or student.username}',
            'student_name': student.get_full_name() or student.username,
            'reset_time': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def end_exam(request):
    """Manually end exam for all students and create submissions for attempted MCQs"""
    if request.user.role != 'Faculty':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        exam_id = data.get('exam_id')
        
        exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
        
        # Get all active attempts for this exam
        from .models import Question
        try:
            from .models import ExamProgress
            has_exam_progress = True
        except ImportError:
            has_exam_progress = False
        
        active_attempts = ExamAttempt.objects.filter(exam=exam, is_active=True)
        
        submissions_created = 0
        for attempt in active_attempts:
            student = attempt.student
            
            # Check if student already submitted
            existing_submission = Submission.objects.filter(exam=exam, student=student).first()
            if existing_submission:
                continue
            
            # Try to get saved progress
            score = 0
            if has_exam_progress:
                try:
                    from .models import ExamProgress
                    progress = ExamProgress.objects.get(exam=exam, student=student)
                    answers = progress.answers
                    
                    # Calculate score from saved answers
                    questions = Question.objects.filter(exam=exam)
                    correct_count = 0
                    total_questions = questions.count()
                    
                    for question in questions:
                        student_answer = answers.get(str(question.id), '')
                        if student_answer == question.answer:
                            correct_count += 1
                    
                    score = (correct_count / total_questions * 100) if total_questions > 0 else 0
                except Exception:
                    # No saved progress or table doesn't exist, score remains 0
                    score = 0
            else:
                # ExamProgress model doesn't exist
                score = 0
            
            # Create submission with calculated score
            Submission.objects.create(
                exam=exam,
                student=student,
                score=score
            )
            
            # Mark attempt as completed
            attempt.is_active = False
            attempt.ended_at = timezone.now()
            attempt.save()
            
            submissions_created += 1
        
        # Mark exam as ended by updating its duration to make it past
        # Or add a flag to indicate manual end
        
        return JsonResponse({
            'success': True,
            'submissions_created': submissions_created,
            'message': f'Exam ended. {submissions_created} submissions created.'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def student_violations_detail(request, exam_id, student_id):
    """View detailed violations for a student in an exam"""
    if request.user.role != 'Faculty':
        return redirect('student_dashboard')
    
    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
    student = get_object_or_404(User, id=student_id, role='Student')
    
    violations = Violation.objects.filter(
        exam=exam,
        student=student
    ).order_by('-timestamp')
    
    context = {
        'exam': exam,
        'student': student,
        'violations': violations,
        'total_violations': violations.count(),
        'frozen_violations': violations.filter(is_frozen=True).count()
    }
    
    return render(request, 'student_violations_detail.html', context)


@login_required
def student_analytics(request):
    """Analytics dashboard for all students"""
    if request.user.role != 'Faculty':
        return redirect('student_dashboard')
    
    # Get all exams by this faculty
    faculty_exams = Exam.objects.filter(created_by=request.user)
    
    # Get students who have taken exams
    students = User.objects.filter(
        role='Student',
        submission__exam__in=faculty_exams
    ).distinct().annotate(
        total_exams=Count('submission', distinct=True),
        avg_score=Avg('submission__score'),
        total_violations=Count('violation', distinct=True)
    ).order_by('-avg_score')
    
    # Get recent violations
    recent_violations = Violation.objects.filter(
        exam__in=faculty_exams
    ).select_related('student', 'exam').order_by('-timestamp')[:50]
    
    # Statistics
    total_students = students.count()
    total_submissions = Submission.objects.filter(exam__in=faculty_exams).count()
    total_violations = Violation.objects.filter(exam__in=faculty_exams).count()
    avg_score = Submission.objects.filter(exam__in=faculty_exams).aggregate(Avg('score'))['score__avg'] or 0
    
    context = {
        'students': students,
        'recent_violations': recent_violations,
        'total_students': total_students,
        'total_submissions': total_submissions,
        'total_violations': total_violations,
        'avg_score': round(avg_score, 2),
        'faculty': request.user
    }
    
    return render(request, 'student_analytics.html', context)


@login_required
def exam_analytics(request, exam_id):
    """Detailed analytics for a specific exam"""
    if request.user.role != 'Faculty':
        return redirect('student_dashboard')
    
    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
    
    # Get submissions
    submissions = Submission.objects.filter(exam=exam).select_related('student')
    
    # Get attempts
    attempts = ExamAttempt.objects.filter(exam=exam).select_related('student')
    
    # Get violations
    violations = Violation.objects.filter(exam=exam).select_related('student')
    
    # Statistics
    total_attempts = attempts.count()
    total_submissions = submissions.count()
    total_violations = violations.count()
    avg_score = submissions.aggregate(Avg('score'))['score__avg'] or 0
    
    # Score distribution
    score_ranges = {
        '0-20': submissions.filter(score__lt=20).count(),
        '20-40': submissions.filter(score__gte=20, score__lt=40).count(),
        '40-60': submissions.filter(score__gte=40, score__lt=60).count(),
        '60-80': submissions.filter(score__gte=60, score__lt=80).count(),
        '80-100': submissions.filter(score__gte=80).count(),
    }
    
    # Violation types
    violation_types = violations.values('type').annotate(count=Count('type')).order_by('-count')
    
    context = {
        'exam': exam,
        'submissions': submissions,
        'attempts': attempts,
        'violations': violations,
        'total_attempts': total_attempts,
        'total_submissions': total_submissions,
        'total_violations': total_violations,
        'avg_score': round(avg_score, 2),
        'score_ranges': score_ranges,
        'violation_types': violation_types
    }
    
    return render(request, 'exam_analytics.html', context)


@login_required
def get_exam_status_updates(request, exam_id):
    """AJAX endpoint for getting real-time exam status updates"""
    if request.user.role != 'Faculty':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
        current_time = timezone.now()
        exam_end_time = exam.date + timezone.timedelta(minutes=exam.duration_minutes)
        
        # Get all students with active attempts or violations
        attempt_students = set(exam.attempts.filter(is_active=True).values_list('student_id', flat=True))
        violation_students = set(Violation.objects.filter(
            exam=exam,
            timestamp__gte=current_time - timezone.timedelta(minutes=5)
        ).values_list('student_id', flat=True))
        
        all_student_ids = attempt_students | violation_students
        
        students_data = []
        for student in User.objects.filter(id__in=all_student_ids):
            # Get recent violations
            recent_violations = Violation.objects.filter(
                exam=exam,
                student=student,
                timestamp__gte=current_time - timezone.timedelta(minutes=5)
            ).order_by('-timestamp')
            
            # Get frozen status
            is_frozen = Violation.objects.filter(
                exam=exam,
                student=student,
                is_frozen=True,
                freeze_cancelled_by__isnull=True
            ).exists()
            
            # Get submission status
            has_submitted = Submission.objects.filter(exam=exam, student=student).exists()
            
            students_data.append({
                'student_id': student.id,
                'student_name': student.get_full_name() or student.username,
                'violations_count': recent_violations.count(),
                'is_frozen': is_frozen,
                'has_submitted': has_submitted,
                'recent_violations': [
                    {
                        'type': v.type,
                        'timestamp': v.timestamp.isoformat(),
                        'message': v.message if hasattr(v, 'message') else None
                    } for v in recent_violations[:5]
                ]
            })
        
        return JsonResponse({
            'success': True,
            'exam_id': exam.id,
            'current_time': current_time.isoformat(),
            'exam_end_time': exam_end_time.isoformat(),
            'is_exam_ended': current_time > exam_end_time,
            'students': students_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def update_exam_assignment(request):
    """Update exam assignment when faculty enables reappearing"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    if request.user.role != 'Faculty':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        exam_id = data.get('exam_id')
        student_id = data.get('student_id')
        action = data.get('action')  # 'enable' or 'disable'
        
        exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
        student = get_object_or_404(User, id=student_id, role='Student')
        
        if action not in ['enable', 'disable']:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        assignment, created = ExamAssignment.objects.get_or_create(
            exam=exam,
            student=student,
            defaults={
                'assigned_by': request.user,
                'is_active': action == 'enable'
            }
        )
        
        if not created:
            assignment.is_active = action == 'enable'
            assignment.save()
        
        # If enabling reappear, also reset attempt
        if action == 'enable':
            # Clear previous submission
            Submission.objects.filter(exam=exam, student=student).delete()
            
            # Reset violations
            Violation.objects.filter(exam=exam, student=student).update(is_frozen=False)
            
            # Update attempt
            attempt, _ = ExamAttempt.objects.get_or_create(
                exam=exam,
                student=student,
                defaults={
                    'is_active': True,
                    'can_reattempt': True,
                    'reset_by': request.user,
                    'reset_at': timezone.now()
                }
            )
            if not _:
                attempt.is_active = True
                attempt.can_reattempt = True
                attempt.reset_by = request.user
                attempt.reset_at = timezone.now()
                attempt.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{"Enabled" if action == "enable" else "Disabled"} reappear for {student.get_full_name() or student.username}',
            'assignment_id': assignment.id,
            'is_active': assignment.is_active
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
