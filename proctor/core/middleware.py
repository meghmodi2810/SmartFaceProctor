from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.conf import settings
from django.contrib import messages
from .models import Department

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
        if request.user.is_authenticated and request.user.role == 'Student':
            # Exempt URLs that should be accessible even without a complete profile
            exempt_paths = [
                '/student/profile/update/',
                '/logout/',
                '/static/',
            ]
            
            # Check if current path is exempt
            is_exempt = any(request.path.startswith(path) for path in exempt_paths)
            
            if not request.user.is_profile_complete and not is_exempt:
                messages.warning(request, 'Please complete your profile before continuing.')
                return redirect('/student/profile/update/')
        
        response = self.get_response(request)
        return response