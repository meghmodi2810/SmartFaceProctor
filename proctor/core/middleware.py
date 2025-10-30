from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.conf import settings
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from .models import Department
from .monitoring_cleanup import cleanup_exam_monitoring
import logging

logger = logging.getLogger(__name__)

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs that can be accessed without login
        exempt_urls = [
            '/',  # Home page
            '/static/',  # Static files
            reverse('login'),
            reverse('register'),
            reverse('forget'),
            reverse('verify_otp'),
            reverse('reset_password'),
            reverse('test_otp'),
            reverse('check_database'),
            reverse('check_migration'),
        ]
        
        # Check if the path starts with admin URL or custom admin
        if request.path.startswith('/admin/') or request.path.startswith('/customadmin/'):
            return self.get_response(request)

        # Check if the path is for static files
        if request.path.startswith(settings.STATIC_URL):
            return self.get_response(request)

        # Check if the path starts with any exempt URL
        for exempt_url in exempt_urls:
            if request.path.startswith(exempt_url):
                return self.get_response(request)

        if not request.user.is_authenticated and request.path not in exempt_urls:
            return redirect('login')

        response = self.get_response(request)
        return response

class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Get exempt URLs using reverse to avoid hardcoding paths
            exempt_urls = [
                reverse('login'),
                reverse('logout'),
                reverse('faculty_profile'),
                reverse('faculty_password_change'),
                reverse('faculty_dashboard'),  # Using reverse instead of hardcoded path
                reverse('student_profile'),
                reverse('student_profile_update'),
                reverse('report_bug'),
                '/static/',  # Static files don't have reverse URLs
                settings.STATIC_URL,  # Additional static files path
            ]
            
            current_url = request.path
            
            # Check if current URL is exempt
            is_exempt = any(current_url.startswith(url) for url in exempt_urls)
            
            # If user hasn't completed their profile and trying to access a non-exempt URL
            if not request.user.is_profile_complete and not is_exempt:
                if request.user.role == 'Student':
                    messages.info(request, 'Please complete your profile to continue.')
                    return redirect('student_profile')
                elif request.user.role == 'Faculty':
                    messages.info(request, 'Please complete your profile to continue.')
                    return redirect('faculty_profile')
        
        return self.get_response(request)

class ExamMonitoringMiddleware(MiddlewareMixin):
    """Middleware to handle exam monitoring cleanup"""
    
    def process_request(self, request):
        try:
            # Run cleanup periodically (every ~5 minutes)
            from django.core.cache import cache
            last_cleanup = cache.get('last_monitoring_cleanup')
            if not last_cleanup or (timezone.now() - last_cleanup).total_seconds() > 300:
                cleanup_exam_monitoring(request)
                cache.set('last_monitoring_cleanup', timezone.now())
        except Exception as e:
            logger.error(f"Error in ExamMonitoringMiddleware: {e}")
        return None