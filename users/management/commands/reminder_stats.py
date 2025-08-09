from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.models import CourseReminderLog, CourseReminderSettings
from users.services.reminder_service import reminder_service

class Command(BaseCommand):
    help = 'Show reminder statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Show statistics for the last N days (default: 7)',
        )

    def handle(self, *args, **options):
        try:
            days = options['days']
            
            self.stdout.write(f'\n=== REMINDER STATISTICS (Last {days} days) ===\n')
            
            # Get statistics from service
            stats = reminder_service.get_reminder_statistics(days)
            
            # Overall stats
            self.stdout.write('OVERALL STATISTICS:')
            self.stdout.write(f'  Total Scheduled: {stats.get("total_scheduled", 0)}')
            self.stdout.write(f'  Total Sent: {stats.get("total_sent", 0)}')
            self.stdout.write(f'  Total Failed: {stats.get("total_failed", 0)}')
            self.stdout.write(f'  Total Cancelled: {stats.get("total_cancelled", 0)}')
            self.stdout.write(f'  Skipped (DND): {stats.get("total_skipped_dnd", 0)}')
            self.stdout.write(f'  Success Rate: {stats.get("success_rate", 0)}%\n')
            
            # By type stats
            self.stdout.write('BY REMINDER TYPE:')
            by_type = stats.get('by_type', {})
            for reminder_type, type_stats in by_type.items():
                self.stdout.write(f'  {reminder_type.upper()}:')
                self.stdout.write(f'    Scheduled: {type_stats.get("scheduled", 0)}')
                self.stdout.write(f'    Sent: {type_stats.get("sent", 0)}')
                self.stdout.write(f'    Failed: {type_stats.get("failed", 0)}')
            
            # Current pending reminders
            self.stdout.write('\nCURRENT STATUS:')
            pending_count = CourseReminderLog.objects.filter(status='pending').count()
            overdue_count = CourseReminderLog.objects.filter(
                status='pending',
                scheduled_time__lt=timezone.now()
            ).count()
            
            self.stdout.write(f'  Pending Reminders: {pending_count}')
            self.stdout.write(f'  Overdue Reminders: {overdue_count}')
            
            # Settings
            settings = CourseReminderSettings.objects.first()
            if settings:
                self.stdout.write('\nCURRENT SETTINGS:')
                self.stdout.write(f'  30-min Reminders: {"Enabled" if settings.reminder_30_min_enabled else "Disabled"}')
                self.stdout.write(f'  6-hour Reminders: {"Enabled" if settings.reminder_6_hour_enabled else "Disabled"}')
                self.stdout.write(f'  Max 6-hour Reminders: {settings.max_6_hour_reminders}')
                self.stdout.write(f'  DND Period: {settings.dnd_start_time} - {settings.dnd_end_time}')
            
            self.stdout.write('\n' + '='*50 + '\n')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error getting reminder statistics: {e}')
            )