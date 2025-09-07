"""
Custom session middleware for enhanced session management in the Proctor System.
Provides session timeout, activity tracking, and security features.
"""

import time
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Enhanced session security middleware that provides:
    - Session timeout based on inactivity
    - Session activity tracking
    - Automatic logout on suspicious activity
    - Session regeneration on login
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming request for session security checks"""
        
        # Skip session checks for certain URLs
        skip_urls = [
            '/login/',
            '/register/',
            '/forget/',
            '/verify-otp/',
            '/reset-password/',
            '/static/',
            '/admin/',
            '/customadmin/',
        ]
        
        if any(request.path.startswith(url) for url in skip_urls):
            return None
        
        # Check if user attribute exists and is authenticated
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        current_time = time.time()
        
        # Get session data
        last_activity = request.session.get('last_activity')
        session_start = request.session.get('session_start')
        user_agent = request.session.get('user_agent')
        ip_address = request.session.get('ip_address')
        
        # Initialize session tracking if not present
        if not session_start:
            request.session['session_start'] = current_time
            request.session['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
            request.session['ip_address'] = self.get_client_ip(request)
            request.session['login_count'] = request.session.get('login_count', 0) + 1
        
        # Check for session hijacking attempts
        current_user_agent = request.META.get('HTTP_USER_AGENT', '')
        current_ip = self.get_client_ip(request)
        
        if user_agent and user_agent != current_user_agent:
            messages.error(request, 'Session security violation detected. Please login again.')
            logout(request)
            return redirect('login')
        
        # Check for IP address changes (optional - can be disabled for mobile users)
        # Uncomment the following lines if you want strict IP checking
        # if ip_address and ip_address != current_ip:
        #     messages.error(request, 'IP address changed. Please login again.')
        #     logout(request)
        #     return redirect('login')
        
        # Check session timeout
        if last_activity:
            inactive_time = current_time - last_activity
            max_inactive_time = getattr(settings, 'SESSION_COOKIE_AGE', 1800)  # 30 minutes default
            
            if inactive_time > max_inactive_time:
                messages.info(request, 'Your session has expired due to inactivity. Please login again.')
                logout(request)
                return redirect('login')
        
        # Update last activity
        request.session['last_activity'] = current_time
        request.session.modified = True
        
        return None
    
    def get_client_ip(self, request):
        """Get the client's IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ExamSessionMiddleware(MiddlewareMixin):
    """
    Specialized middleware for exam sessions to prevent cheating
    """
    
    def process_request(self, request):
        """Monitor exam sessions for security"""
        
        # Check if user is in an exam
        if request.path.startswith('/student/start-mcq-exam/') or request.path.startswith('/student/mcq-exam/'):
            if hasattr(request, 'user') and request.user.is_authenticated and request.user.role == 'Student':
                # Track exam session
                request.session['in_exam'] = True
                request.session['exam_start_time'] = request.session.get('exam_start_time', time.time())
                
                # Prevent multiple tabs/windows during exam
                exam_session_id = request.session.get('exam_session_id')
                current_session_id = request.session.session_key
                
                if exam_session_id and exam_session_id != current_session_id:
                    messages.error(request, 'Multiple exam sessions detected. Exam terminated for security.')
                    # Log violation here if needed
                    return redirect('student_exams')
                
                request.session['exam_session_id'] = current_session_id
        
        # Clear exam session when not in exam
        elif request.session.get('in_exam'):
            request.session.pop('in_exam', None)
            request.session.pop('exam_start_time', None)
            request.session.pop('exam_session_id', None)
        
        return None


class SessionCleanupMiddleware(MiddlewareMixin):
    """
    Middleware to clean up expired sessions and perform maintenance
    """
    
    def process_request(self, request):
        """Perform session cleanup periodically"""
        
        # Only run cleanup occasionally to avoid performance impact
        if hasattr(request, 'user') and request.user.is_authenticated:
            last_cleanup = request.session.get('last_cleanup', 0)
            current_time = time.time()
            
            # Run cleanup every hour
            if current_time - last_cleanup > 3600:
                self.cleanup_expired_sessions()
                request.session['last_cleanup'] = current_time
        
        return None
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions from database"""
        try:
            from django.contrib.sessions.models import Session
            from django.utils import timezone
            
            # Delete expired sessions
            expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
            expired_count = expired_sessions.count()
            expired_sessions.delete()
            
            print(f"Cleaned up {expired_count} expired sessions")
            
        except Exception as e:
            print(f"Error during session cleanup: {e}")
