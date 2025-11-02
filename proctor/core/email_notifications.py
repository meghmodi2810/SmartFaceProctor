from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger('exam_monitoring')

def send_exam_scheduled_notification(exam, students):
    """
    Send email notification to students when a new exam is scheduled
    
    Args:
        exam: Exam object
        students: List of User objects (students)
    """
    try:
        subject = f"New Exam Scheduled: {exam.title}"
        
        # Format date and time
        exam_date = exam.date.strftime("%B %d, %Y")
        exam_time = exam.date.strftime("%I:%M %p")
        
        for student in students:
            # Create personalized email content
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                             color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .exam-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; 
                                   border-left: 4px solid #667eea; }}
                    .detail-row {{ margin: 10px 0; }}
                    .label {{ font-weight: bold; color: #667eea; }}
                    .button {{ display: inline-block; padding: 12px 30px; background: #667eea; 
                             color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                    .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📝 New Exam Scheduled</h1>
                    </div>
                    <div class="content">
                        <p>Dear {student.first_name or student.username},</p>
                        
                        <p>A new exam has been scheduled for you. Please review the details below:</p>
                        
                        <div class="exam-details">
                            <h2 style="color: #667eea; margin-top: 0;">{exam.title}</h2>
                            
                            <div class="detail-row">
                                <span class="label">📅 Date:</span> {exam_date}
                            </div>
                            <div class="detail-row">
                                <span class="label">🕐 Time:</span> {exam_time}
                            </div>
                            <div class="detail-row">
                                <span class="label">⏱️ Duration:</span> {exam.duration_minutes} minutes
                            </div>
                            <div class="detail-row">
                                <span class="label">👨‍🏫 Created by:</span> {exam.created_by.get_full_name() or exam.created_by.username}
                            </div>
                            
                            {f'<div class="detail-row"><span class="label">📋 Description:</span> {exam.description}</div>' if exam.description else ''}
                        </div>
                        
                        <p><strong>Important Reminders:</strong></p>
                        <ul>
                            <li>Ensure you have a stable internet connection</li>
                            <li>Keep your camera and microphone ready</li>
                            <li>Log in 10 minutes before the exam starts</li>
                            <li>Make sure you're in a well-lit, quiet environment</li>
                        </ul>
                        
                        <p style="text-align: center;">
                            <a href="{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}/student/notifications/" 
                               class="button">View in Dashboard</a>
                        </p>
                        
                        <div class="footer">
                            <p>This is an automated message from Smart Face Proctor System</p>
                            <p>Please do not reply to this email</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            plain_message = f"""
            New Exam Scheduled: {exam.title}
            
            Dear {student.first_name or student.username},
            
            A new exam has been scheduled for you.
            
            Exam Details:
            - Date: {exam_date}
            - Time: {exam_time}
            - Duration: {exam.duration_minutes} minutes
            - Created by: {exam.created_by.get_full_name() or exam.created_by.username}
            
            {f'Description: {exam.description}' if exam.description else ''}
            
            Important Reminders:
            - Ensure you have a stable internet connection
            - Keep your camera and microphone ready
            - Log in 10 minutes before the exam starts
            
            Please check your dashboard for more details.
            
            This is an automated message from Smart Face Proctor System.
            """
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Exam scheduled notification sent to {student.email} for exam: {exam.title}")
            
    except Exception as e:
        logger.error(f"Error sending exam scheduled notification: {str(e)}")


def send_exam_result_notification(submission):
    """
    Send email notification to student with their exam result
    
    Args:
        submission: Submission object
    """
    try:
        from .views_student_results import calculate_grade
        
        student = submission.student
        exam = submission.exam
        score = submission.score
        grade = calculate_grade(score)
        
        subject = f"Exam Result: {exam.title}"
        
        # Determine result status
        if score >= 34:
            status = "Passed"
            status_color = "#10b981"
            status_emoji = "🎉"
        else:
            status = "Failed"
            status_color = "#ef4444"
            status_emoji = "📝"
        
        # Format submission date
        submission_date = submission.submitted_on.strftime("%B %d, %Y at %I:%M %p")
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                         color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .result-card {{ background: white; padding: 30px; border-radius: 8px; margin: 20px 0; 
                              text-align: center; border: 3px solid {status_color}; }}
                .score {{ font-size: 48px; font-weight: bold; color: {status_color}; margin: 20px 0; }}
                .grade {{ font-size: 36px; font-weight: bold; color: #667eea; 
                        background: #e0e7ff; padding: 10px 30px; border-radius: 50px; 
                        display: inline-block; margin: 10px 0; }}
                .status {{ font-size: 24px; font-weight: bold; color: {status_color}; margin: 10px 0; }}
                .exam-info {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .detail-row {{ margin: 10px 0; padding: 10px; border-bottom: 1px solid #e2e8f0; }}
                .label {{ font-weight: bold; color: #667eea; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; 
                         color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{status_emoji} Exam Result Available</h1>
                </div>
                <div class="content">
                    <p>Dear {student.first_name or student.username},</p>
                    
                    <p>Your exam result for <strong>{exam.title}</strong> is now available.</p>
                    
                    <div class="result-card">
                        <div class="status">{status}</div>
                        <div class="score">{score:.1f}%</div>
                        <div class="grade">Grade: {grade}</div>
                    </div>
                    
                    <div class="exam-info">
                        <h3 style="color: #667eea; margin-top: 0;">Exam Details</h3>
                        <div class="detail-row">
                            <span class="label">📝 Exam:</span> {exam.title}
                        </div>
                        <div class="detail-row">
                            <span class="label">📅 Submitted on:</span> {submission_date}
                        </div>
                        <div class="detail-row">
                            <span class="label">⏱️ Duration:</span> {exam.duration_minutes} minutes
                        </div>
                        <div class="detail-row">
                            <span class="label">👨‍🏫 Conducted by:</span> {exam.created_by.get_full_name() or exam.created_by.username}
                        </div>
                    </div>
                    
                    <p style="text-align: center;">
                        <a href="{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}/student/results/" 
                           class="button">View All Results</a>
                    </p>
                    
                    <div class="footer">
                        <p>This is an automated message from Smart Face Proctor System</p>
                        <p>Please do not reply to this email</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_message = f"""
        Exam Result: {exam.title}
        
        Dear {student.first_name or student.username},
        
        Your exam result is now available.
        
        Result: {status}
        Score: {score:.1f}%
        Grade: {grade}
        
        Exam Details:
        - Exam: {exam.title}
        - Submitted on: {submission_date}
        - Duration: {exam.duration_minutes} minutes
        - Conducted by: {exam.created_by.get_full_name() or exam.created_by.username}
        
        Please check your dashboard to view detailed results.
        
        This is an automated message from Smart Face Proctor System.
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Exam result notification sent to {student.email} for exam: {exam.title}")
        
    except Exception as e:
        logger.error(f"Error sending exam result notification: {str(e)}")
