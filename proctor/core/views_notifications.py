from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from .models import Exam, Submission, ExamAssignment, NotificationRead

@login_required
def student_notifications(request):
    """Display categorized exam notifications for students"""
    user = request.user
    if user.role != 'Student':
        return redirect('faculty_dashboard')
    
    current_time = timezone.now()
    
    # Get all exams that haven't ended yet
    from .models import ExamAssignment
    all_exams = Exam.objects.select_related('created_by').order_by('date')
    
    # Filter based on selective assignment
    if all_exams.exists():
        selective_exam_ids = set(ExamAssignment.objects.filter(
            student=user,
            exam_id__in=[e.id for e in all_exams],
            is_active=True
        ).values_list('exam_id', flat=True))
        
        filtered_exams = []
        for exam in all_exams:
            if not exam.is_selective or exam.id in selective_exam_ids:
                filtered_exams.append(exam)
        all_exams = filtered_exams
    
    # Categorize exams
    urgent_exams = []  # Starting in 5 minutes or less
    warning_10min_exams = []  # Starting in 6-10 minutes
    warning_30min_exams = []  # Starting in 11-30 minutes
    upcoming_exams = []  # Starting in more than 30 minutes
    missed_exams = []  # Already ended and not submitted
    
    # Get list of exam IDs that student has marked as read
    read_exam_ids = set(NotificationRead.objects.filter(
        student=user
    ).values_list('exam_id', flat=True))
    
    for exam in all_exams:
        exam_end_time = exam.date + timedelta(minutes=exam.duration_minutes)
        time_diff = (exam.date - current_time).total_seconds()
        
        # Mark if notification is read
        exam.is_read = exam.id in read_exam_ids
        
        # Check if student has submitted
        submission = Submission.objects.filter(student=user, exam=exam).first()
        
        # If exam has ended
        if current_time > exam_end_time:
            # Show as missed only if no submission
            if not submission:
                exam.end_time = exam_end_time
                missed_exams.append(exam)
        # If exam hasn't started yet
        elif current_time < exam.date:
            minutes_until = int(time_diff / 60)
            
            # Calculate time display
            if minutes_until < 1:
                exam.time_until = f"{int(time_diff)} seconds"
            elif minutes_until < 60:
                exam.time_until = f"{minutes_until} minutes"
            elif minutes_until < 1440:  # Less than 24 hours
                hours = minutes_until // 60
                mins = minutes_until % 60
                exam.time_until = f"{hours}h {mins}m"
            else:
                days = minutes_until // 1440
                exam.time_until = f"{days} days"
            
            # Categorize
            if minutes_until <= 5:
                urgent_exams.append(exam)
            elif minutes_until <= 10:
                warning_10min_exams.append(exam)
            elif minutes_until <= 30:
                warning_30min_exams.append(exam)
            else:
                upcoming_exams.append(exam)
    
    context = {
        'student': user,
        'urgent_exams': urgent_exams,
        'warning_10min_exams': warning_10min_exams,
        'warning_30min_exams': warning_30min_exams,
        'upcoming_exams': upcoming_exams,
        'missed_exams': missed_exams,
        'total_notifications': len(urgent_exams) + len(warning_10min_exams) + len(warning_30min_exams)
    }
    
    return render(request, 'student_notifications.html', context)


@login_required
def mark_notification_read(request, exam_id):
    """Mark an exam notification as read"""
    if request.method == 'POST' and request.user.role == 'Student':
        try:
            exam = Exam.objects.get(id=exam_id)
            NotificationRead.objects.get_or_create(
                student=request.user,
                exam=exam
            )
            return JsonResponse({'success': True, 'message': 'Notification marked as read'})
        except Exam.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Exam not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
def bulk_notification_action(request):
    """Handle bulk actions on notifications (mark read/unread, delete)"""
    if request.method != 'POST' or request.user.role != 'Student':
        return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
    
    try:
        import json
        data = json.loads(request.body)
        action = data.get('action')  # 'mark_read', 'mark_unread', 'delete'
        exam_ids = data.get('exam_ids', [])
        
        if not action or not exam_ids:
            return JsonResponse({'success': False, 'message': 'Action and exam IDs required'}, status=400)
        
        if action == 'mark_read':
            # Mark selected notifications as read
            for exam_id in exam_ids:
                try:
                    exam = Exam.objects.get(id=exam_id)
                    NotificationRead.objects.get_or_create(
                        student=request.user,
                        exam=exam
                    )
                except Exam.DoesNotExist:
                    continue
            
            return JsonResponse({
                'success': True,
                'message': f'{len(exam_ids)} notification(s) marked as read'
            })
        
        elif action == 'mark_unread':
            # Mark selected notifications as unread
            NotificationRead.objects.filter(
                student=request.user,
                exam_id__in=exam_ids
            ).delete()
            
            return JsonResponse({
                'success': True,
                'message': f'{len(exam_ids)} notification(s) marked as unread'
            })
        
        elif action == 'delete':
            # Delete notification read status (hide from view)
            deleted_count = NotificationRead.objects.filter(
                student=request.user,
                exam_id__in=exam_ids
            ).update(is_deleted=True)
            
            # If NotificationRead doesn't have is_deleted field, create new records
            for exam_id in exam_ids:
                try:
                    exam = Exam.objects.get(id=exam_id)
                    obj, created = NotificationRead.objects.get_or_create(
                        student=request.user,
                        exam=exam
                    )
                    # Mark as deleted (you may need to add this field to the model)
                    if hasattr(obj, 'is_deleted'):
                        obj.is_deleted = True
                        obj.save()
                except Exam.DoesNotExist:
                    continue
            
            return JsonResponse({
                'success': True,
                'message': f'{len(exam_ids)} notification(s) deleted'
            })
        
        else:
            return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
