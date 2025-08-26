from django.core.management.base import BaseCommand
from core.models import User
from core.Modules.send_email_using_sheets import SmartFaceProctorMailer

class Command(BaseCommand):
    help = 'Test password reset functionality'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email address to test password reset')

    def handle(self, *args, **options):
        email = options['email']
        
        try:
            # Check if user exists
            user = User.objects.get(email=email)
            self.stdout.write(f"Found user: {user.username} ({user.get_full_name()})")
            
            # Test password reset
            mailer = SmartFaceProctorMailer()
            result = mailer.send_password_reset_email(email)
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f"Password reset successful! Email sent to {email}")
                )
                self.stdout.write(f"New password: {result.get('new_password', 'N/A')}")
            else:
                self.stdout.write(
                    self.style.ERROR(f"Password reset failed: {result['error']}")
                )
                
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"No user found with email: {email}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error: {str(e)}")
            ) 