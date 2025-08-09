import json
import phpserialize
import logging
import re
from ..models import WpPostmeta

logger = logging.getLogger(__name__)

class CourseDataService:
    """Service for handling course data and message parsing"""
    
    @staticmethod
    def get_course_lessons(course_id):
        """Extract lesson structure from messageData field"""
        try:
            logger.info(f"CourseDataService.get_course_lessons called for course ID: {course_id}")
            
            # Get the messageData from postmeta
            message_meta = WpPostmeta.objects.get(
                post_id=course_id,
                meta_key='messageData'
            )
            serialized_data = message_meta.meta_value

            logger.info(f"Found messageData for course {course_id}, data length: {len(serialized_data)}")
            logger.info(f"Data preview: {serialized_data[:200]}...")
            
            # Parse the PHP serialized data using the same method as whatsapp_service
            from ..services.whatsapp_service import whatsapp_service
            course_data = whatsapp_service.parse_serialized_data(serialized_data)
            
            if not course_data:
                logger.error(f"Failed to parse course data for course ID {course_id}")
                return []
                
            logger.info(f"Parsed course data successfully. Found {len(course_data)} messages")
            
            # Extract lesson structure from parsed data
            lessons = []
            
            # Sort by message ID to ensure correct order
            if isinstance(course_data, dict):
                sorted_items = []
                for key, message_data in course_data.items():
                    if isinstance(message_data, dict) and 'id' in message_data:
                        message_id = message_data.get('id', '')
                        if message_id.startswith('m-'):
                            try:
                                msg_num = int(message_id.replace('m-', ''))
                                sorted_items.append((msg_num, message_data))
                            except ValueError:
                                logger.warning(f"Invalid message ID format: {message_id}")
                
                # Sort by message number
                sorted_items.sort(key=lambda x: x[0])
                logger.info(f"Sorted {len(sorted_items)} valid messages")
                
                # Process each message
                for msg_num, message_data in sorted_items:
                    message_id = message_data.get('id', '')
                    message_type = message_data.get('type', 'text')
                    lesson_name = message_data.get('lesson_name', '')
                    content = message_data.get('content', '')
                    
                    logger.info(f"Processing message {message_id}: type={message_type}, lesson_name='{lesson_name}'")
                    
                    # Determine lesson title
                    if lesson_name:
                        title = lesson_name
                    elif message_type == 'quiz':
                        title = f"QUIZ {len([l for l in lessons if l.get('is_quiz', False)]) + 1}"
                    elif message_type == 'button':
                        # Extract title from button data if available
                        button_data = message_data.get('button', {})
                        if isinstance(button_data, dict) and 0 in button_data:
                            first_button = button_data[0]
                            if hasattr(first_button, 'question'):
                                title = first_button.question
                            else:
                                title = f"LESSON {len(lessons) + 1}"
                        else:
                            title = f"LESSON {len(lessons) + 1}"
                    else:
                        # Extract title from content first line
                        if content:
                            lines = content.strip().split('\n')
                            first_line = lines[0].strip()
                            if len(first_line) < 100 and first_line:
                                title = first_line
                            else:
                                title = f"LESSON {len(lessons) + 1}"
                        else:
                            title = f"LESSON {len(lessons) + 1}"
                    
                    # Create lesson entry
                    lesson = {
                        "id": f"lesson_{len(lessons) + 1}",
                        "title": title,
                        "message_ids": [message_id],
                        "type": message_type,
                        "is_quiz": message_type == 'quiz',
                        "is_assessment": 'assessment' in title.lower()
                    }
                    
                    lessons.append(lesson)
                    logger.info(f"Added lesson: {lesson['id']} - {lesson['title']}")
            
            logger.info(f"Extracted {len(lessons)} lessons for course {course_id}")
            return lessons
            
        except WpPostmeta.DoesNotExist:
            logger.error(f"messageData not found for course ID {course_id}")
            return []
        except Exception as e:
            logger.error(f"Error extracting lesson data: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    @staticmethod
    def parse_serialized_data(serialized_data):
        """Parse PHP serialized data - delegated to whatsapp_service"""
        try:
            from ..services.whatsapp_service import whatsapp_service
            return whatsapp_service.parse_serialized_data(serialized_data)
        except Exception as e:
            logger.error(f"Error parsing serialized data: {str(e)}")
            return None