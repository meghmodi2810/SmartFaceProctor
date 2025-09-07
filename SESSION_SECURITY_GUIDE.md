# Session Management & Security Guide

## Overview
This document outlines the comprehensive session management and security features implemented in the Proctor System.

## Features Implemented

### 1. Enhanced Session Configuration
- **Custom session cookie names** for security through obscurity
- **HTTPOnly cookies** to prevent XSS attacks
- **SameSite protection** against CSRF attacks
- **Configurable session timeouts** based on user roles
- **Session regeneration** on login for security

### 2. Session Security Middleware
- **SessionSecurityMiddleware**: Monitors session activity and detects suspicious behavior
- **ExamSessionMiddleware**: Specialized handling for exam sessions to prevent cheating
- **SessionCleanupMiddleware**: Automatic cleanup of expired sessions

### 3. Advanced Authentication Features
- **Rate limiting** on login attempts (5 for regular users, 3 for admins)
- **Session hijacking detection** via User-Agent monitoring
- **Remember me functionality** with extended session timeouts
- **Automatic logout** on suspicious activity
- **Enhanced admin login** with stricter security measures

### 4. Session Monitoring & Management
- **Admin session dashboard** for monitoring all active sessions
- **User session tracking** with detailed information
- **Suspicious session detection** and automatic termination
- **Session statistics** and analytics
- **Manual session termination** capabilities

## Security Settings

### Development Settings (Current)
```python
# Session Settings
SESSION_COOKIE_SECURE = False  # Set to True in production
CSRF_COOKIE_SECURE = False     # Set to True in production
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
```

### Production Settings (Recommended)
```python
# Session Settings for Production
SESSION_COOKIE_SECURE = True      # Requires HTTPS
CSRF_COOKIE_SECURE = True         # Requires HTTPS
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'  # Stricter CSRF protection
CSRF_COOKIE_SAMESITE = 'Strict'

# Additional Security Headers
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Session Security
SESSION_COOKIE_AGE = 1800          # 30 minutes for regular users
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
```

## Session Timeouts by Role

| Role | Default Timeout | Remember Me Timeout | Max Admin Timeout |
|------|----------------|--------------------|--------------------|
| Student | 30 minutes | 2 weeks | N/A |
| Faculty | 30 minutes | 2 weeks | N/A |
| Admin | 1 hour | 8 hours | 8 hours |

## Session Data Tracked

### Security Information
- `session_start`: Timestamp when session was created
- `last_activity`: Last activity timestamp
- `user_agent`: Browser user agent string
- `ip_address`: Client IP address
- `login_count`: Number of logins in this session

### User Context
- `user_role`: User's role (Student/Faculty/Admin)
- `is_admin_session`: Boolean flag for admin sessions

### Exam Context
- `in_exam`: Boolean flag indicating if user is taking an exam
- `exam_start_time`: When the exam session started
- `exam_session_id`: Unique identifier for exam session

## Management Commands

### Session Cleanup Command
```bash
# Basic cleanup
python manage.py cleanup_sessions

# Dry run to see what would be cleaned
python manage.py cleanup_sessions --dry-run

# Force cleanup of suspicious sessions
python manage.py cleanup_sessions --force-cleanup

# Custom limits
python manage.py cleanup_sessions --max-sessions-per-user 3 --max-session-age-hours 12
```

## Admin Interface

### Session Monitoring Dashboard
- Access: `/customadmin/sessions/`
- Features:
  - Real-time session statistics
  - Active session listing
  - Suspicious session detection
  - Bulk session termination
  - Session cleanup tools

### User Session Management
- Access: `/customadmin/sessions/user/<user_id>/`
- Features:
  - View all sessions for a specific user
  - Terminate individual sessions
  - Terminate all user sessions
  - Session history and analytics

## Security Features

### 1. Session Hijacking Prevention
- User-Agent validation on each request
- IP address monitoring (optional)
- Session key regeneration on login
- Automatic logout on suspicious activity

### 2. Exam Security
- Single session enforcement during exams
- Exam session timeout monitoring
- Automatic violation logging
- Session termination on multiple tab detection

### 3. Rate Limiting
- Login attempt limiting per username
- Progressive delay on failed attempts
- Temporary account lockout after threshold
- Different limits for admin vs regular users

### 4. Suspicious Activity Detection
- Multiple concurrent sessions from different IPs
- Sessions lasting longer than 24 hours
- Exam sessions exceeding normal duration
- Corrupted or malformed session data

## API Endpoints

### Session Management APIs
- `POST /customadmin/sessions/action/` - Session management actions
- `GET /customadmin/sessions/` - Session monitoring dashboard
- `POST /customadmin/sessions/user/<id>/` - User session management

## Logging and Monitoring

### Session Events Logged
- User login/logout events
- Session security violations
- Suspicious session detection
- Administrative session terminations
- Session cleanup activities

### Monitoring Recommendations
1. Set up alerts for multiple failed login attempts
2. Monitor for unusual session patterns
3. Regular session cleanup (daily recommended)
4. Review suspicious session reports weekly
5. Monitor exam session violations

## Best Practices

### For Administrators
1. Regularly review session statistics
2. Clean up expired sessions daily
3. Monitor for suspicious activities
4. Use strong passwords and 2FA (when implemented)
5. Log out properly after admin tasks

### For Users
1. Always log out when finished
2. Don't share login credentials
3. Use private/incognito mode for exams
4. Report suspicious activity immediately
5. Keep browsers updated

### For Production Deployment
1. Enable HTTPS and set secure cookie flags
2. Configure proper session timeouts
3. Set up automated session cleanup
4. Monitor session security logs
5. Implement IP whitelisting for admin access

## Troubleshooting

### Common Issues
1. **Sessions expiring too quickly**: Adjust `SESSION_COOKIE_AGE`
2. **Users can't login**: Check rate limiting settings
3. **Exam sessions terminating**: Review exam session middleware
4. **Suspicious session alerts**: Verify IP/User-Agent changes

### Debug Commands
```bash
# Check session statistics
python manage.py shell -c "from core.session_utils import SessionManager; print(SessionManager.get_session_statistics())"

# List suspicious sessions
python manage.py shell -c "from core.session_utils import SessionSecurity; print(SessionSecurity.detect_suspicious_sessions())"

# Manual session cleanup
python manage.py cleanup_sessions --dry-run
```

## Future Enhancements

### Planned Features
1. Two-factor authentication integration
2. Device fingerprinting
3. Geolocation-based session validation
4. Advanced session analytics
5. Real-time session monitoring dashboard

### Security Improvements
1. Machine learning-based anomaly detection
2. Behavioral analysis for session validation
3. Integration with security information systems
4. Advanced threat detection capabilities

## Compliance Notes

This session management system helps meet various security compliance requirements:
- **GDPR**: Proper session data handling and cleanup
- **FERPA**: Student data protection during sessions
- **SOC 2**: Security controls and monitoring
- **ISO 27001**: Information security management

## Support

For issues related to session management:
1. Check the session monitoring dashboard
2. Review system logs for errors
3. Run session cleanup commands
4. Contact system administrators

---

**Last Updated**: August 2025
**Version**: 1.0
**Maintainer**: Proctor System Development Team
