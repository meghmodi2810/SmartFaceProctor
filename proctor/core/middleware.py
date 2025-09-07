from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs that can be accessed without login
        exempt_urls = [
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

        # Check if the path starts with any exempt URL
        for exempt_url in exempt_urls:
            if request.path.startswith(exempt_url):
                return self.get_response(request)

        if not request.user.is_authenticated and request.path not in exempt_urls:
            return redirect('login')

        response = self.get_response(request)
        return response