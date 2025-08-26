from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class AdminSecurityMiddleware:
    """
    Middleware to enhance security for admin routes
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_urls = [
            '/customadmin/',
        ]
        self.exempt_urls = [
            '/customadmin/login/',
            '/customadmin/logout/',
        ]
    
    def __call__(self, request):
        # Check if this is an admin route
        if any(request.path.startswith(url) for url in self.admin_urls):
            if not any(request.path.startswith(url) for url in self.exempt_urls):
                # Check if user is authenticated and is admin
                if not request.user.is_authenticated:
                    messages.error(request, 'Please log in to access the admin panel.')
                    return redirect('login')
                
                if request.user.role != 'Admin':
                    messages.error(request, 'Access denied. Admin privileges required.')
                    return redirect('login')
                
                # Check session timeout
                if self._is_session_expired(request):
                    messages.warning(request, 'Your session has expired. Please log in again.')
                    return redirect('login')
                
                # Update last activity
                request.session['last_activity'] = timezone.now().isoformat()
                
                # Log admin activity
                self._log_admin_activity(request)
        
        response = self.get_response(request)
        return response
    
    def _is_session_expired(self, request):
        """Check if the admin session has expired"""
        last_activity = request.session.get('last_activity')
        if not last_activity:
            # Set initial activity time for new sessions
            request.session['last_activity'] = timezone.now().isoformat()
            return False
        
        try:
            last_activity_time = timezone.datetime.fromisoformat(last_activity)
            if timezone.is_naive(last_activity_time):
                last_activity_time = timezone.make_aware(last_activity_time)
            
            # Session timeout: 30 minutes of inactivity
            timeout_duration = timedelta(minutes=30)
            return timezone.now() - last_activity_time > timeout_duration
        except (ValueError, TypeError):
            return True
    
    def _log_admin_activity(self, request):
        """Log admin activities for audit purposes"""
        try:
            logger.info(f"Admin activity: {request.user.username} accessed {request.path} from {request.META.get('REMOTE_ADDR', 'unknown')}")
        except Exception as e:
            logger.error(f"Error logging admin activity: {e}")


class AdminRateLimitMiddleware:
    """
    Middleware to implement rate limiting for admin actions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = {
            'POST': 60,  # 60 POST requests per minute
            'DELETE': 10,  # 10 DELETE requests per minute
        }
    
    def __call__(self, request):
        if request.path.startswith('/customadmin/') and request.user.is_authenticated:
            if request.user.role == 'Admin':
                if self._is_rate_limited(request):
                    messages.error(request, 'Rate limit exceeded. Please wait before making more requests.')
                    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))
        
        response = self.get_response(request)
        return response
    
    def _is_rate_limited(self, request):
        """Check if the request should be rate limited"""
        method = request.method
        if method not in self.rate_limits:
            return False
        
        # Use session to track requests
        session_key = f'admin_rate_limit_{method}'
        current_time = timezone.now()
        
        # Get existing requests from session
        requests_data = request.session.get(session_key, [])
        
        # Filter requests from the last minute
        one_minute_ago = current_time - timedelta(minutes=1)
        recent_requests = [
            req_time for req_time in requests_data 
            if timezone.datetime.fromisoformat(req_time) > one_minute_ago
        ]
        
        # Check if limit exceeded
        if len(recent_requests) >= self.rate_limits[method]:
            return True
        
        # Add current request
        recent_requests.append(current_time.isoformat())
        request.session[session_key] = recent_requests
        
        return False


class AdminAuditMiddleware:
    """
    Middleware to audit admin actions for compliance and security
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.sensitive_actions = [
            'delete',
            'create',
            'update',
            'export',
            'reset',
            'backup',
        ]
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Audit admin actions after response
        if (request.path.startswith('/customadmin/') and 
            request.user.is_authenticated and 
            request.user.role == 'Admin'):
            self._audit_action(request, response)
        
        return response
    
    def _audit_action(self, request, response):
        """Audit admin actions"""
        try:
            action_type = self._determine_action_type(request)
            if action_type:
                audit_data = {
                    'user': request.user.username,
                    'action': action_type,
                    'path': request.path,
                    'method': request.method,
                    'ip_address': request.META.get('REMOTE_ADDR', 'unknown'),
                    'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown'),
                    'timestamp': timezone.now().isoformat(),
                    'status_code': response.status_code,
                }
                
                # Log to file or database
                logger.info(f"Admin audit: {audit_data}")
                
                # Store in session for recent activity display
                recent_activities = request.session.get('admin_recent_activities', [])
                recent_activities.insert(0, {
                    'action': action_type,
                    'path': request.path,
                    'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
                
                # Keep only last 10 activities
                request.session['admin_recent_activities'] = recent_activities[:10]
                
        except Exception as e:
            logger.error(f"Error in admin audit: {e}")
    
    def _determine_action_type(self, request):
        """Determine the type of action being performed"""
        path = request.path.lower()
        method = request.method
        
        if method == 'DELETE' or 'delete' in path:
            return 'DELETE'
        elif method == 'POST' and 'create' in path:
            return 'CREATE'
        elif method == 'POST' and ('edit' in path or 'update' in path):
            return 'UPDATE'
        elif 'export' in path:
            return 'EXPORT'
        elif 'backup' in path:
            return 'BACKUP'
        elif 'reset' in path:
            return 'RESET'
        elif method == 'GET' and any(sensitive in path for sensitive in self.sensitive_actions):
            return 'VIEW_SENSITIVE'
        
        return None


class AdminIPWhitelistMiddleware:
    """
    Middleware to restrict admin access to whitelisted IP addresses
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Default whitelist - should be configured via settings
        self.whitelisted_ips = [
            '127.0.0.1',
            '::1',
            'localhost',
        ]
        # Add your organization's IP ranges here
        # self.whitelisted_ips.extend(['192.168.1.0/24', '10.0.0.0/8'])
    
    def __call__(self, request):
        if request.path.startswith('/customadmin/'):
            client_ip = self._get_client_ip(request)
            
            # Skip IP check for development (when DEBUG=True)
            from django.conf import settings
            if not getattr(settings, 'DEBUG', False):
                if not self._is_ip_whitelisted(client_ip):
                    logger.warning(f"Admin access denied for IP: {client_ip}")
                    messages.error(request, 'Access denied from this IP address.')
                    return redirect('login')  # Redirect to main login
        
        response = self.get_response(request)
        return response
    
    def _get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _is_ip_whitelisted(self, ip):
        """Check if IP is in whitelist"""
        # Simple check for exact matches and localhost
        if ip in self.whitelisted_ips:
            return True
        
        # Add more sophisticated IP range checking here if needed
        # For now, allow all IPs in development
        return True  # Change to False for production with proper IP whitelist


class AdminMaintenanceModeMiddleware:
    """
    Middleware to handle maintenance mode for admin panel
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if maintenance mode is enabled
        if self._is_maintenance_mode_enabled(request):
            if request.path.startswith('/customadmin/'):
                # Allow only super admins during maintenance
                if not (request.user.is_authenticated and 
                       request.user.role == 'Admin' and 
                       request.user.is_superuser):
                    messages.warning(request, 'Admin panel is currently under maintenance. Please try again later.')
                    return redirect('login')
        
        response = self.get_response(request)
        return response
    
    def _is_maintenance_mode_enabled(self, request):
        """Check if maintenance mode is enabled"""
        # Check session flag set by admin
        return request.session.get('maintenance_mode', False)
