"""
Admin views for session management and monitoring
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.utils import timezone
from .admin_views import admin_required
from .session_utils import SessionManager, SessionSecurity
from .models import User


@admin_required
def admin_session_monitor(request):
    """Session monitoring dashboard for admins"""
    
    # Get session statistics
    stats = SessionManager.get_session_statistics()
    
    # Get active sessions
    active_sessions = SessionManager.get_active_sessions()
    
    # Get suspicious sessions
    suspicious_sessions = SessionSecurity.detect_suspicious_sessions()
    
    # Process actions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'cleanup_expired':
            expired_count = SessionManager.cleanup_expired_sessions()
            messages.success(request, f'Cleaned up {expired_count} expired sessions.')
            
        elif action == 'terminate_suspicious':
            terminated_count = SessionSecurity.force_logout_suspicious_sessions()
            messages.success(request, f'Terminated {terminated_count} suspicious sessions.')
            
        elif action == 'terminate_session':
            session_key = request.POST.get('session_key')
            try:
                session = Session.objects.get(session_key=session_key)
                session.delete()
                messages.success(request, 'Session terminated successfully.')
            except Session.DoesNotExist:
                messages.error(request, 'Session not found.')
                
        elif action == 'terminate_user_sessions':
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                terminated_count = SessionManager.terminate_user_sessions(user)
                messages.success(request, f'Terminated {terminated_count} sessions for user {user.username}.')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
        
        return redirect('admin_session_monitor')
    
    context = {
        'admin': request.user,
        'stats': stats,
        'active_sessions': active_sessions,
        'suspicious_sessions': suspicious_sessions,
        'total_active': len(active_sessions),
        'total_suspicious': len(suspicious_sessions)
    }
    
    return render(request, 'admin_session_monitor.html', context)


@admin_required
def admin_user_sessions(request, user_id):
    """View all sessions for a specific user"""
    try:
        user = User.objects.get(id=user_id)
        user_sessions = SessionManager.get_user_sessions(user)
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'terminate_all':
                terminated_count = SessionManager.terminate_user_sessions(user)
                messages.success(request, f'Terminated {terminated_count} sessions for {user.username}.')
                return redirect('admin_user_sessions', user_id=user_id)
            
            elif action == 'terminate_session':
                session_key = request.POST.get('session_key')
                try:
                    session = Session.objects.get(session_key=session_key)
                    session.delete()
                    messages.success(request, 'Session terminated successfully.')
                except Session.DoesNotExist:
                    messages.error(request, 'Session not found.')
                return redirect('admin_user_sessions', user_id=user_id)
        
        context = {
            'admin': request.user,
            'target_user': user,
            'user_sessions': user_sessions,
            'session_count': len(user_sessions)
        }
        
        return render(request, 'admin_user_sessions.html', context)
        
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('admin_users')


@admin_required
@require_POST
def admin_session_action(request):
    """Handle AJAX session actions"""
    action = request.POST.get('action')
    
    if action == 'get_session_details':
        session_key = request.POST.get('session_key')
        try:
            session = Session.objects.get(session_key=session_key)
            session_data = session.get_decoded()
            
            details = {
                'session_key': session_key,
                'expire_date': session.expire_date.isoformat(),
                'last_activity': session_data.get('last_activity'),
                'ip_address': session_data.get('ip_address', 'Unknown'),
                'user_agent': session_data.get('user_agent', 'Unknown'),
                'login_count': session_data.get('login_count', 0),
                'in_exam': session_data.get('in_exam', False),
                'is_admin_session': session_data.get('is_admin_session', False),
                'session_start': session_data.get('session_start'),
                'user_role': session_data.get('user_role', 'Unknown')
            }
            
            return JsonResponse({'success': True, 'details': details})
            
        except Session.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Session not found'})
    
    elif action == 'refresh_stats':
        stats = SessionManager.get_session_statistics()
        return JsonResponse({'success': True, 'stats': stats})
    
    return JsonResponse({'success': False, 'error': 'Invalid action'})
