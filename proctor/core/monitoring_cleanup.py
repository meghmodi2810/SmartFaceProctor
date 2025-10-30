import logging
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Exam, ExamAttempt
from .FaceModules.exam_monitor import ExamMonitor

logger = logging.getLogger(__name__)

def cleanup_exam_monitoring(request=None):
    """
    Utility function to clean up exam monitoring for ended exams.
    Can be called by a cron job or manually.
    """
    try:
        current_time = timezone.now()
        
        # Get all exams that have just ended
        ending_exams = Exam.objects.filter(
            date__lte=current_time - timedelta(minutes=1),  # Give 1 minute buffer
            date__gte=current_time - timedelta(minutes=10)  # Look back 10 minutes
        )
        
        for exam in ending_exams:
            exam_end_time = exam.date + timedelta(minutes=exam.duration_minutes)
            
            # If exam has ended, stop all monitoring instances
            if current_time > exam_end_time:
                # Get all active monitoring instances for this exam
                active_monitors = ExamMonitor._instances.copy()  # Copy to avoid modification during iteration
                for key, monitor in active_monitors.items():
                    if key.endswith(f"_{exam.id}"):
                        try:
                            monitor.stop_monitoring()
                        except Exception:
                            pass  # Ensure cleanup continues even if one monitor fails
                            
    except Exception:
        pass  # Ensure cleanup doesn't break anything if it fails

def cleanup_stale_monitors():
    """Clean up stale exam monitoring instances"""
    try:
        # Get active exam attempts
        active_attempts = ExamAttempt.objects.filter(
            is_active=True
        ).select_related('exam', 'student')
        
        current_time = timezone.now()
        cleanup_count = 0
        
        for attempt in active_attempts:
            # Calculate exam end time
            exam_end_time = attempt.exam.date + timedelta(minutes=attempt.exam.duration_minutes)
            
            # Check if exam has ended
            if current_time > exam_end_time:
                # Get monitor instance if it exists
                monitor_key = f"{attempt.student.id}_{attempt.exam.id}"
                monitor = ExamMonitor._instances.get(monitor_key)
                
                if monitor:
                    try:
                        monitor.stop_monitoring()
                        cleanup_count += 1
                    except Exception as e:
                        logger.error(f"Error stopping monitor for {monitor_key}: {e}")
                
                # Mark attempt as inactive
                attempt.is_active = False
                attempt.ended_at = current_time
                attempt.save()
        
        logger.info(f"Cleaned up {cleanup_count} stale monitoring instances")
        return cleanup_count
        
    except Exception as e:
        logger.error(f"Error in cleanup_stale_monitors: {e}")
        return 0

def cleanup_on_server_start():
    """Run cleanup when server starts"""
    try:
        # Clear all monitoring instances since server is starting fresh
        ExamMonitor._instances.clear()
        
        # Mark all active attempts as inactive
        cleanup_count = ExamAttempt.objects.filter(is_active=True).update(
            is_active=False,
            ended_at=timezone.now()
        )
        
        logger.info(f"Server start cleanup: Marked {cleanup_count} attempts as inactive")
        return cleanup_count
        
    except Exception as e:
        logger.error(f"Error in cleanup_on_server_start: {e}")
        return 0