from django.db.models.signals import post_save, pre_save, post_delete, pre_delete
from django.dispatch import receiver
import logging
from .models import Exam, Submission, ExamAssignment, User
from .email_notifications import send_exam_scheduled_notification, send_exam_result_notification

logger = logging.getLogger('exam_monitoring')


@receiver(post_save, sender=Exam)
def notify_students_on_exam_creation(sender, instance, created, **kwargs):
    """
    Send email notifications to students when a new exam is created
    """
    if created:
        try:
            # Get all students who should receive this notification
            if instance.is_selective:
                # For selective exams, only notify assigned students
                assignments = ExamAssignment.objects.filter(
                    exam=instance,
                    is_active=True
                ).select_related('student')
                students = [assignment.student for assignment in assignments]
            else:
                # For general exams, notify all students
                students = User.objects.filter(role='Student', is_active=True)
            
            if students:
                # Send notification emails
                send_exam_scheduled_notification(instance, students)
                logger.info(f"Exam scheduled notifications sent for: {instance.title} to {len(students)} students")
            else:
                logger.warning(f"No students found to notify for exam: {instance.title}")
                
        except Exception as e:
            logger.error(f"Error sending exam scheduled notifications: {str(e)}")


@receiver(post_save, sender=ExamAssignment)
def notify_student_on_selective_assignment(sender, instance, created, **kwargs):
    """
    Send email notification when a student is assigned to a selective exam
    """
    if created and instance.is_active:
        try:
            # Send notification to the newly assigned student
            send_exam_scheduled_notification(instance.exam, [instance.student])
            logger.info(f"Selective exam assignment notification sent to {instance.student.email} for exam: {instance.exam.title}")
        except Exception as e:
            logger.error(f"Error sending selective assignment notification: {str(e)}")


@receiver(post_save, sender=Submission)
def notify_student_on_result_available(sender, instance, created, **kwargs):
    """
    Send email notification to student when their exam result is available
    """
    if created:
        try:
            # Send result notification email
            send_exam_result_notification(instance)
            logger.info(f"Exam result notification sent to {instance.student.email} for exam: {instance.exam.title}")
        except Exception as e:
            logger.error(f"Error sending exam result notification: {str(e)}")
