from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import CourseReminderLog
from users.services.reminder_service import reminder_service
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process overdue reminders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually sending reminders',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of reminders to process in one run',
        )

    def handle(self, *args, **options):
        try:
            dry_run = options['dry_run']
            limit = options['limit']
            
            # Find overdue pending reminders
            overdue_reminders = CourseReminderLog.objects.filter(
                status='pending',
                scheduled_time__lte=timezone.now()
            ).order_by('scheduled_time')[:limit]

            total_found = overdue_reminders.count()
            self.stdout.write(f'Found {total_found} overdue reminders to process')

            if dry_run:
                self.stdout.write(self.style.WARNING('DRY RUN MODE - No reminders will be sent'))
                for reminder in overdue_reminders:
                    self.stdout.write(
                        f'Would process: User {reminder.user_id}, Course {reminder.course_id}, '
                        f'Type: {reminder.reminder_type}, Scheduled: {reminder.scheduled_time}'
                    )
                return

            processed = 0
            failed = 0
            
            for reminder in overdue_reminders:
                try:
                    self.stdout.write(f'Processing reminder {reminder.id} for user {reminder.user_id}')
                    success = reminder_service._send_reminder_message(reminder.id)
                    if success:
                        processed += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Sent reminder {reminder.id}')
                        )
                    else:
                        failed += 1
                        self.stdout.write(
                            self.style.WARNING(f'✗ Failed to send reminder {reminder.id}')
                        )
                except Exception as e:
                    failed += 1
                    logger.error(f"Error processing reminder {reminder.id}: {e}")
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error processing reminder {reminder.id}: {e}')
                    )

            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSummary:\n'
                    f'Total found: {total_found}\n'
                    f'Successfully processed: {processed}\n'
                    f'Failed: {failed}'
                )
            )

            # Show some statistics
            pending_count = CourseReminderLog.objects.filter(status='pending').count()
            self.stdout.write(f'Remaining pending reminders: {pending_count}')

        except Exception as e:
            logger.error(f"Error in process_reminders command: {e}")
            self.stdout.write(
                self.style.ERROR(f'Error processing reminders: {e}')
            )