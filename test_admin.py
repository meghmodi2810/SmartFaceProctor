#!/usr/bin/env python
"""
Test script for the custom admin functionality
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proctor.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import User, Exam, Question, Submission, Violation, BugReport

def create_test_admin():
    """Create a test admin user"""
    User = get_user_model()
    
    # Check if admin already exists
    admin_username = 'admin'
    if User.objects.filter(username=admin_username).exists():
        print(f"Admin user {admin_username} already exists")
        return User.objects.get(username=admin_username)
    
    # Create admin user
    admin_user = User.objects.create_user(
        username=admin_username,
        email='admin@smartfaceproctor.com',
        password='admin123',
        first_name='System',
        last_name='Administrator',
        role='Admin'
    )
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()
    
    print(f"Created admin user: {admin_username}")
    return admin_user

def create_test_data():
    """Create some test data for the admin to manage"""
    User = get_user_model()
    
    # Create test students
    for i in range(1, 6):
        username = f'student{i:03d}'
        if not User.objects.filter(username=username).exists():
            User.objects.create_user(
                username=username,
                email=f'student{i}@example.com',
                password='Student@123',
                first_name=f'Student',
                last_name=f'User{i}',
                role='Student'
            )
    
    # Create test faculty
    for i in range(1, 3):
        username = f'faculty{i:03d}'
        if not User.objects.filter(username=username).exists():
            User.objects.create_user(
                username=username,
                email=f'faculty{i}@example.com',
                password='Faculty@123',
                first_name=f'Faculty',
                last_name=f'Member{i}',
                role='Faculty'
            )
    
    print("Created test users (students and faculty)")

def verify_admin_urls():
    """Verify that admin URLs are properly configured"""
    from django.urls import reverse, NoReverseMatch
    
    admin_urls = [
        'admin_login',
        'admin_dashboard',
        'admin_users',
        'admin_exams',
        'admin_submissions',
        'admin_violations',
        'admin_bug_reports',
        'admin_settings',
        'admin_export',
        'admin_logout',
    ]
    
    print("Verifying admin URL patterns...")
    for url_name in admin_urls:
        try:
            url = reverse(url_name)
            print(f"✓ {url_name}: {url}")
        except NoReverseMatch as e:
            print(f"✗ {url_name}: {e}")

def check_database_tables():
    """Check if all required database tables exist"""
    from django.db import connection
    
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = [table[0] for table in cursor.fetchall()]
    
    required_tables = [
        'core_user',
        'core_exam',
        'core_question',
        'core_submission',
        'core_violation',
        'core_bugreport',
        'core_passwordresetotp',
    ]
    
    print("Checking database tables...")
    for table in required_tables:
        if table in tables:
            print(f"✓ {table}")
        else:
            print(f"✗ {table} - Missing!")

def main():
    """Main test function"""
    print("=" * 50)
    print("SMART FACE PROCTOR - ADMIN SYSTEM TEST")
    print("=" * 50)
    
    try:
        # Check database tables
        check_database_tables()
        print()
        
        # Verify URL patterns
        verify_admin_urls()
        print()
        
        # Create test admin user
        admin_user = create_test_admin()
        print()
        
        # Create test data
        create_test_data()
        print()
        
        print("=" * 50)
        print("TEST COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print(f"Admin Login URL: http://localhost:8000/customadmin/login/")
        print(f"Admin Username: {admin_user.username}")
        print(f"Admin Password: admin123")
        print("=" * 50)
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
