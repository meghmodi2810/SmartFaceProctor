"""
Management command to create an admin user directly in the database.
Usage: python manage.py create_admin
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import random
import string


class Command(BaseCommand):
    help = 'Create an admin user for the Smart Face Proctor system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Admin username (default: auto-generated SPA-XXXXXXXXXX)',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Admin email address (required)',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Admin password (default: auto-generated 12 char)',
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default='Admin',
            help='Admin first name (default: Admin)',
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default='User',
            help='Admin last name (default: User)',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Get or generate credentials
        email = options.get('email')
        if not email:
            self.stdout.write(self.style.ERROR('Email is required. Use --email=your@email.com'))
            return
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'User with email {email} already exists!'))
            return
        
        # Generate username if not provided
        username = options.get('username')
        if not username:
            random_number = random.randint(1000000000, 9999999999)
            username = f'SPA-{random_number}'  # SPA = Smart Proctor Admin
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'Username {username} already exists!'))
            return
        
        # Generate password if not provided
        password = options.get('password')
        if not password:
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        first_name = options.get('first_name', 'Admin')
        last_name = options.get('last_name', 'User')
        
        # Create the admin user
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
            
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS('✅ Admin user created successfully!'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.WARNING(f'Username: {username}'))
            self.stdout.write(self.style.WARNING(f'Password: {password}'))
            self.stdout.write(self.style.WARNING(f'Email: {email}'))
            self.stdout.write(self.style.WARNING(f'Role: Admin'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.NOTICE('⚠️  SAVE THESE CREDENTIALS! They won\'t be shown again.'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating admin user: {str(e)}'))
