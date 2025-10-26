from django.core.management.base import BaseCommand
from django.utils import timezone
from ...monitoring_cleanup import cleanup_exam_monitoring

class Command(BaseCommand):
    help = 'Cleanup exam monitoring for ended exams'

    def handle(self, *args, **options):
        self.stdout.write(f"[{timezone.now()}] Running exam monitoring cleanup...")
        cleanup_exam_monitoring()
        self.stdout.write(self.style.SUCCESS(f"[{timezone.now()}] Cleanup completed"))