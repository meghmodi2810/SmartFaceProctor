"""
Asynchronous Email Utility for Smart Face Proctor
Sends emails in background threads to prevent blocking the main application
"""
import threading
import time
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Log email configuration on module load
def _log_email_config():
    """Log email configuration for debugging"""
    try:
        host = getattr(settings, 'EMAIL_HOST', 'NOT SET')
        port = getattr(settings, 'EMAIL_PORT', 'NOT SET')
        user = getattr(settings, 'EMAIL_HOST_USER', 'NOT SET')
        has_password = bool(getattr(settings, 'EMAIL_HOST_PASSWORD', ''))
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')
        use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
        
        # Mask the user for security
        masked_user = user[:3] + '***' if user and len(user) > 3 else 'NOT SET'
        
        print(f"📧 Email Configuration:")
        print(f"   HOST: {host}")
        print(f"   PORT: {port}")
        print(f"   USER: {masked_user}")
        print(f"   PASSWORD SET: {has_password}")
        print(f"   FROM: {from_email}")
        print(f"   USE_TLS: {use_tls}")
        
        if not has_password:
            print("⚠️  WARNING: EMAIL_HOST_PASSWORD is not set! Emails will fail.")
        if host == 'smtp.sendgrid.net' and user != 'apikey':
            print("⚠️  WARNING: For SendGrid, EMAIL_HOST_USER should be 'apikey'")
            
    except Exception as e:
        print(f"❌ Error logging email config: {e}")

# Log config when module loads
_log_email_config()


def send_email_sync(subject, message, recipient_list, html_message=None):
    """
    Send email synchronously (blocking) - more reliable for production
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        # Validate configuration
        if not getattr(settings, 'EMAIL_HOST_PASSWORD', ''):
            error_msg = "EMAIL_HOST_PASSWORD is not configured"
            print(f"❌ {error_msg}")
            return False, error_msg
        
        print(f"📤 Sending email to {recipient_list}...")
        print(f"   Subject: {subject}")
        print(f"   From: {settings.DEFAULT_FROM_EMAIL}")
        print(f"   Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        
        if result:
            print(f"✅ Email sent successfully to {recipient_list}")
            return True, None
        else:
            print(f"❌ Email send returned 0 (no emails sent)")
            return False, "send_mail returned 0"
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to send email to {recipient_list}: {error_msg}")
        logger.error(f"Failed to send email to {recipient_list}: {error_msg}")
        return False, error_msg


def send_email_async(subject, message, recipient_list, html_message=None, fail_silently=True):
    """
    Send email asynchronously using threading to avoid blocking the request
    
    Args:
        subject (str): Email subject
        message (str): Plain text message
        recipient_list (list): List of recipient email addresses
        html_message (str, optional): HTML version of the message
        fail_silently (bool): If True, don't raise exceptions on failure
    
    Returns:
        threading.Thread: The thread object (for testing/debugging)
    """
    def send():
        try:
            # Small delay to ensure the main request has context
            time.sleep(0.5)
            
            # Check if email is properly configured
            if not getattr(settings, 'EMAIL_HOST_PASSWORD', ''):
                print(f"⚠️ Email not configured (no password). Would send to: {recipient_list}")
                print(f"   Subject: {subject}")
                logger.warning(f"Email not sent - EMAIL_HOST_PASSWORD not configured")
                return
            
            print(f"📤 [Thread] Sending email to {recipient_list}...")
            
            result = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,  # Always get the error for logging
            )
            
            if result:
                print(f"✅ [Thread] Email sent successfully to {recipient_list}")
                logger.info(f"Email sent successfully to {recipient_list}")
            else:
                print(f"⚠️ [Thread] send_mail returned 0 for {recipient_list}")
                
        except Exception as e:
            print(f"❌ [Thread] Failed to send email to {recipient_list}: {str(e)}")
            logger.error(f"Failed to send email to {recipient_list}: {str(e)}")
            if not fail_silently:
                raise
    
    # Create and start the thread
    # Use daemon=False so thread completes even if main request ends
    email_thread = threading.Thread(target=send, daemon=False)
    email_thread.start()
    
    return email_thread


def send_otp_email_async(email, otp, fullname="User"):
    """
    Send OTP email asynchronously for registration
    """
    subject = "Smart Face Proctor - Email Verification OTP"
    message = f"""
Dear {fullname},

Thank you for registering with Smart Face Proctor!

Your OTP for email verification is: {otp}

This OTP is valid for 15 minutes.

If you did not request this registration, please ignore this email.

