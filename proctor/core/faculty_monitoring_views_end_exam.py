from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import Exam
import json

@login_required
def end_exam(request):
    """End an exam early (force end for all students)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if request.user.role != 'Faculty':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        exam_id = data.get('exam_id')
        
        if not exam_id:
            return JsonResponse({'error': 'exam_id is required'}, status=400)
        
        exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
        
        # Force end the exam by setting the end time to now
        current_time = timezone.now()
        exam_duration = timezone.timedelta(minutes=exam.duration_minutes)
        
        # Set exam date such that end time is now
        exam.date = current_time - exam_duration
        exam.save()
        
        # Get all active students in this exam (those who haven't submitted)
        from .models import ExamAttempt, Submission
        active_attempts = ExamAttempt.objects.filter(
            exam=exam,
            is_active=True
        ).select_related('student')
        
        active_students_count = active_attempts.count()
        
        # Mark all active attempts as ended
        for attempt in active_attempts:
            attempt.is_active = False
            attempt.ended_at = current_time
            attempt.save()
        
        # Clear any active exam sessions for these students
        # This will trigger frontend to show "exam ended by faculty" message
        
        return JsonResponse({
            'success': True,
            'message': f'Exam "{exam.title}" has been ended. {active_students_count} active student(s) were notified.',
            'exam_id': exam.id,
            'active_students': active_students_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
