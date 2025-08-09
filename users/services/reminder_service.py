import logging
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from ..models import (
    WpUsers, WpUsermeta, WpPosts, CourseReminderLog, 
    CourseReminderSettings, UserReminderPreference
)
from .whatsapp_service import whatsapp_service
import threading
import time

logger = logging.getLogger(__name__)

class CourseReminderService:
    """Service for managing course reminders"""

    def __init__(self):
        self.ensure_default_settings()

    def ensure_default_settings(self):
        """Ensure default reminder settings exist"""
        try:
            if not CourseReminderSettings.objects.exists():
                CourseReminderSettings.objects.create(
                    reminder_30_min_enabled=True,
                    reminder_6_hour_enabled=True,
                    max_6_hour_reminders=3,
                    dnd_start_time='20:00:00',
                    dnd_end_time='08:00:00'
                )
                logger.info("Created default reminder settings")
        except Exception as e:
            logger.error(f"Error creating default settings: {e}")

    def schedule_30_minute_reminder(self, user_id, course_id, current_message_id):
        """Schedule 30-minute reminder for inactive user"""
        try:
            logger.info(f"Scheduling 30-minute reminder for user {user_id}, course {course_id}")
            
            # Cancel any existing 30-minute reminders for this user/course
            self.cancel_pending_reminders(user_id, course_id, '30_min')
            
            # Get user info
            user_info = self._get_user_info(user_id)
            if not user_info:
                logger.error(f"User {user_id} not found")
                return False

            # Get course info
            course_info = self._get_course_info(course_id)
            if not course_info:
                logger.error(f"Course {course_id} not found")
                return False

            # Calculate schedule time (30 minutes from now)
            scheduled_time = timezone.now() + timedelta(minutes=30)
            
            # Create reminder log
            reminder = CourseReminderLog.objects.create(
                user_id=user_id,
                course_id=course_id,
                reminder_type='30_min',
                message_id=current_message_id,
                scheduled_time=scheduled_time,
                phone_number=user_info['phone'],
                user_name=user_info['name'],
                course_name=course_info['name'],
                triggered_by='system',
                meta_data=json.dumps({
                    'current_message_id': current_message_id,
                    'scheduled_by': 'system',
                    'original_schedule_time': scheduled_time.isoformat()
                })
            )

            # Schedule the reminder using threading
            self._schedule_reminder_execution(reminder.id, 1 * 60)  # 1 minute in seconds

            logger.info(f"30-minute reminder scheduled for {scheduled_time}")
            return True

        except Exception as e:
            logger.error(f"Error scheduling 30-minute reminder: {e}")
            return False

    def schedule_6_hour_reminder(self, user_id, course_id, current_message_id, reminder_count=0):
        """Schedule 6-hour reminder for inactive user"""
        try:
            settings = CourseReminderSettings.objects.first()
            if not settings or not settings.reminder_6_hour_enabled:
                return False

            # Check if we've reached max reminders
            if reminder_count >= settings.max_6_hour_reminders:
                logger.info(f"Max 6-hour reminders reached for user {user_id}")
                return False

            logger.info(f"Scheduling 6-hour reminder #{reminder_count + 1} for user {user_id}")
            
            # Get user info
            user_info = self._get_user_info(user_id)
            if not user_info:
                return False

            # Get course info
            course_info = self._get_course_info(course_id)
            if not course_info:
                return False

            # Calculate schedule time (6 hours from now)
            scheduled_time = timezone.now() + timedelta(hours=6)
            
            # Create reminder log
            reminder = CourseReminderLog.objects.create(
                user_id=user_id,
                course_id=course_id,
                reminder_type='6_hour',
                message_id=current_message_id,
                scheduled_time=scheduled_time,
                phone_number=user_info['phone'],
                user_name=user_info['name'],
                course_name=course_info['name'],
                reminder_count=reminder_count + 1,
                triggered_by='system',
                meta_data=json.dumps({
                    'current_message_id': current_message_id,
                    'reminder_sequence': reminder_count + 1,
                    'max_reminders': settings.max_6_hour_reminders,
                    'original_schedule_time': scheduled_time.isoformat()
                })
            )

            # Schedule the reminder
            self._schedule_reminder_execution(reminder.id, 6 * 60 * 60)  # 6 hours in seconds
            
            logger.info(f"6-hour reminder #{reminder_count + 1} scheduled for {scheduled_time}")
            return True

        except Exception as e:
            logger.error(f"Error scheduling 6-hour reminder: {e}")
            return False

    def send_admin_reminder(self, user_ids, course_id, admin_user_id, custom_message=None):
        """Send immediate reminder triggered by admin"""
        try:
            logger.info(f"Admin {admin_user_id} triggering reminders for {len(user_ids)} users")
            
            results = []
            
            for user_id in user_ids:
                try:
                    # Get user info
                    user_info = self._get_user_info(user_id)
                    if not user_info:
                        results.append({'user_id': user_id, 'success': False, 'error': 'User not found'})
                        continue

                    # Get current state
                    current_state = self._get_user_current_state(user_id)
                    current_message_id = current_state.get('message_id', 'm-1')

                    # Get course info
                    course_info = self._get_course_info(course_id)
                    if not course_info:
                        results.append({'user_id': user_id, 'success': False, 'error': 'Course not found'})
                        continue

                    # Create reminder log
                    reminder = CourseReminderLog.objects.create(
                        user_id=user_id,
                        course_id=course_id,
                        reminder_type='admin',
                        message_id=current_message_id,
                        scheduled_time=timezone.now(),
                        phone_number=user_info['phone'],
                        user_name=user_info['name'],
                        course_name=course_info['name'],
                        triggered_by=f'admin_{admin_user_id}',
                        meta_data=json.dumps({
                            'admin_user_id': admin_user_id,
                            'custom_message': custom_message,
                            'sent_immediately': True
                        })
                    )

                    # Send immediately
                    success = self._send_reminder_message(reminder.id, custom_message)
                    results.append({
                        'user_id': user_id,
                        'success': success,
                        'reminder_id': reminder.id
                    })

                except Exception as e:
                    logger.error(f"Error sending admin reminder to user {user_id}: {e}")
                    results.append({'user_id': user_id, 'success': False, 'error': str(e)})

            return results

        except Exception as e:
            logger.error(f"Error in send_admin_reminder: {e}")
            return []

    # Add these methods to your CourseReminderService class

    def send_reminder_with_resume_template(self, reminder_id, custom_message=None):
        """Send reminder using resume template when possible"""
        try:
            reminder = CourseReminderLog.objects.get(id=reminder_id)
            
            # Check if reminder is still pending
            if reminder.status != 'pending':
                logger.info(f"Reminder {reminder_id} already processed: {reminder.status}")
                return False

            # Get user's current state and progress info
            current_state = self._get_user_current_state(reminder.user_id)
            stored_message_id = reminder.message_id
            current_message_id = current_state.get('message_id', 'm-1')
            
            # If user has progressed, cancel the reminder
            if current_message_id != stored_message_id:
                reminder.status = 'cancelled'
                reminder.error_message = f'User progressed from {stored_message_id} to {current_message_id}'
                reminder.save()
                logger.info(f"Cancelled reminder {reminder_id} - user has progressed")
                return False

            # Check DND period
            if reminder.is_in_dnd_period():
                next_time = reminder.get_next_available_time()
                reminder.scheduled_time = next_time
                reminder.status = 'skipped_dnd'
                reminder.error_message = f'Rescheduled due to DND period to {next_time}'
                reminder.save()
                
                delay_seconds = (next_time - timezone.now()).total_seconds()
                self._schedule_reminder_execution(reminder_id, max(0, delay_seconds))
                
                logger.info(f"Rescheduled reminder {reminder_id} due to DND period")
                return False

            # Get detailed progress information
            progress_info = self._get_user_progress_info(reminder.user_id, reminder.course_id, current_message_id)
            
            # Try to send template first, fallback to regular message
            template_result = self._send_resume_template_message(reminder, progress_info, custom_message)
            
            if template_result.get('success'):
                reminder.status = 'sent'
                reminder.sent_time = timezone.now()
                reminder.meta_data = json.dumps({
                    **json.loads(reminder.meta_data or '{}'),
                    'message_sid': template_result.get('message_sid'),
                    'sent_at': timezone.now().isoformat(),
                    'method': 'template',
                    'progress_info': progress_info
                })
                
                # Schedule next reminder if applicable
                self._schedule_next_reminder_if_needed(reminder, current_message_id, stored_message_id)
                
                logger.info(f"Resume template reminder {reminder_id} sent successfully")
                
            else:
                # Fallback to regular message
                logger.warning(f"Template failed for reminder {reminder_id}, using regular message")
                fallback_result = self._send_reminder_message(reminder_id, custom_message)
                return fallback_result

            reminder.save()
            return template_result.get('success', False)

        except CourseReminderLog.DoesNotExist:
            logger.error(f"Reminder {reminder_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error sending resume template reminder {reminder_id}: {e}")
            return False

    def _send_resume_template_message(self, reminder, progress_info, custom_message=None):
        """Send the resume template message"""
        try:
            # Get template SID from settings
            template_sid = getattr(settings, 'WHATSAPP_COURSE_RESUME_TEMPLATE_SID', None)
            
            if not template_sid:
                logger.warning("No course resume template SID configured")
                return {'success': False, 'error': 'No template configured'}

            # Prepare template variables
            user_name = reminder.user_name
            course_name = reminder.course_name
            lesson_name = progress_info.get('lesson_name', 'your lesson')
            progress_percentage = progress_info.get('progress_percentage', 0)
            completed_lessons = progress_info.get('completed_lessons', 0)
            total_lessons = progress_info.get('total_lessons', 0)
            lesson_type = progress_info.get('lesson_type', 'lesson')
            
            # Determine time passed
            time_passed = self._get_time_passed_text(reminder.reminder_type, reminder.reminder_count)
            
            # Determine next action
            next_action = self._get_next_action_text(lesson_type)
            
            # Create remaining lessons text
            remaining_lessons = total_lessons - completed_lessons
            remaining_text = f"{remaining_lessons} lessons" if remaining_lessons > 1 else f"{remaining_lessons} lesson"
            
            template_variables = {
                "1": user_name,                           # {{1}} - User name
                "2": course_name,                         # {{2}} - Course name  
                "3": lesson_name,                         # {{3}} - Current lesson name
                "4": str(int(progress_percentage)),       # {{4}} - Progress percentage
                "5": time_passed,                         # {{5}} - Time passed text
                "6": lesson_name,                         # {{6}} - Lesson to resume from
                "7": remaining_text                       # {{7}} - Remaining lessons
            }
            
            logger.info(f"Sending resume template to {reminder.phone_number}")
            logger.info(f"Template variables: {template_variables}")
            
            result = whatsapp_service.send_template_message(
                to_number=reminder.phone_number,
                template_sid=template_sid,
                template_variables=template_variables
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending resume template: {e}")
            return {'success': False, 'error': str(e)}

    def _get_time_passed_text(self, reminder_type, reminder_count=0):
        """Get human-readable time passed text"""
        if reminder_type == '30_min':
            return "30 minutes"
        elif reminder_type == '6_hour':
            if reminder_count == 1:
                return "6 hours"
            else:
                hours = reminder_count * 6
                return f"{hours} hours"
        elif reminder_type == 'admin':
            return "some time"
        else:
            return "a while"

    def _get_next_action_text(self, lesson_type):
        """Get next action text based on lesson type"""
        if lesson_type == 'video':
            return "📹 Video lesson to watch"
        elif lesson_type == 'quiz':
            return "❓ Quiz to complete"
        elif lesson_type == 'text':
            return "📖 Content to read"
        else:
            return "📚 Lessons to complete"

    def _schedule_next_reminder_if_needed(self, reminder, current_message_id, stored_message_id):
        """Schedule next reminder if conditions are met"""
        if reminder.reminder_type == '6_hour':
            settings_obj = CourseReminderSettings.objects.first()
            if (settings_obj and 
                reminder.reminder_count < settings_obj.max_6_hour_reminders and
                current_message_id == stored_message_id):
                
                self.schedule_6_hour_reminder(
                    reminder.user_id,
                    reminder.course_id,
                    current_message_id,
                    reminder.reminder_count
                )

    # Update the existing _schedule_reminder_execution method
    def _schedule_reminder_execution(self, reminder_id, delay_seconds):
        """Schedule reminder execution using threading with template support"""
        def execute_reminder():
            try:
                time.sleep(delay_seconds)
                
                # Try template first, then fallback to regular
                template_success = self.send_reminder_with_resume_template(reminder_id)
                
                if not template_success:
                    logger.info(f"Template reminder failed for {reminder_id}, using regular reminder")
                    self._send_reminder_message(reminder_id)
                    
            except Exception as e:
                logger.error(f"Error in reminder execution thread: {e}")

        thread = threading.Thread(target=execute_reminder)
        thread.daemon = True
        thread.start()


    def _send_reminder_message(self, reminder_id, custom_message=None):
        """Send the actual reminder message with course continuation"""
        try:
            reminder = CourseReminderLog.objects.get(id=reminder_id)
            
            # Check if reminder is still pending
            if reminder.status != 'pending':
                logger.info(f"Reminder {reminder_id} already processed: {reminder.status}")
                return False

            # Get user's current state to determine where they left off
            current_state = self._get_user_current_state(reminder.user_id)
            stored_message_id = reminder.message_id
            current_message_id = current_state.get('message_id', 'm-1')
            
            # If user has progressed, cancel the reminder
            if current_message_id != stored_message_id:
                reminder.status = 'cancelled'
                reminder.error_message = f'User progressed from {stored_message_id} to {current_message_id}'
                reminder.save()
                logger.info(f"Cancelled reminder {reminder_id} - user has progressed")
                return False

            # Check DND period
            if reminder.is_in_dnd_period():
                next_time = reminder.get_next_available_time()
                reminder.scheduled_time = next_time
                reminder.status = 'skipped_dnd'
                reminder.error_message = f'Rescheduled due to DND period to {next_time}'
                reminder.save()
                
                # Reschedule for after DND
                delay_seconds = (next_time - timezone.now()).total_seconds()
                self._schedule_reminder_execution(reminder_id, max(0, delay_seconds))
                
                logger.info(f"Rescheduled reminder {reminder_id} due to DND period")
                return False

            # Get course progress information for the reminder message
            progress_info = self._get_user_progress_info(reminder.user_id, reminder.course_id, current_message_id)

            # Prepare reminder message with course continuation
            if custom_message:
                message = custom_message
            else:
                message = self._generate_reminder_message_with_progress(reminder, progress_info)

            # Send the message
            result = whatsapp_service.send_message(reminder.phone_number, message)
            
            # Update reminder status
            if result.get('success'):
                reminder.status = 'sent'
                reminder.sent_time = timezone.now()
                reminder.meta_data = json.dumps({
                    **json.loads(reminder.meta_data or '{}'),
                    'message_sid': result.get('message_sid'),
                    'sent_at': timezone.now().isoformat(),
                    'progress_info': progress_info  # Store progress info
                })
                
                # Schedule next 6-hour reminder if applicable
                if reminder.reminder_type == '6_hour':
                    settings = CourseReminderSettings.objects.first()
                    if (settings and 
                        reminder.reminder_count < settings.max_6_hour_reminders and
                        current_message_id == stored_message_id):
                        
                        self.schedule_6_hour_reminder(
                            reminder.user_id,
                            reminder.course_id,
                            current_message_id,
                            reminder.reminder_count
                        )
                
                logger.info(f"Reminder {reminder_id} sent successfully with progress info")
                
            else:
                reminder.status = 'failed'
                reminder.error_message = result.get('error', 'Unknown error')
                logger.error(f"Failed to send reminder {reminder_id}: {reminder.error_message}")

            reminder.save()
            return result.get('success', False)

        except CourseReminderLog.DoesNotExist:
            logger.error(f"Reminder {reminder_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error sending reminder {reminder_id}: {e}")
            return False

    def _generate_reminder_message(self, reminder):
        """Generate reminder message based on type"""
        try:
            user_name = reminder.user_name
            course_name = reminder.course_name
            
            if reminder.reminder_type == '30_min':
                message = f"""🔔 **Course Reminder** 🔔

Hi {user_name}!

You started the course "{course_name}" but haven't completed it yet.

⏰ **It's been 30 minutes** - Ready to continue your learning journey?

🎯 **Your Progress Awaits!**
• Continue where you left off
• Complete your course modules
• Achieve your learning goals

Reply **CONTINUE** to resume your course now!

---
💡 *Learning Tip: Consistent progress leads to better retention!*

📚 **ILead Learning Platform**"""

            elif reminder.reminder_type == '6_hour':
                sequence = reminder.reminder_count
                message = f"""📚 **Course Continuation Reminder #{sequence}** 📚

Hello {user_name}!

We noticed you haven't completed "{course_name}" yet.

⏰ **It's been {sequence * 6} hours** since your last activity.

🎯 **Don't Let Your Progress Fade!**
• Complete your remaining lessons
• Achieve your learning objectives
• Get your course certificate

Reply **CONTINUE** to get back on track!

---
🌟 *Reminder #{sequence} of 3* - Stay committed to your growth!

📚 **ILead Learning Platform**"""

            elif reminder.reminder_type == 'admin':
                message = f"""📢 **Important Course Reminder** 📢

Hi {user_name}!

This is a special reminder about your course "{course_name}".

👨‍💼 **Message from Course Administrator:**

Please complete your pending course modules at your earliest convenience.

🎯 **Action Required:**
• Log in to your course
• Complete remaining lessons
• Submit any pending assignments

Reply **CONTINUE** to resume now!

---
📚 **ILead Learning Platform**
*This message was sent by your course administrator*"""

            else:
                message = f"""🔔 **Course Reminder** 🔔

Hi {user_name}!

Please continue with your course "{course_name}".

Reply **CONTINUE** to resume!

📚 **ILead Learning Platform**"""

            return message

        except Exception as e:
            logger.error(f"Error generating reminder message: {e}")
            return f"Hi {reminder.user_name}! Please continue your course. Reply CONTINUE to resume."
        

    def _get_user_progress_info(self, user_id, course_id, current_message_id):
        """Get detailed progress information for the user"""
        try:
            # Get course data to determine lesson details
            from ..models import WpPostmeta
            from .whatsapp_service import whatsapp_service
            
            # Get course message data
            try:
                message_meta = WpPostmeta.objects.get(
                    post_id=course_id,
                    meta_key='messageData'
                )
                course_data = whatsapp_service.parse_serialized_data(message_meta.meta_value)
            except Exception as e:
                logger.warning(f"Could not get course data: {e}")
                course_data = None

            progress_info = {
                'current_message_id': current_message_id,
                'lesson_name': None,
                'lesson_type': None,
                'progress_percentage': 0,
                'total_lessons': 0,
                'completed_lessons': 0,
                'next_lesson_type': None
            }

            if course_data:
                # Calculate progress
                total_messages = len(course_data)
                current_index = 0
                
                # Find current message index
                try:
                    current_index = int(current_message_id.replace('m-', '')) - 1
                    if current_index < 0:
                        current_index = 0
                except:
                    current_index = 0

                progress_info['total_lessons'] = total_messages
                progress_info['completed_lessons'] = current_index
                progress_info['progress_percentage'] = round((current_index / total_messages) * 100, 1) if total_messages > 0 else 0

                # Get current lesson info
                if current_index < total_messages:
                    current_lesson = course_data.get(current_index, {})
                    progress_info['lesson_name'] = current_lesson.get('lesson_name', f'Lesson {current_index + 1}')
                    progress_info['lesson_type'] = current_lesson.get('type', 'unknown')
                    
                    # Get next lesson type if available
                    if current_index + 1 < total_messages:
                        next_lesson = course_data.get(current_index + 1, {})
                        progress_info['next_lesson_type'] = next_lesson.get('type', 'unknown')

            return progress_info

        except Exception as e:
            logger.error(f"Error getting progress info: {e}")
            return {
                'current_message_id': current_message_id,
                'lesson_name': None,
                'lesson_type': None,
                'progress_percentage': 0,
                'total_lessons': 0,
                'completed_lessons': 0,
                'next_lesson_type': None
            }
        
    def _generate_reminder_message_with_progress(self, reminder, progress_info):
        """Generate reminder message with course progress information"""
        try:
            user_name = reminder.user_name
            course_name = reminder.course_name
            lesson_name = progress_info.get('lesson_name', 'your lesson')
            lesson_type = progress_info.get('lesson_type', 'lesson')
            progress_percentage = progress_info.get('progress_percentage', 0)
            completed_lessons = progress_info.get('completed_lessons', 0)
            total_lessons = progress_info.get('total_lessons', 0)
            next_lesson_type = progress_info.get('next_lesson_type', 'lesson')
            
            # Determine the appropriate action based on lesson type
            action_text = "continue"
            if lesson_type == 'video':
                action_text = "watch the video"
            elif lesson_type == 'quiz':
                action_text = "answer the quiz"
            elif lesson_type == 'text':
                action_text = "read the content"
            
            # Determine next lesson preview
            next_action = ""
            if next_lesson_type == 'video':
                next_action = "📹 Next: Video lesson"
            elif next_lesson_type == 'quiz':
                next_action = "❓ Next: Quiz assessment"
            elif next_lesson_type == 'text':
                next_action = "📖 Next: Learning content"
            
            if reminder.reminder_type == '30_min':
                message = f"""🔔 **Course Reminder** 🔔

    Hi {user_name}!

    You started "{course_name}" but paused at:

    📍 **Current Position:**
    • {lesson_name}
    • Progress: {progress_percentage}% ({completed_lessons}/{total_lessons} lessons)

    ⏰ **It's been 30 minutes** - Ready to {action_text}?

    🎯 **Continue Where You Left Off:**
    • Resume from "{lesson_name}"
    • {next_action}
    • Complete your learning journey

    Reply **CONTINUE** to resume exactly where you stopped!

    ---
    💡 *Learning Tip: Consistent progress leads to better retention!*

    📚 **ILead Learning Platform**"""

            elif reminder.reminder_type == '6_hour':
                sequence = reminder.reminder_count
                hours_passed = sequence * 6
                
                message = f"""📚 **Course Continuation Reminder #{sequence}** 📚

    Hello {user_name}!

    You haven't completed "{course_name}" yet.

    ⏰ **It's been {hours_passed} hours** since your last activity.

    📍 **You Left Off At:**
    • Lesson: {lesson_name}
    • Progress: {progress_percentage}% complete
    • Status: {completed_lessons} of {total_lessons} lessons done

    🎯 **Pick Up Where You Stopped:**
    • Resume from "{lesson_name}"
    • Action needed: {action_text}
    • {next_action}

    Reply **CONTINUE** to resume your exact position!

    ---
    🌟 *Reminder #{sequence} of 3* - Don't lose your momentum!

    📚 **ILead Learning Platform**"""

            elif reminder.reminder_type == 'admin':
                message = f"""📢 **Important Course Reminder** 📢

    Hi {user_name}!

    This is a special reminder about your course "{course_name}".

    👨‍💼 **Message from Course Administrator:**

    Please complete your pending course modules at your earliest convenience.

    📍 **Your Current Status:**
    • Last Position: {lesson_name}
    • Progress: {progress_percentage}% ({completed_lessons}/{total_lessons} lessons)
    • Action Required: {action_text}

    🎯 **Continue From Where You Left Off:**
    • Resume at "{lesson_name}"
    • {next_action}
    • Complete your remaining modules

    Reply **CONTINUE** to resume your exact position!

    ---
    📚 **ILead Learning Platform**
    *This message was sent by your course administrator*"""

            else:
                message = f"""🔔 **Course Reminder** 🔔

    Hi {user_name}!

    Continue your course "{course_name}" from where you left off.

    📍 **Resume Position:** {lesson_name}
    📊 **Progress:** {progress_percentage}% complete

    Reply **CONTINUE** to resume!

    📚 **ILead Learning Platform**"""

            return message

        except Exception as e:
            logger.error(f"Error generating progress reminder message: {e}")
            # Fallback to original message
            return self._generate_reminder_message(reminder)

    def cancel_pending_reminders(self, user_id, course_id, reminder_type=None):
        """Cancel pending reminders for a user"""
        try:
            query = CourseReminderLog.objects.filter(
                user_id=user_id,
                course_id=course_id,
                status='pending'
            )
            
            if reminder_type:
                query = query.filter(reminder_type=reminder_type)
            
            updated = query.update(
                status='cancelled',
                error_message='Cancelled due to user activity',
                updated_at=timezone.now()
            )
            
            logger.info(f"Cancelled {updated} pending reminders for user {user_id}")
            return updated

        except Exception as e:
            logger.error(f"Error cancelling reminders: {e}")
            return 0

    def cancel_all_user_reminders(self, user_id):
        """Cancel all pending reminders for a user"""
        try:
            updated = CourseReminderLog.objects.filter(
                user_id=user_id,
                status='pending'
            ).update(
                status='cancelled',
                error_message='All reminders cancelled',
                updated_at=timezone.now()
            )
            
            logger.info(f"Cancelled all {updated} pending reminders for user {user_id}")
            return updated

        except Exception as e:
            logger.error(f"Error cancelling all reminders for user {user_id}: {e}")
            return 0

    def _get_user_info(self, user_id):
        """Get user information"""
        try:
            user = WpUsers.objects.get(id=user_id)
            
            # Get phone number
            phone_meta = WpUsermeta.objects.filter(
                user_id=user_id,
                meta_key='waid'
            ).first()
            
            if not phone_meta:
                return None
            
            phone = phone_meta.meta_value
            if not phone.startswith('+'):
                phone = f'+{phone}'
            
            return {
                'name': user.display_name or user.user_nicename or 'Student',
                'email': user.user_email,
                'phone': phone
            }
            
        except WpUsers.DoesNotExist:
            return None

    def _get_course_info(self, course_id):
        """Get course information"""
        try:
            course = WpPosts.objects.get(id=course_id, post_type='sfwd-courses')
            return {
                'name': course.post_title,
                'status': course.post_status
            }
        except WpPosts.DoesNotExist:
            return None

    def _get_user_current_state(self, user_id):
        """Get user's current state"""
        try:
            state_meta = WpUsermeta.objects.filter(
                user_id=user_id,
                meta_key='whatsapp_current_state'
            ).first()
            
            if state_meta:
                state_parts = state_meta.meta_value.split('|')
                return {
                    'course_id': state_parts[0] if len(state_parts) > 0 else None,
                    'message_id': state_parts[1] if len(state_parts) > 1 else 'm-1',
                    'step': state_parts[2] if len(state_parts) > 2 else 'start',
                    'language': state_parts[3] if len(state_parts) > 3 else None
                }
            
            return {
                'course_id': None,
                'message_id': 'm-1',
                'step': 'start',
                'language': None
            }
            
        except Exception as e:
            logger.error(f"Error getting user state: {e}")
            return {
                'course_id': None,
                'message_id': 'm-1',
                'step': 'start',
                'language': None
            }

    def get_reminder_statistics(self, days=7):
        """Get reminder statistics for the last N days"""
        try:
            since_date = timezone.now() - timedelta(days=days)
            
            stats = {
                'total_scheduled': 0,
                'total_sent': 0,
                'total_failed': 0,
                'total_skipped_dnd': 0,
                'total_cancelled': 0,
                'by_type': {},
                'success_rate': 0
            }
            
            reminders = CourseReminderLog.objects.filter(
                created_at__gte=since_date
            )
            
            stats['total_scheduled'] = reminders.count()
            stats['total_sent'] = reminders.filter(status='sent').count()
            stats['total_failed'] = reminders.filter(status='failed').count()
            stats['total_skipped_dnd'] = reminders.filter(status='skipped_dnd').count()
            stats['total_cancelled'] = reminders.filter(status='cancelled').count()
            
            # By type statistics
            for reminder_type, _ in CourseReminderLog.REMINDER_TYPES:
                type_reminders = reminders.filter(reminder_type=reminder_type)
                stats['by_type'][reminder_type] = {
                    'scheduled': type_reminders.count(),
                    'sent': type_reminders.filter(status='sent').count(),
                    'failed': type_reminders.filter(status='failed').count()
                }
            
            # Calculate success rate
            if stats['total_scheduled'] > 0:
                stats['success_rate'] = round(
                    (stats['total_sent'] / stats['total_scheduled']) * 100, 2
                )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting reminder statistics: {e}")
            return {}

# Create global instance
reminder_service = CourseReminderService()