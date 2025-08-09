from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.models import CourseReminderLog
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up old reminder logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete reminder logs older than this many days (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        try:
            days = options['days']
            dry_run = options['dry_run']
            
            cutoff_date = timezone.now() - timedelta(days=days)
            
            old_reminders = CourseReminderLog.objects.filter(
                created_at__lt=cutoff_date
            )
            
            count = old_reminders.count()
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'DRY RUN: Would delete {count} reminder logs older than {days} days'
                    )
                )
            else:
                deleted_count, _ = old_reminders.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully deleted {deleted_count} old reminder logs'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error cleaning up reminders: {e}')
            )