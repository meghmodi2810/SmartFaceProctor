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
        
        # Force end the exam by setting the date + duration to current time
        # This makes the exam appear as ended
        current_time = timezone.now()
        exam_duration = timezone.timedelta(minutes=exam.duration_minutes)
        exam.date = current_time - exam_duration  # Set start time in the past
        exam.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Exam "{exam.title}" has been ended',
            'exam_id': exam.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
