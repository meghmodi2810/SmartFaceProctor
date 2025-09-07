"""
Session management utilities for the Proctor System.
Provides session monitoring, cleanup, and security functions.
"""

import time
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import json

User = get_user_model()


class SessionManager:
    """Utility class for managing user sessions"""
    
    @staticmethod
    def get_active_sessions():
        """Get all active sessions with user information"""
        active_sessions = []
        current_time = timezone.now()
        
        for session in Session.objects.filter(expire_date__gt=current_time):
            try:
                session_data = session.get_decoded()
                user_id = session_data.get('_auth_user_id')
                
                if user_id:
                    try:
                        user = User.objects.get(id=user_id)
                        session_info = {
                            'session_key': session.session_key,
                            'user': user,
                            'user_role': session_data.get('user_role', 'Unknown'),
                            'expire_date': session.expire_date,
                            'last_activity': session_data.get('last_activity'),
                            'ip_address': session_data.get('ip_address', 'Unknown'),
                            'user_agent': session_data.get('user_agent', 'Unknown'),
                            'login_count': session_data.get('login_count', 0),
                            'in_exam': session_data.get('in_exam', False),
                            'is_admin_session': session_data.get('is_admin_session', False)
                        }
                        active_sessions.append(session_info)
                    except User.DoesNotExist:
                        # Session exists but user doesn't - mark for cleanup
                        session.delete()
            except Exception as e:
                print(f"Error processing session {session.session_key}: {e}")
                
        return active_sessions
    
    @staticmethod
    def get_user_sessions(user):
        """Get all active sessions for a specific user"""
        user_sessions = []
        current_time = timezone.now()
        
        for session in Session.objects.filter(expire_date__gt=current_time):
            try:
                session_data = session.get_decoded()
                session_user_id = session_data.get('_auth_user_id')
                
                if session_user_id and int(session_user_id) == user.id:
                    session_info = {
                        'session_key': session.session_key,
                        'expire_date': session.expire_date,
                        'last_activity': session_data.get('last_activity'),
                        'ip_address': session_data.get('ip_address', 'Unknown'),
                        'user_agent': session_data.get('user_agent', 'Unknown'),
                        'login_count': session_data.get('login_count', 0),
                        'in_exam': session_data.get('in_exam', False),
                        'is_admin_session': session_data.get('is_admin_session', False)
                    }
                    user_sessions.append(session_info)
            except Exception as e:
                print(f"Error processing session for user {user.username}: {e}")
                
        return user_sessions
    
    @staticmethod
    def terminate_user_sessions(user, exclude_session_key=None):
        """Terminate all sessions for a specific user"""
        terminated_count = 0
        current_time = timezone.now()
        
        for session in Session.objects.filter(expire_date__gt=current_time):
            if exclude_session_key and session.session_key == exclude_session_key:
                continue
                
            try:
                session_data = session.get_decoded()
                session_user_id = session_data.get('_auth_user_id')
                
                if session_user_id and int(session_user_id) == user.id:
                    session.delete()
                    terminated_count += 1
            except Exception as e:
                print(f"Error terminating session: {e}")
                
        return terminated_count
    
    @staticmethod
    def cleanup_expired_sessions():
        """Clean up expired sessions"""
        current_time = timezone.now()
        expired_sessions = Session.objects.filter(expire_date__lt=current_time)
        expired_count = expired_sessions.count()
        expired_sessions.delete()
        return expired_count
    
    @staticmethod
    def get_session_statistics():
        """Get session statistics"""
        current_time = timezone.now()
        
        total_sessions = Session.objects.count()
        active_sessions = Session.objects.filter(expire_date__gt=current_time).count()
        expired_sessions = Session.objects.filter(expire_date__lt=current_time).count()
        
        # Count sessions by role
        role_counts = {'Student': 0, 'Faculty': 0, 'Admin': 0, 'Unknown': 0}
        exam_sessions = 0
        
        for session in Session.objects.filter(expire_date__gt=current_time):
            try:
                session_data = session.get_decoded()
                role = session_data.get('user_role', 'Unknown')
                role_counts[role] = role_counts.get(role, 0) + 1
                
                if session_data.get('in_exam', False):
                    exam_sessions += 1
            except Exception:
                role_counts['Unknown'] += 1
        
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'expired_sessions': expired_sessions,
            'role_counts': role_counts,
            'exam_sessions': exam_sessions
        }


class SessionSecurity:
    """Security utilities for session management"""
    
    @staticmethod
    def detect_suspicious_sessions():
        """Detect potentially suspicious sessions"""
        suspicious_sessions = []
        current_time = timezone.now()
        
        for session in Session.objects.filter(expire_date__gt=current_time):
            try:
                session_data = session.get_decoded()
                user_id = session_data.get('_auth_user_id')
                
                if not user_id:
                    continue
                
                # Check for multiple sessions from different IPs
                user_sessions = SessionManager.get_user_sessions(User.objects.get(id=user_id))
                if len(user_sessions) > 3:  # More than 3 concurrent sessions
                    suspicious_sessions.append({
                        'type': 'multiple_sessions',
                        'user_id': user_id,
                        'session_count': len(user_sessions),
                        'session_key': session.session_key
                    })
                
                # Check for very long sessions
                session_start = session_data.get('session_start')
                if session_start:
                    session_duration = time.time() - session_start
                    if session_duration > 86400:  # More than 24 hours
                        suspicious_sessions.append({
                            'type': 'long_session',
                            'user_id': user_id,
                            'duration_hours': session_duration / 3600,
                            'session_key': session.session_key
                        })
                
                # Check for exam sessions that are too long
                if session_data.get('in_exam', False):
                    exam_start = session_data.get('exam_start_time')
                    if exam_start and (time.time() - exam_start) > 10800:  # More than 3 hours
                        suspicious_sessions.append({
                            'type': 'long_exam_session',
                            'user_id': user_id,
                            'exam_duration_hours': (time.time() - exam_start) / 3600,
                            'session_key': session.session_key
                        })
                        
            except Exception as e:
                print(f"Error checking session security: {e}")
        
        return suspicious_sessions
    
    @staticmethod
    def force_logout_suspicious_sessions():
        """Force logout of suspicious sessions"""
        suspicious_sessions = SessionSecurity.detect_suspicious_sessions()
        terminated_count = 0
        
        for suspicious in suspicious_sessions:
            try:
                session = Session.objects.get(session_key=suspicious['session_key'])
                session.delete()
                terminated_count += 1
                print(f"Terminated suspicious session: {suspicious['type']} for user {suspicious['user_id']}")
            except Session.DoesNotExist:
                pass
            except Exception as e:
                print(f"Error terminating suspicious session: {e}")
        
        return terminated_count
