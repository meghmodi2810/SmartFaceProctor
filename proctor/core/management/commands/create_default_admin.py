"""
Management command to create a default admin user for deployment.
This is safe to run multiple times - it will skip if admin already exists.
Usage: python manage.py create_default_admin
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError


class Command(BaseCommand):
    help = 'Create default admin user for Smart Face Proctor system deployment'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Default admin credentials
        username = 'admin'
        password = 'Admin@123'
        email = 'admin@smartfaceproctor.com'
        first_name = 'System'
        last_name = 'Administrator'
        
        # Check if admin already exists (by username or email)
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'⚠️  Admin user "{username}" already exists. Skipping creation.'))
            return
        
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'⚠️  User with email "{email}" already exists. Skipping creation.'))
            return
        
        # Create the default admin user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='Admin',
                is_staff=True,
                is_superuser=True,
                is_active=True,
                is_profile_complete=True,
            )
            
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('✅ DEFAULT ADMIN USER CREATED SUCCESSFULLY!'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.WARNING('📋 CREDENTIALS:'))
            self.stdout.write(self.style.WARNING(f'   Username: {username}'))
            self.stdout.write(self.style.WARNING(f'   Password: {password}'))
            self.stdout.write(self.style.WARNING(f'   Email: {email}'))
            self.stdout.write(self.style.WARNING(f'   Role: Admin'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.NOTICE('⚠️  IMPORTANT: Change the password after first login for security!'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'❌ Error creating admin user (IntegrityError): {str(e)}'))
            self.stdout.write(self.style.WARNING('This usually means the user already exists.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error creating admin user: {str(e)}'))