Best regards,
Smart Face Proctor Team
    """
    
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
            .otp-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; 
                      text-align: center; border: 3px dashed #667eea; }}
            .otp {{ font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 5px; 
                  font-family: 'Courier New', monospace; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Email Verification</h1>
            </div>
            <div class="content">
                <p>Dear {fullname},</p>
                
                <p>Thank you for registering with Smart Face Proctor!</p>
                
                <div class="otp-box">
                    <p style="margin: 0; color: #666;">Your verification code is:</p>
                    <div class="otp">{otp}</div>
                </div>
                
                <p><strong>⏰ This OTP is valid for 15 minutes.</strong></p>
                
                <p>If you did not request this registration, please ignore this email.</p>
                
                <div class="footer">
                    <p>This is an automated message from Smart Face Proctor System</p>
                    <p>Please do not reply to this email</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    print(f"🔑 OTP for {email}: {otp}")  # Log OTP for debugging
    
    return send_email_async(
        subject=subject,
        message=message,
        recipient_list=[email],
        html_message=html_message,
        fail_silently=True
    )


def send_credentials_email_async(email, username, password, fullname, role):
    """
    Send login credentials email asynchronously after successful registration
    """
    subject = "Smart Face Proctor - Your Login Credentials"
    
    site_url = getattr(settings, 'SITE_URL', 'https://smartfaceproctor.onrender.com')
    
    message = f"""
Dear {fullname},

Your registration has been completed successfully!

Your login credentials are:
Username: {username}
Password: {password}

Role: {role}

Please login at: {site_url}/login/

Important: Please change your password after first login for security.

Best regards,
Smart Face Proctor Team
    """
    
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
            .credentials-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; 
                              border: 2px solid #28a745; }}
            .credential-row {{ margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
            .label {{ font-weight: bold; color: #667eea; }}
            .value {{ font-size: 18px; font-weight: bold; color: #2a2e94; 
                    font-family: 'Courier New', monospace; }}
            .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; 
                      padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✅ Registration Successful!</h1>
            </div>
            <div class="content">
                <p>Dear {fullname},</p>
                
                <p>Congratulations! Your account has been created successfully.</p>
                
                <div class="credentials-box">
                    <h3 style="color: #667eea; margin-top: 0;">Your Login Credentials</h3>
                    
                    <div class="credential-row">
                        <div class="label">Username</div>
                        <div class="value">{username}</div>
                    </div>
                    
                    <div class="credential-row">
                        <div class="label">Password</div>
                        <div class="value">{password}</div>
                    </div>
                    
                    <div class="credential-row">
                        <div class="label">Role</div>
                        <div class="value" style="color: #28a745;">{role}</div>
                    </div>
                </div>
                
                <div class="warning">
                    <strong>⚠️ Important Security Notice:</strong><br>
                    Please save these credentials in a secure location and change your password after first login.
                </div>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{site_url}/login/" 
                       style="display: inline-block; padding: 12px 30px; background: #667eea; 
                              color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Login Now
                    </a>
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
    
    print(f"🔐 Credentials for {email}: Username={username}")  # Log for debugging
    
    return send_email_async(
        subject=subject,
        message=message,
        recipient_list=[email],
        html_message=html_message,
        fail_silently=True
    )


def send_password_reset_otp_async(email, otp, username="User"):
    """
    Send password reset OTP email asynchronously
    """
    subject = "Smart Face Proctor - Password Reset OTP"
    message = f"""
Dear {username},

You have requested to reset your password for Smart Face Proctor.

Your OTP for password reset is: {otp}

This OTP is valid for 15 minutes.

If you did not request this, please ignore this email and your password will remain unchanged.

Best regards,
Smart Face Proctor Team
    """
    
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
            .otp-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; 
                      text-align: center; border: 3px dashed #667eea; }}
            .otp {{ font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 5px; 
                  font-family: 'Courier New', monospace; }}
            .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; 
                      padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔑 Password Reset Request</h1>
            </div>
            <div class="content">
                <p>Dear {username},</p>
                
                <p>You have requested to reset your password for Smart Face Proctor.</p>
                
                <div class="otp-box">
                    <p style="margin: 0; color: #666;">Your password reset code is:</p>
                    <div class="otp">{otp}</div>
                </div>
                
                <p><strong>⏰ This OTP is valid for 15 minutes.</strong></p>
                
                <div class="warning">
                    <strong>⚠️ Security Notice:</strong><br>
                    If you did not request this password reset, please ignore this email. Your password will remain unchanged.
                </div>
                
                <div class="footer">
                    <p>This is an automated message from Smart Face Proctor System</p>
                    <p>Please do not reply to this email</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    print(f"🔑 Password Reset OTP for {email}: {otp}")  # Log for debugging
    
    return send_email_async(
        subject=subject,
        message=message,
        recipient_list=[email],
        html_message=html_message,
        fail_silently=True
    )
