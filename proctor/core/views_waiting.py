"""
Views for handling the exam waiting room functionality.
This is separated from the main views to keep the code organized.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse

from .models import Exam, Question, Submission

@login_required
def exam_waiting_room(request, exam_id):
    """
    Dedicated waiting room page that shows countdown to exam start.
    This is completely separate from the actual exam interface.
    """
    user = request.user
    if user.role != 'Student':
        return redirect('faculty_dashboard')
    
    try:
        exam = Exam.objects.get(id=exam_id)
        current_time = timezone.now()
        exam_start_time = exam.date
        exam_end_time = exam_start_time + timezone.timedelta(minutes=exam.duration_minutes)
        
        # If exam has already started, redirect to the exam
        if current_time >= exam_start_time:
            return redirect('start_mcq_exam', exam_id=exam_id)
            
        # If exam has ended (shouldn't normally reach here)
        if current_time > exam_end_time:
            messages.error(request, 'This exam has ended.')
            return redirect('student_exams')
        
        # Calculate time until exam starts
        time_until_start = max(0, (exam_start_time - current_time).total_seconds())
        
        context = {
            'exam': exam,
            'time_until_start': int(time_until_start),
            'exam_start_time': exam_start_time,
            'exam_end_time': exam_end_time,
            'questions_count': Question.objects.filter(exam=exam).count(),
            'student': user
        }
        return render(request, 'exam_waiting_room.html', context)
        
    except Exam.DoesNotExist:
        messages.error(request, 'Exam not found.')
        return redirect('student_exams')

def check_exam_status(request, exam_id):
    """
    API endpoint to check exam status.
    Used by the waiting room to know when to redirect to the exam.
    """
    if not request.user.is_authenticated or request.user.role != 'Student':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        exam = Exam.objects.get(id=exam_id)
        current_time = timezone.now()
        exam_start_time = exam.date
        exam_end_time = exam_start_time + timezone.timedelta(minutes=exam.duration_minutes)
        
        # Check if exam has started
        if current_time >= exam_start_time:
            return JsonResponse({
                'started': True,
                'message': 'Exam has started',
                'redirect_url': reverse('start_mcq_exam', args=[exam_id])
            })
            
        # Calculate time until exam starts
        time_until_start = max(0, (exam_start_time - current_time).total_seconds())
        
        return JsonResponse({
            'started': False,
            'message': f'Exam starts in {int(time_until_start)} seconds',
            'time_until_start': int(time_until_start)
        })
        
    except Exam.DoesNotExist:
        return JsonResponse({'error': 'Exam not found'}, status=404)
