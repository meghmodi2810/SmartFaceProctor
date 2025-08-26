import os
import json
import gspread
import random
import string
from email.message import EmailMessage
import smtplib
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

from core.models import User

class SmartFaceProctorMailer:
    def __init__(self,
                 smtp_credentials_path=None,
                 google_credentials_path=None,
                 sheet_url=None,
                 sheet_name='Sheet1',
                 password_length=12):
        if smtp_credentials_path is None:
            smtp_credentials_path = os.path.join(os.path.dirname(__file__), '../config/SMTP_credentials.json')
            smtp_credentials_path = os.path.normpath(smtp_credentials_path)
        self.smtp_credentials_path = smtp_credentials_path
        self.google_credentials_path = google_credentials_path
        self.sheet_url = sheet_url
        self.sheet_name = sheet_name
        self.password_length = password_length
        self.smtp_creds = self._load_smtp_credentials()
        if self.google_credentials_path and self.sheet_url:
            self.sheet = self._get_google_sheet()
            self.recipients = self._collect_recipients()
            print("Found these emails:", [email for _, email, _ in self.recipients])
        else:
            self.sheet = None
            self.recipients = []

    def _load_smtp_credentials(self):
        with open(self.smtp_credentials_path, 'r') as f:
            return json.load(f)

    def _get_google_sheet(self):
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.google_credentials_path, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(self.sheet_url).worksheet(self.sheet_name)
        return sheet

    def _collect_recipients(self):
        rows = self.sheet.get_all_records()
        recipients = []
        for row in rows:
            email = row.get('Email')
            user_type = row.get('User Type')
            if email and user_type:
                recipients.append((row, email, user_type.strip().lower()))
        return recipients

    def generate_user_id_and_password(self, user_type):
        user_type = user_type.strip().lower()
        if user_type == 'student':
            prefix = 'SPS'
        elif user_type == 'faculty':
            prefix = 'SPF'
        else:
            raise ValueError(f"Unknown user type: {user_type}")

        digits = ''.join(random.choices(string.digits, k=10))
        user_id = f"{prefix}-{digits}" # This would store ID like SPS-1234567890 or SPF-1234567890
        # Generate a random password
        alphabet = string.ascii_letters + string.digits
        password = ''.join(random.choices(alphabet, k=self.password_length))
        return user_id, password

    def generate_new_password(self):
        """Generate only a new password (for password reset)"""
        alphabet = string.ascii_letters + string.digits
        password = ''.join(random.choices(alphabet, k=self.password_length))
        return password

    def reset_user_password(self, email):
        """Reset password for existing user - keeps ID, generates new password"""
        try:
            # Find user by email
            user = User.objects.get(email=email)
            
            # Generate new password only
            new_password = self.generate_new_password()
            
            # Update user's password
            user.set_password(new_password)
            user.save()
            
            return {
                'success': True,
                'user_id': user.username,
                'new_password': new_password,
                'user_name': user.get_full_name() or user.username
            }
            
        except User.DoesNotExist:
            return {
                'success': False,
                'error': 'No user found with this email address.'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error resetting password: {str(e)}'
            }

    def send_email(self, recipient, subject, body):
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = self.smtp_creds['FROM_EMAIL']
        msg['To'] = recipient
        
        try:
            with smtplib.SMTP_SSL(self.smtp_creds['SMTP_HOST'], self.smtp_creds['SMTP_PORT']) as smtp:
                smtp.login(self.smtp_creds['SMTP_USER'], self.smtp_creds['SMTP_API_KEY'])
                smtp.send_message(msg)
            print(f"Sent email to {recipient}")
            return True
        except Exception as e:
            print(f"Failed to send email to {recipient}: {e}")
            return False

    def send_password_reset_email(self, email):
        """Send password reset email with existing ID and new password"""
        result = self.reset_user_password(email)
        
        if result['success']:
            subject = "Password Reset - Smart Face Proctor"
            body = f"""
            Hello {result['user_name']},
            
            Your password has been reset successfully.
            
            Your login credentials:
            ID: {result['user_id']}
            New Password: {result['new_password']}
            
            Please login with these credentials and change your password after login.
            
            Best regards,
            Smart Face Proctor Team
            """
            
            email_sent = self.send_email(email, subject, body)
            if email_sent:
                return {
                    'success': True,
                    'message': f'Password reset email sent to {email}. Please check your inbox.'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to send email. Please try again.'
                }
        else:
            return result

    def send_otp_email(self, email, otp):
        """Send OTP email for password reset"""
        try:
            # Find user by email
            from ..models import User
            user = User.objects.get(email=email)
            user_name = user.get_full_name() or user.username
            
            subject = "Password Reset OTP - Smart Face Proctor"
            body = f"""
            Hello {user_name},
            
            You have requested to reset your password.
            
            Your OTP (One-Time Password) is: {otp}
            
            This OTP is valid for 15 minutes only.
            If you didn't request this password reset, please ignore this email.
            
            Best regards,
            Smart Face Proctor Team
            """
            
            email_sent = self.send_email(email, subject, body)
            
            if email_sent:
                return {
                    'success': True,
                    'message': f'OTP sent to {email}. Please check your inbox.'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to send OTP email. Please try again.'
                }
                
        except User.DoesNotExist:
            return {
                'success': False,
                'error': 'No user found with this email address.'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error sending OTP: {str(e)}'
            }

    def create_user(self, email, user_type, user_id, password):
        """Create a user in Django database - skip if already exists"""
        try:
            # Convert user_type to match choices in model
            role = 'Student' if user_type.lower() == 'student' else 'Faculty'
            
            # Check if user with this email already exists
            if User.objects.filter(email=email).exists():
                print(f"User with email {email} already exists - skipping")
                return False  # Return False to indicate user was skipped
            
            # Create new user only if doesn't exist
            user = User.objects.create_user(
                username=user_id,
                email=email,
                password=password,
                role=role
            )
            print(f"Created new user with email {email}")
            return True
            
        except Exception as e:
            print(f"Failed to create user in database: {e}")
            return False

    def process_and_send(self, subject, body_template):
        """
        body_template should be a str with two placeholders:
        {user_id} and {password}
        """
        for row, email, user_type in self.recipients:
            try:
                user_id, password = self.generate_user_id_and_password(user_type)
                # First create the user in database
                if self.create_user(email, user_type, user_id, password):
                    # If user creation successful, send email
                    body = body_template.format(
                        user_type=user_type.title(),
                        user_id=user_id,
                        password=password
                    )
                    self.send_email(email, subject, body)
                else:
                    print(f"Skipping email for {email} due to database error")
            except Exception as e:
                print(f"Could not process user at {email}: {e}")