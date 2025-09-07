"""
Django management command to clean up expired sessions and perform session maintenance.
Usage: python manage.py cleanup_sessions
"""

from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.utils import timezone
from datetime import timedelta
from core.session_utils import SessionManager, SessionSecurity
from core.models import User


class Command(BaseCommand):
    help = 'Clean up expired sessions and perform session maintenance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-cleanup',
            action='store_true',
            help='Force cleanup of all suspicious sessions',
        )
        parser.add_argument(
            '--max-sessions-per-user',
            type=int,
            default=5,
            help='Maximum allowed sessions per user (default: 5)',
        )
        parser.add_argument(
            '--max-session-age-hours',
            type=int,
            default=24,
            help='Maximum session age in hours (default: 24)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting session cleanup...'))
        
        # Get initial statistics
        initial_stats = SessionManager.get_session_statistics()
        self.stdout.write(f"Initial session count: {initial_stats['total_sessions']}")
        self.stdout.write(f"Active sessions: {initial_stats['active_sessions']}")
        self.stdout.write(f"Expired sessions: {initial_stats['expired_sessions']}")
        
        cleanup_count = 0
        
        # 1. Clean up expired sessions
        self.stdout.write('\n1. Cleaning up expired sessions...')
        if not options['dry_run']:
            expired_count = SessionManager.cleanup_expired_sessions()
            cleanup_count += expired_count
            self.stdout.write(
                self.style.SUCCESS(f'   Cleaned up {expired_count} expired sessions')
            )
        else:
            expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
            self.stdout.write(f'   Would clean up {expired_sessions.count()} expired sessions')
        
        # 2. Handle sessions with too many concurrent sessions per user
        self.stdout.write('\n2. Checking for users with too many concurrent sessions...')
        max_sessions = options['max_sessions_per_user']
        users_with_many_sessions = []
        
        for user in User.objects.all():
            user_sessions = SessionManager.get_user_sessions(user)
            if len(user_sessions) > max_sessions:
                users_with_many_sessions.append((user, len(user_sessions)))
                
                if not options['dry_run']:
                    # Keep only the most recent sessions
                    sessions_to_keep = max_sessions - 1
                    sorted_sessions = sorted(user_sessions, 
                                           key=lambda x: x.get('last_activity', 0), 
                                           reverse=True)
                    
                    for session_info in sorted_sessions[sessions_to_keep:]:
                        try:
                            session = Session.objects.get(session_key=session_info['session_key'])
                            session.delete()
                            cleanup_count += 1
                        except Session.DoesNotExist:
                            pass
                    
                    self.stdout.write(
                        f'   Cleaned up excess sessions for user {user.username} '
                        f'({len(user_sessions)} -> {sessions_to_keep})'
                    )
        
        if options['dry_run'] and users_with_many_sessions:
            for user, session_count in users_with_many_sessions:
                self.stdout.write(
                    f'   User {user.username} has {session_count} sessions '
                    f'(limit: {max_sessions})'
                )
        
        # 3. Clean up very old sessions
        self.stdout.write('\n3. Cleaning up very old sessions...')
        max_age_hours = options['max_session_age_hours']
        cutoff_time = timezone.now() - timedelta(hours=max_age_hours)
        
        old_sessions = []
        for session in Session.objects.filter(expire_date__gt=timezone.now()):
            try:
                session_data = session.get_decoded()
                session_start = session_data.get('session_start')
                if session_start:
                    session_start_time = timezone.datetime.fromtimestamp(
                        session_start, tz=timezone.get_current_timezone()
                    )
                    if session_start_time < cutoff_time:
                        old_sessions.append(session)
            except Exception:
                # If we can't decode the session, it's probably corrupted
                old_sessions.append(session)
        
        if not options['dry_run']:
            for session in old_sessions:
                session.delete()
                cleanup_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'   Cleaned up {len(old_sessions)} old sessions')
            )
        else:
            self.stdout.write(f'   Would clean up {len(old_sessions)} old sessions')
        
        # 4. Handle suspicious sessions
        self.stdout.write('\n4. Checking for suspicious sessions...')
        suspicious_sessions = SessionSecurity.detect_suspicious_sessions()
        
        if suspicious_sessions:
            for suspicious in suspicious_sessions:
                self.stdout.write(
                    self.style.WARNING(
                        f'   Suspicious session detected: {suspicious["type"]} '
                        f'for user {suspicious["user_id"]}'
                    )
                )
            
            if options['force_cleanup'] and not options['dry_run']:
                terminated_count = SessionSecurity.force_logout_suspicious_sessions()
                cleanup_count += terminated_count
                self.stdout.write(
                    self.style.SUCCESS(f'   Terminated {terminated_count} suspicious sessions')
                )
            elif options['dry_run']:
                self.stdout.write(f'   Would terminate {len(suspicious_sessions)} suspicious sessions')
            else:
                self.stdout.write(
                    self.style.WARNING(
                        '   Use --force-cleanup to automatically terminate suspicious sessions'
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS('   No suspicious sessions found'))
        
        # 5. Final statistics
        self.stdout.write('\n' + '='*50)
        final_stats = SessionManager.get_session_statistics()
        
        if not options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'Session cleanup completed!'))
            self.stdout.write(f'Total sessions cleaned up: {cleanup_count}')
            self.stdout.write(f'Sessions before cleanup: {initial_stats["total_sessions"]}')
            self.stdout.write(f'Sessions after cleanup: {final_stats["total_sessions"]}')
        else:
            self.stdout.write(self.style.WARNING('Dry run completed - no changes made'))
        
        self.stdout.write(f'Current active sessions: {final_stats["active_sessions"]}')
        self.stdout.write(f'Sessions by role:')
        for role, count in final_stats['role_counts'].items():
            if count > 0:
                self.stdout.write(f'  {role}: {count}')
        
        if final_stats['exam_sessions'] > 0:
            self.stdout.write(f'Active exam sessions: {final_stats["exam_sessions"]}')
        
        self.stdout.write('\nSession cleanup completed successfully!')
