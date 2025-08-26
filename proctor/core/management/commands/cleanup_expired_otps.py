from django.core.management.base import BaseCommand
from core.models import PasswordResetOTP


class Command(BaseCommand):
    help = 'Clean up expired OTPs from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get all expired OTPs
        expired_otps = []
        all_otps = PasswordResetOTP.objects.filter(is_used=False)
        
        for otp_obj in all_otps:
            if otp_obj.is_expired():
                expired_otps.append(otp_obj)
        
        if not expired_otps:
            self.stdout.write(
                self.style.SUCCESS('No expired OTPs found.')
            )
            return
        
        self.stdout.write(
            f'Found {len(expired_otps)} expired OTP(s):'
        )
        
        for otp_obj in expired_otps:
            self.stdout.write(
                f'  - {otp_obj.email}: {otp_obj.otp} (created: {otp_obj.created_at})'
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {len(expired_otps)} expired OTP(s)'
                )
            )
        else:
            # Delete expired OTPs
            count = len(expired_otps)
            for otp_obj in expired_otps:
                otp_obj.delete()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {count} expired OTP(s)'
                )
            ) 