import json
import time
import logging
from django.utils import timezone
from datetime import datetime, timedelta
from ..models import WpUsermeta, WpUsers, WpPosts, WpPostmeta

logger = logging.getLogger(__name__)

class ComprehensiveCourseTracker:
    """Comprehensive course tracking service for detailed learning analytics"""
    
    @staticmethod
    def track_course_enrollment(user_id, course_id, enrollment_method='whatsapp'):
        """Track when a user enrolls in a course"""
        try:
            timestamp = int(time.time())
            
            enrollment_data = {
                'course_id': course_id,
                'enrolled_at': timestamp,
                'enrollment_method': enrollment_method,
                'status': 'enrolled'
            }
            
            WpUsermeta.objects.update_or_create(
                user_id=user_id,
                meta_key=f'course_{course_id}_enrollment',
                defaults={'meta_value': json.dumps(enrollment_data)}
            )
            
            # Also track general course access
            WpUsermeta.objects.update_or_create(
                user_id=user_id,
                meta_key=f'course_{course_id}_access_from',
                defaults={'meta_value': str(timestamp)}
            )
            
            logger.info(f"Tracked enrollment: User {user_id} in Course {course_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking course enrollment: {e}")
            return False
    
    @staticmethod
    def track_lesson_start(user_id, course_id, lesson_id, message_id):
        """Track when a user starts a lesson"""
        try:
            timestamp = int(time.time())
            
            lesson_data = {
                'lesson_id': lesson_id,
                'message_id': message_id,
                'course_id': course_id,
                'started_at': timestamp,
                'status': 'started'
            }
            
            WpUsermeta.objects.update_or_create(
                user_id=user_id,
                meta_key=f'lesson_started_{message_id}',
                defaults={'meta_value': json.dumps(lesson_data)}
            )
            
            logger.info(f"Tracked lesson start: User {user_id}, Lesson {lesson_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking lesson start: {e}")
            return False
    
    @staticmethod
    def track_lesson_completion(user_id, course_id, lesson_id, message_id, time_spent=None):
        """Track when a user completes a lesson"""
        try:
            timestamp = int(time.time())
            
            # Get start time if available
            start_meta = WpUsermeta.objects.filter(
                user_id=user_id,
                meta_key=f'lesson_started_{message_id}'
            ).first()
            
            started_at = None
            if start_meta:
                try:
                    start_data = json.loads(start_meta.meta_value)
                    started_at = start_data.get('started_at')
                except:
                    pass
            
            # Calculate time spent if not provided
            if not time_spent and started_at:
                time_spent = timestamp - started_at
            
            completion_data = {
                'lesson_id': lesson_id,
                'message_id': message_id,
                'course_id': course_id,
                'started_at': started_at,
                'completed_at': timestamp,
                'time_spent_seconds': time_spent,
                'status': 'completed'
            }
            
            WpUsermeta.objects.update_or_create(
                user_id=user_id,
                meta_key=f'lesson_completed_{message_id}',
                defaults={'meta_value': json.dumps(completion_data)}
            )
            
            logger.info(f"Tracked lesson completion: User {user_id}, Lesson {lesson_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking lesson completion: {e}")
            return False
    
    @staticmethod
    def track_video_interaction(user_id, course_id, video_id, interaction_type, session_token=None, duration_watched=None):
        """Track video interactions (play, pause, complete, rewatch)"""
        try:
            timestamp = time.time()
            
            # Get existing video data
            existing_meta = WpUsermeta.objects.filter(
                user_id=user_id,
                meta_key=f'video_viewed_video_{video_id}'
            ).first()
            
            if existing_meta:
                try:
                    video_data = json.loads(existing_meta.meta_value)
                except:
                    video_data = {}
            else:
                video_data = {
                    'video_id': video_id,
                    'course_id': course_id,
                    'first_accessed': timestamp
                }
            
            # Track interaction
            if 'interactions' not in video_data:
                video_data['interactions'] = []
            
            interaction = {
                'type': interaction_type,  # 'play', 'pause', 'complete', 'rewatch'
                'timestamp': timestamp,
                'session_token': session_token,
                'duration_watched': duration_watched
            }
            
            video_data['interactions'].append(interaction)
            
            # Update specific fields based on interaction
            if interaction_type == 'complete':
                video_data['viewed_at'] = timestamp
                video_data['completed'] = True
                video_data['completion_count'] = video_data.get('completion_count', 0) + 1
            
            # Track access count
            video_data['access_count'] = video_data.get('access_count', 0) + 1
            video_data['last_accessed'] = timestamp
            
            if session_token:
                video_data['session_token'] = session_token
            
            WpUsermeta.objects.update_or_create(
                user_id=user_id,
                meta_key=f'video_viewed_video_{video_id}',
                defaults={'meta_value': json.dumps(video_data)}
            )
            
            logger.info(f"Tracked video interaction: User {user_id}, Video {video_id}, Type {interaction_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking video interaction: {e}")
            return False
    
    @staticmethod
    def track_quiz_attempt(user_id, course_id, quiz_id, message_id, question, user_answer, correct_answer, is_correct, attempt_number, max_attempts):
        """Track quiz attempts with detailed analytics"""
        try:
            timestamp = int(time.time())
            
            quiz_data = {
                'message_id': message_id,
                'course_id': course_id,
                'quiz_id': quiz_id,
                'question': question,
                'correct_answer': correct_answer,
                'user_answer': user_answer,
                'is_correct': is_correct,
                'attempt_number': attempt_number,
                'max_attempts': max_attempts,
                'attempted_at': timestamp
            }
            
            # Track individual attempt
            WpUsermeta.objects.create(
                user_id=user_id,
                meta_key=f'quiz_attempt_{message_id}_{attempt_number}_{timestamp}',
                meta_value=json.dumps(quiz_data)
            )
            
            # If quiz is completed (correct or max attempts reached)
            if is_correct or attempt_number >= max_attempts:
                final_result = {
                    'message_id': message_id,
                    'course_id': course_id,
                    'quiz_id': quiz_id,
                    'question': question,
                    'correct_answer': correct_answer,
                    'user_answer': user_answer,
                    'is_correct': is_correct,
                    'attempts_used': attempt_number,
                    'max_attempts': max_attempts,
                    'completed_at': timestamp,
                    'score_percentage': 100 if is_correct else 0
                }
                
                WpUsermeta.objects.update_or_create(
                    user_id=user_id,
                    meta_key=f'quiz_answered_{message_id}',
                    defaults={'meta_value': json.dumps(final_result)}
                )
            
            logger.info(f"Tracked quiz attempt: User {user_id}, Quiz {quiz_id}, Attempt {attempt_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking quiz attempt: {e}")
            return False
    
    @staticmethod
    def track_course_progress(user_id, course_id, current_message_id, step, completion_percentage):
        """Track overall course progress"""
        try:
            timestamp = int(time.time())
            
            progress_data = {
                'course_id': course_id,
                'current_message_id': current_message_id,
                'current_step': step,
                'completion_percentage': completion_percentage,
                'last_updated': timestamp
            }
            
            WpUsermeta.objects.update_or_create(
                user_id=user_id,
                meta_key=f'course_{course_id}_progress',
                defaults={'meta_value': json.dumps(progress_data)}
            )
            
            # Also update the whatsapp current state
            language = 'en'  # Default, you might want to get this from user preferences
            state_value = f"{course_id}|{current_message_id}|{step}|{language}"
            
            WpUsermeta.objects.update_or_create(
                user_id=user_id,
                meta_key='whatsapp_current_state',
                defaults={'meta_value': state_value}
            )
            
            logger.info(f"Tracked course progress: User {user_id}, Course {course_id}, {completion_percentage}%")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking course progress: {e}")
            return False
    
    @staticmethod
    def track_course_completion(user_id, course_id, completion_type='full'):
        """Track course completion"""
        try:
            timestamp = int(time.time())
            
            completion_data = {
                'course_id': course_id,
                'completed_at': timestamp,
                'completion_type': completion_type,  # 'full', 'partial', 'assessment_only'
                'status': 'completed'
            }
            
            WpUsermeta.objects.update_or_create(
                user_id=user_id,
                meta_key=f'course_{course_id}_completion',
                defaults={'meta_value': json.dumps(completion_data)}
            )
            
            # Update completed courses count
            try:
                count_meta = WpUsermeta.objects.filter(
                    user_id=user_id,
                    meta_key='completed_courses_count'
                ).first()
                
                if count_meta:
                    current_count = int(count_meta.meta_value)
                    new_count = current_count + 1
                else:
                    new_count = 1
                
                WpUsermeta.objects.update_or_create(
                    user_id=user_id,
                    meta_key='completed_courses_count',
                    defaults={'meta_value': str(new_count)}
                )
            except Exception as e:
                logger.warning(f"Could not update completed courses count: {e}")
            
            # Update current state to completed
            language = 'en'
            final_message_id = 'm-14'  # Assuming this is the final message
            state_value = f"{course_id}|{final_message_id}|completed|{language}"
            
            WpUsermeta.objects.update_or_create(
                user_id=user_id,
                meta_key='whatsapp_current_state',
                defaults={'meta_value': state_value}
            )
            
            logger.info(f"Tracked course completion: User {user_id}, Course {course_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking course completion: {e}")
            return False
    
    @staticmethod
    def get_comprehensive_user_analytics(user_id):
        """Get comprehensive analytics for a user"""
        try:
            user = WpUsers.objects.get(id=user_id)
            user_meta = WpUsermeta.objects.filter(user_id=user_id)
            
            analytics = {
                'user_info': {
                    'user_id': user_id,
                    'name': user.display_name,
                    'email': user.user_email,
                    'registered': user.user_registered.isoformat() if user.user_registered else None
                },
                'course_enrollments': [],
                'course_completions': [],
                'lesson_activities': [],
                'video_interactions': [],
                'quiz_performance': [],
                'overall_progress': {}
            }
            
            for meta in user_meta:
                key = meta.meta_key
                value = meta.meta_value
                
                # Parse different types of tracking data
                if key.startswith('course_') and key.endswith('_enrollment'):
                    try:
                        data = json.loads(value)
                        analytics['course_enrollments'].append(data)
                    except:
                        pass
                
                elif key.startswith('course_') and key.endswith('_completion'):
                    try:
                        data = json.loads(value)
                        analytics['course_completions'].append(data)
                    except:
                        pass
                
                elif key.startswith('lesson_'):
                    try:
                        data = json.loads(value)
                        analytics['lesson_activities'].append(data)
                    except:
                        pass
                
                elif key.startswith('video_viewed_'):
                    try:
                        data = json.loads(value)
                        video_id = key.replace('video_viewed_video_', '')
                        data['video_id'] = video_id
                        analytics['video_interactions'].append(data)
                    except:
                        pass
                
                elif key.startswith('quiz_'):
                    try:
                        data = json.loads(value)
                        analytics['quiz_performance'].append(data)
                    except:
                        pass
                
                elif key == 'completed_courses_count':
                    analytics['overall_progress']['completed_courses'] = int(value)
                
                elif key == 'whatsapp_current_state':
                    state_parts = value.split('|')
                    analytics['overall_progress']['current_state'] = {
                        'course_id': state_parts[0] if len(state_parts) > 0 else None,
                        'message_id': state_parts[1] if len(state_parts) > 1 else None,
                        'step': state_parts[2] if len(state_parts) > 2 else None,
                        'language': state_parts[3] if len(state_parts) > 3 else None
                    }
            
            # Calculate summary statistics
            analytics['summary_stats'] = {
                'total_courses_enrolled': len(analytics['course_enrollments']),
                'total_courses_completed': len(analytics['course_completions']),
                'total_lessons_accessed': len(analytics['lesson_activities']),
                'total_videos_watched': len([v for v in analytics['video_interactions'] if v.get('completed')]),
                'total_quizzes_attempted': len([q for q in analytics['quiz_performance'] if 'quiz_answered' in str(q)]),
                'quiz_success_rate': ComprehensiveCourseTracker._calculate_quiz_success_rate(analytics['quiz_performance'])
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting comprehensive analytics: {e}")
            return None
    
    @staticmethod
    def _calculate_quiz_success_rate(quiz_data):
        """Calculate quiz success rate"""
        try:
            completed_quizzes = [q for q in quiz_data if q.get('is_correct') is not None]
            if not completed_quizzes:
                return 0
            
            correct_quizzes = [q for q in completed_quizzes if q.get('is_correct')]
            return round((len(correct_quizzes) / len(completed_quizzes)) * 100, 2)
            
        except Exception as e:
            logger.error(f"Error calculating quiz success rate: {e}")
            return 0
    
    @staticmethod
    def get_course_analytics(course_id):
        """Get analytics for a specific course across all users"""
        try:
            # Get all users who have interacted with this course
            course_users = WpUsermeta.objects.filter(
                meta_key__contains=f'course_{course_id}'
            ).values_list('user_id', flat=True).distinct()
            
            analytics = {
                'course_id': course_id,
                'total_enrolled_users': 0,
                'completed_users': 0,
                'in_progress_users': 0,
                'average_completion_time': 0,
                'lesson_completion_rates': {},
                'quiz_performance': {},
                'video_engagement': {}
            }
            
            for user_id in course_users:
                user_analytics = ComprehensiveCourseTracker.get_comprehensive_user_analytics(user_id)
                if user_analytics:
                    # Process user data for course analytics
                    # This would involve aggregating data across users
                    pass
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting course analytics: {e}")
            return None

# Initialize the tracker
course_tracker = ComprehensiveCourseTracker()