from datetime import datetime, timedelta
from django.utils import timezone

def cleanup_exam_monitoring(request=None):
    """
    Utility function to clean up exam monitoring for ended exams.
    Can be called by a cron job or manually.
    """
    try:
        from .models import Exam
        from .FaceModules.exam_monitor import ExamMonitor
        
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