import logging
from twilio.rest import Client
from django.conf import settings
import logging
import phpserialize
import json
import re
from urllib.parse import unquote
from .secure_video_service import secure_video_service
from urllib.parse import urlparse, parse_qs
from django.utils import timezone
from datetime import timedelta
import uuid

import traceback

 
logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = settings.TWILIO_WHATSAPP_FROM


    def send_message_with_fallback(self, to_number, message_body, media_url=None, is_new_contact=False):
        """Send WhatsApp message with template fallback for new contacts"""
        try:
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            # First, try to send a regular message
            message_params = {
                'body': message_body,
                'from_': self.from_number,
                'to': to_number
            }
            
            if media_url:
                message_params['media_url'] = [media_url]
            
            try:
                message = self.client.messages.create(**message_params)
                logger.info(f"WhatsApp message sent successfully. SID: {message.sid}")
                return {'success': True, 'message_sid': message.sid, 'method': 'regular'}
                
            except Exception as regular_error:
                error_msg = str(regular_error).lower()
                
                # Check if error is due to 24-hour window restriction
                if any(keyword in error_msg for keyword in ['24 hour', '24-hour', 'conversation', 'window', 'policy']):
                    logger.warning(f"24-hour window restriction detected for {to_number}, trying template fallback")
                    
                    # Try to send using a template message instead
                    return self._send_template_fallback(to_number, message_body)
                else:
                    # For other errors, raise the original exception
                    raise regular_error
                    
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _send_template_fallback(self, to_number, original_message):
        """Send template message when regular message fails due to 24-hour window"""
        try:
            # Use your welcome/introduction template for new contacts
            welcome_template_sid = getattr(settings, 'WHATSAPP_WELCOME_TEMPLATE_SID', None)
            
            if not welcome_template_sid:
                logger.error("No welcome template SID configured for new contacts")
                return {'success': False,
                 'error': 'No template available for new contacts'}
            
            # Extract user name from the original message if possible
            user_name = "Student"  # Default
            
            # Try to extract name from message content
            if "hello" in original_message.lower():
                import re
                name_match = re.search(r'hello[,\s]+([a-zA-Z\s]+)[,!]', original_message, re.IGNORECASE)
                if name_match:
                    user_name = name_match.group(1).strip()
            
            template_variables = {
                "1": user_name
            }
            
            logger.info(f"Sending welcome template to new contact: {to_number}")
            result = self.send_template_message(to_number, welcome_template_sid, template_variables)
            
            if result.get('success'):
                result['method'] = 'template_fallback'
                logger.info(f"Template fallback successful for {to_number}")
            
            return result
            
        except Exception as e:
            logger.error(f"Template fallback also failed: {str(e)}")
            return {'success': False, 'error': f'Both regular and template messages failed: {str(e)}'}

    def check_contact_eligibility(self, to_number):
        """Check if we can send regular messages to this contact"""
        try:
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            # Try to get contact information
            # Note: This is a theoretical check - actual implementation depends on your Twilio setup
            
            # For now, we'll assume new contacts need templates
            # You can enhance this by checking your database for previous conversations
            
            from ..models import WpUsermeta
            clean_phone = to_number.replace('whatsapp:', '').replace('+', '')
            
            # Check if user has received messages before
            user_meta = WpUsermeta.objects.filter(
                meta_key='waid',
                meta_value__icontains=clean_phone
            ).first()
            
            if user_meta:
                # Check if user has any conversation history
                conversation_meta = WpUsermeta.objects.filter(
                    user_id=user_meta.user_id,
                    meta_key='last_whatsapp_activity'
                ).first()
                
                if conversation_meta:
                    from datetime import datetime, timedelta
                    import json
                    
                    try:
                        activity_data = json.loads(conversation_meta.meta_value)
                        last_activity = datetime.fromisoformat(activity_data.get('timestamp', ''))
                        
                        # Check if within 24 hours
                        if datetime.now() - last_activity < timedelta(hours=24):
                            return {'can_send_regular': True, 'reason': 'within_24_hours'}
                        else:
                            return {'can_send_regular': False, 'reason': 'outside_24_hours'}
                            
                    except:
                        return {'can_send_regular': False, 'reason': 'no_recent_activity'}
                else:
                    return {'can_send_regular': False, 'reason': 'no_conversation_history'}
            else:
                return {'can_send_regular': False, 'reason': 'new_contact'}
                
        except Exception as e:
            logger.error(f"Error checking contact eligibility: {e}")
            return {'can_send_regular': False, 'reason': 'check_failed'}

    def update_user_activity(self, user_id):
        """Update user's last WhatsApp activity timestamp"""
        try:
            from ..models import WpUsermeta
            import json
            from datetime import datetime
            
            activity_data = {
                'timestamp': datetime.now().isoformat(),
                'platform': 'whatsapp',
                'action': 'message_received'
            }
            
            WpUsermeta.objects.update_or_create(
                user_id=user_id,
                meta_key='last_whatsapp_activity',
                defaults={'meta_value': json.dumps(activity_data)}
            )
            
            logger.info(f"Updated WhatsApp activity for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")

    
    def send_message(self, to_number, message_body, media_url=None):
        """Send a WhatsApp message"""
        try:
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            message_params = {
                'body': message_body,
                'from_': self.from_number,
                'to': to_number
            }
            
            if media_url:
                message_params['media_url'] = [media_url]
            
            message = self.client.messages.create(**message_params)
            
            logger.info(f"WhatsApp message sent successfully. SID: {message.sid}")
            return {'success': True, 'message_sid': message.sid}
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {str(e)}")
            return {'success': False, 'error': str(e)}

    def send_message_smart(self, to_number, message_body, media_url=None, is_new_contact=False):
        """Send WhatsApp message with automatic fallback for new contacts"""
        if is_new_contact:
            return self.send_message_with_fallback(to_number, message_body, media_url, is_new_contact)
        else:
            return self.send_message(to_number, message_body, media_url)

    
    def send_template_message(self, to_number, template_sid, template_variables=None):
        """Send a WhatsApp template message"""
        try:
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            message_params = {
                'content_sid': template_sid,
                'from_': self.from_number,
                'to': to_number
            }
            
            # Add template variables if provided
            if template_variables:
                message_params['content_variables'] = json.dumps(template_variables)
            
            message = self.client.messages.create(**message_params)
            
            logger.info(f"WhatsApp template message sent successfully. SID: {message.sid}")
            return {'success': True, 'message_sid': message.sid}
        except Exception as e:
            logger.error(f"Failed to send WhatsApp template message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def object_hook(self, name, d):
        """Custom object hook for phpserialize to handle PHP objects"""
        if name == b'stdClass':
            return d
        return d
    
    # In your WhatsApp service class
    def send_video_template_message(self, to_number, template_sid, video_url, video_caption, user_name, video_delay=None):
        """Send video template message with one-time DRM video URL and dynamic delay"""
        try:
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'

            logger.info(f"Sending one-time video template to {to_number}")
            logger.info(f"Template SID: {template_sid}")
            logger.info(f"Original Video ID: {video_url}")
            logger.info(f"Video Caption: {video_caption}")
            logger.info(f"Video Delay: {video_delay} seconds")

            # Create one-time token for this video
            from ..models import OneTimeVideoToken
            from ..utils import create_one_time_video_token
            
            # Extract phone number for tracking
            clean_phone = to_number.replace('whatsapp:', '')
            
            # Create one-time token (expires in 24 hours)
            video_token = create_one_time_video_token(
                video_id=video_url,
                user_phone=clean_phone,
                ttl_hours=24
            )

            # ENHANCED: Store dynamic delay in token metadata
            if video_delay:
                try:
                    token_metadata = {
                        'dynamic_delay': video_delay,
                        'video_caption': video_caption,
                        'created_at': timezone.now().isoformat()
                    }
                    video_token.meta_data = json.dumps(token_metadata)
                    video_token.save()
                    logger.info(f"Stored dynamic delay {video_delay}s in token metadata")
                except Exception as e:
                    logger.warning(f"Could not store token metadata: {e}")

            # FIXED: Ensure video_caption is never empty
            if not video_caption or video_caption.strip() == '':
                video_caption = "Video Lesson"

            # Build one-time DRM video page URL
            drm_page_url = f"api/drm-video/?token={video_token.token}"
            logger.info(f"One-time DRM video page URL created: {drm_page_url}")

            template_variables = {
                "1": f"{user_name}",
                "2": f"{video_caption}",
                "3": drm_page_url,
            }

            logger.info(f"Template variables prepared successfully")

            message = self.client.messages.create(
                from_=self.from_number,
                to=to_number,
                content_sid=template_sid,
                content_variables=json.dumps(template_variables)
            )

            logger.info(f"WhatsApp one-time video template message sent successfully. SID: {message.sid}")

            return {
                'success': True,
                'message_sid': message.sid,
                'message_type': 'video_template',
                'is_drm': True,
                'is_one_time': True,
                'token': str(video_token.token),
                'dynamic_delay': video_delay,
                'video_caption': video_caption  # Return the caption used
            }

        except Exception as e:
            logger.error(f"Error sending one-time video template message: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}


    def _clean_video_url(self, video_url):
        """Extract clean video URL - ONLY for original AWS S3 URLs"""
        # FIXED: Don't clean secure URLs (they contain secure-video in the path)
        # if 'secure-video' in video_url:
        #     logger.info("Skipping URL cleaning for secure video URL")
        #     return video_url
        
        clean_video_url = video_url
        if 'https://embyte-learn.com/' in video_url:
            # Extract everything after the domain
            path_start = video_url.find('https://embyte-learn.com/') + len('https://embyte-learn.com/')
            clean_video_url = video_url[path_start:]
            logger.info(f"Cleaned S3 URL: {clean_video_url}")
        elif video_url.startswith('https://'):
            # For other URLs, try to extract path after domain
            from urllib.parse import urlparse
            parsed_url = urlparse(video_url)
            clean_video_url = parsed_url.path.lstrip('/')
            logger.info(f"Cleaned generic URL: {clean_video_url}")
        
        return clean_video_url
        
    def send_quiz_template_message(self, to_number, template_sid, question, options, user_name):
        """Send quiz template message with dynamic single select options"""
        try:
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            logger.info(f"Sending quiz template to {to_number}")
            logger.info(f"Template SID: {template_sid}")
            logger.info(f"Question: {question[:100]}...")
            logger.info(f"Options: {options}")
            
            # FIXED: Ensure question parameter is properly handled
            if not question:
                logger.error("Question parameter is empty or None")
                return {'success': False, 'error': 'Question is required for quiz template'}
            
            # Format the question for the template - CRITICAL: Keep it very short
            formatted_question = self.format_message_content(question, user_name)
            
            # CRITICAL FIX: Ensure question doesn't exceed 30 characters for template label
            # WhatsApp Flow templates have very strict character limits for labels
            if len(formatted_question) > 1024:  # Much shorter limit for flow templates
                formatted_question = formatted_question[:1020] + "..."
            
            logger.info(f"Formatted question (length: {len(formatted_question)}): {formatted_question}")
            
            # Convert options to the required JSON format for dynamic single select
            # Expected format: [{"id":"option_key","title":"option_text"}]
            dynamic_options = []
            
            if isinstance(options, dict):
                for key, value in options.items():
                    # Clean the option text
                    option_text = str(value).strip()
                    if isinstance(value, bytes):
                        option_text = value.decode('utf-8')
                    
                    # CRITICAL FIX: Ensure option titles don't exceed limits
                    if len(option_text) > 30:  # Even shorter for flow templates
                        option_text = option_text[:27] + "..."
                    
                    # Create the option object
                    dynamic_options.append({
                        "id": str(key),  # Use the original key as ID
                        "title": option_text  # Use the option text as title
                    })
            
            # Convert to JSON string for the template variable
            options_json = json.dumps(dynamic_options)
            
            logger.info(f"Dynamic options JSON: {options_json}")
            
            # FIXED: Match your template configuration exactly - ONLY 2 variables
            # Based on your template:
            # {{1}} = Question text for the label field
            # {{2}} = Dynamic options JSON for single select component
            template_variables = {
                "1": formatted_question,  # {{1}} - Question text (truncated to fit label limits)
                "2": options_json  # {{2}} - Dynamic options in JSON format
            }
            
            # CRITICAL: Validate template variable lengths strictly
            if len(template_variables["1"]) > 1024:
                logger.warning(f"Question text too long ({len(template_variables['1'])} chars), truncating further")
                template_variables["1"] = template_variables["1"][:1020] + "..."

            # Log template variables for debugging
            logger.info(f"Quiz template variables:")
            logger.info(f"  Question ({{1}}): '{template_variables['1']}' (length: {len(template_variables['1'])})")
            logger.info(f"  Options ({{2}}): '{template_variables['2'][:100]}...' (length: {len(template_variables['2'])})")
            
            message = self.client.messages.create(
                from_=self.from_number,
                to=to_number,
                content_sid=template_sid,
                content_variables=json.dumps(template_variables)
            )
            
            logger.info(f"WhatsApp quiz template message sent successfully. SID: {message.sid}")
            
            return {
                'success': True,
                'message_sid': message.sid,
                'message_type': 'quiz_template',
                'options_count': len(dynamic_options)
            }
            
        except Exception as e:
            logger.error(f"Error sending quiz template message: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # FALLBACK: Send regular text quiz if template fails
            logger.info("Template failed, falling back to regular text quiz")
            try:
                fallback_result = self._send_fallback_quiz(to_number, question, options, user_name)
                return fallback_result
            except Exception as fallback_error:
                logger.error(f"Fallback quiz also failed: {fallback_error}")
                return {'success': False, 'error': str(e)}

    def _send_fallback_quiz(self, to_number, question, options, user_name):
        """Send quiz as regular text message if template fails"""
        try:
            # Format quiz as regular message
            message_lines = [f"📝 **Quiz Question**", "", question, ""]
            
            if isinstance(options, dict):
                for key, value in options.items():
                    option_text = str(value).strip()
                    if isinstance(value, bytes):
                        option_text = value.decode('utf-8')
                    message_lines.append(f"{int(key) + 1}. {option_text}")
            
            message_lines.extend(["", "💭 Reply with the number of your answer (1, 2, etc.)"])
            
            message_body = "\n".join(message_lines)
            
            result = self.send_message(to_number, message_body)
            
            if result.get('success'):
                return {
                    'success': True,
                    'message_sid': result.get('message_sid'),
                    'message_type': 'quiz_fallback',
                    'options_count': len(options) if options else 0
                }
            else:
                return {'success': False, 'error': 'Fallback quiz failed'}
                
        except Exception as e:
            logger.error(f"Error in fallback quiz: {str(e)}")
            return {'success': False, 'error': str(e)}

    
    def parse_serialized_data(self, serialized_data):
        """Parse PHP serialized data to Python objects"""
        try:
            data = phpserialize.loads(
                serialized_data.encode('utf-8'), 
                object_hook=self.object_hook,
                decode_strings=True
            )
            return data
        except Exception as e:
            logger.error(f"Failed to parse serialized data: {str(e)}")
            try:
                data = phpserialize.loads(
                    serialized_data.encode('utf-8'), 
                    object_hook=lambda name, d: d,
                    decode_strings=True
                )
                return data
            except Exception as e2:
                logger.error(f"Alternative parsing also failed: {str(e2)}")
                return None
    
    def format_message_content(self, content, user_name, course_name=None):
        """Replace placeholders in message content"""
        if not content:
            return ""
        
        formatted_content = content.replace('{{1}}', user_name)
        
        if course_name:
            formatted_content = formatted_content.replace('{{2}}', f'"{course_name}"')
        
        formatted_content = formatted_content.replace('��', '')
        formatted_content = formatted_content.replace('\r\n', '\n')
        formatted_content = formatted_content.replace('\r', '\n')
        
        return formatted_content.strip()
    






    def send_video_rewatch_template_message(self, to_number, template_sid, video_caption, user_name):
        """Send one-time video rewatch template message"""
        try:
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'

            logger.info(f"Sending one-time video rewatch template to {to_number}")
            logger.info(f"Template SID: {template_sid}")
            logger.info(f"Video Caption: {video_caption}")

            # FIXED: Extract phone number more accurately
            clean_phone = to_number.replace('whatsapp:', '').replace('+', '').strip()
            logger.info(f"Looking for user with cleaned phone: {clean_phone}")
            
            # Find user_id from phone number with better matching
            from ..models import WpUsermeta
            try:
                # Try exact match first
                user_meta = WpUsermeta.objects.filter(
                    meta_key='waid',
                    meta_value=clean_phone
                ).first()
                
                # If no exact match, try contains
                if not user_meta:
                    user_meta = WpUsermeta.objects.filter(
                        meta_key='waid',
                        meta_value__icontains=clean_phone
                    ).first()
                
                # Try with + prefix
                if not user_meta:
                    user_meta = WpUsermeta.objects.filter(
                        meta_key='waid',
                        meta_value__icontains=f"+{clean_phone}"
                    ).first()
                
                if not user_meta:
                    logger.error(f"Could not find user for phone: {clean_phone} (original: {to_number})")
                    return {'success': False, 'error': 'User not found'}
                    
                user_id = user_meta.user_id
                logger.info(f"FOUND USER: {user_id} for phone {clean_phone}")
                
                # Get current message_id from user state
                current_state_meta = WpUsermeta.objects.filter(
                    user_id=user_id,
                    meta_key='whatsapp_current_state'
                ).first()
                
                message_id = 'm-1'  # default
                if current_state_meta:
                    state_parts = current_state_meta.meta_value.split('|')
                    if len(state_parts) > 1:
                        message_id = state_parts[1]
                        
                logger.info(f"Current message_id for user {user_id}: {message_id}")
                
            except Exception as e:
                logger.error(f"Error finding user info: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return {'success': False, 'error': 'User lookup failed'}

            # CRITICAL: Deactivate any existing rewatch tokens for this user+message
            from ..models import OneTimeReWatchToken
            existing_tokens = OneTimeReWatchToken.objects.filter(
                user_id=user_id,
                message_id=message_id,
                is_used=False
            )
            
            deactivated_count = existing_tokens.count()
            if deactivated_count > 0:
                existing_tokens.update(is_used=True, used_at=timezone.now())
                logger.info(f"Deactivated {deactivated_count} existing rewatch tokens for user {user_id}, message {message_id}")

            # Create new one-time rewatch token (expires in 30 minutes)
            rewatch_token = OneTimeReWatchToken.objects.create(
                user_id=user_id,
                message_id=message_id,
                video_id='', # Will be filled from context
                video_caption=video_caption,
                expires_at=timezone.now() + timedelta(minutes=30),
                meta_data=json.dumps({
                    'phone_number': clean_phone,
                    'template_sid': template_sid,
                    'created_at': timezone.now().isoformat()
                })
            )

            logger.info(f"Created one-time rewatch token: {rewatch_token.token} for user {user_id}")

            # Prepare template variables with one-time token
            template_variables = {
                "1": f"{user_name}",
                "2": f"{video_caption}",
                "3": str(rewatch_token.token),  # Pass token as parameter
            }

            logger.info(f"Video rewatch template variables created successfully")

            message = self.client.messages.create(
                from_=self.from_number,
                to=to_number,
                content_sid=template_sid,
                content_variables=json.dumps(template_variables)
            )

            logger.info(f"WhatsApp one-time video rewatch template sent successfully. SID: {message.sid}")

            return {
                'success': True,
                'message_sid': message.sid,
                'message_type': 'video_rewatch_template',
                'is_one_time': True,
                'token': str(rewatch_token.token),
                'expires_at': rewatch_token.expires_at.isoformat(),
                'user_id': user_id,  # Include for debugging
                'message_id': message_id  # Include for debugging
            }

        except Exception as e:
            logger.error(f"Error sending one-time video rewatch template message: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}

    
        
    def send_dynamic_message_with_template(self, to_number, message_data, user_name, course_name=None):
        """Send dynamic message using templates when possible"""
        try:
            if isinstance(message_data, dict):
                message_type = message_data.get('type', '')
                message_id = message_data.get('id', '')
            else:
                message_type = getattr(message_data, 'type', '')
                message_id = getattr(message_data, 'id', '')
            
            logger.info(f"Processing message {message_id} of type: {message_type}")
            
            if message_type == 'button':
                # Handle button messages (like language selection)
                if isinstance(message_data, dict):
                    button_data = message_data.get('button', {})
                else:
                    button_data = getattr(message_data, 'button', {})
                
                if button_data and len(button_data) > 0:
                    first_button = button_data.get(0) or button_data.get('0')
                    
                    if not first_button and isinstance(button_data, dict):
                        first_button = list(button_data.values())[0]
                    
                    if first_button:
                        if isinstance(first_button, dict):
                            question = first_button.get('question', '')
                            options = first_button.get('options', {})
                        else:
                            question = getattr(first_button, 'question', '')
                            options = getattr(first_button, 'options', {})
                        
                        # Check if this is a language selection message
                        if 'language' in question.lower() and 'english' in str(options).lower() and 'hindi' in str(options).lower():
                            # Use template for language selection
                            template_sid = getattr(settings, 'WHATSAPP_LANGUAGE_SELECT_TEMPLATE_SID', None)
                            if template_sid:
                                template_variables = {
                                    "1": user_name
                                }
                                logger.info(f"Using language selection template: {template_sid}")
                                return self.send_template_message(to_number, template_sid, template_variables)
                                
            elif message_type == 'quiz':
                # Use quiz template for quiz messages
                quiz_template_sid = getattr(settings, 'WHATSAPP_QUIZ_TEMPLATE_SID', None)
                logger.info(f"Quiz template SID: {quiz_template_sid}")
                
                if quiz_template_sid:
                    # Get quiz data
                    if isinstance(message_data, dict):
                        quiz_data = message_data.get('quiz', {})
                    else:
                        quiz_data = getattr(message_data, 'quiz', {})
                    
                    first_quiz = quiz_data.get(0) if quiz_data else None
                    
                    if first_quiz:
                        if isinstance(first_quiz, dict):
                            question = first_quiz.get('question', '')
                            options = first_quiz.get('options', {})
                        else:
                            question = getattr(first_quiz, 'question', '')
                            options = getattr(first_quiz, 'options', {})
                        
                        logger.info(f"Sending quiz template with {len(options)} options")
                        
                        # Send quiz template
                        return self.send_quiz_template_message(
                            to_number=to_number,
                            template_sid=quiz_template_sid,
                            question=question,
                            options=options,
                            user_name=user_name
                        )
                    else:
                        logger.info("No quiz data found, using regular message")
                else:
                    logger.info("No quiz template SID configured, using regular message")
            elif message_type == 'video':
                # Use existing video lesson template with dynamic delay
                video_template_sid = getattr(settings, 'WHATSAPP_VIDEO_LESSON_TEMPLATE_SID', None)
                logger.info(f"Using video lesson template: {video_template_sid}")
                
                if video_template_sid:
                    # Get video data
                    if isinstance(message_data, dict):
                        video_url = message_data.get('media_id', '')
                        video_caption = message_data.get('video_caption', '')
                        lesson_name = message_data.get('lesson_name', 'Video Lesson')
                        
                        # EXTRACT DYNAMIC DELAY
                        video_delay = None
                        try:
                            delay = message_data.get('delay', '8')
                            video_delay = int(delay)
                        except:
                            try:
                                video_length = message_data.get('video_length', '300')
                                video_delay = int(video_length)
                            except:
                                video_delay = 8  # Default delay
                    else:
                        video_url = getattr(message_data, 'media_id', '')
                        video_caption = getattr(message_data, 'video_caption', '')
                        lesson_name = getattr(message_data, 'lesson_name', 'Video Lesson')
                        video_delay = 8  # Default delay

                    # FIXED: Ensure video_caption is properly set
                    if not video_caption or video_caption.strip() == '':
                        video_caption = lesson_name or 'Video Lesson'
                    
                    logger.info(f"Final video caption being used: '{video_caption}'")
                    
                    # Send video template with dynamic delay and proper caption
                    video_result = self.send_video_template_message(
                        to_number=to_number,
                        template_sid=video_template_sid,
                        video_url=video_url,
                        video_caption=video_caption,
                        user_name=user_name,
                        video_delay=video_delay
                    )
                    
                    if video_result.get('success'):
                        logger.info("Video template sent successfully, rewatch template will be handled by send_next_message_by_id")
                        # Store additional info for rewatch
                        video_result.update({
                            'video_url': video_url,
                            'video_caption': video_caption,
                            'send_rewatch_template': True,
                            'dynamic_delay': video_delay
                        })
                        return video_result
                    else:
                        logger.error(f"Failed to send video template: {video_result.get('error')}")
                        return video_result
                else:
                    logger.info("No video template SID configured, using regular message")
            
                    
            # For non-template messages or fallback, use regular method
            return self.send_dynamic_message_with_course(to_number, message_data, user_name, course_name)
            
        except Exception as e:
            logger.error(f"Failed to send template message: {str(e)}")
            # Fallback to regular message
            return self.send_dynamic_message_with_course(to_number, message_data, user_name, course_name)

    
    def send_dynamic_message_with_course(self, to_number, message_data, user_name, course_name=None):
        """Send a dynamic message with course name support"""
        try:
            if isinstance(message_data, dict):
                message_type = message_data.get('type', '')
                content = message_data.get('content', '')
                message_id = message_data.get('id', '')
            else:
                message_type = getattr(message_data, 'type', '')
                content = getattr(message_data, 'content', '')
                message_id = getattr(message_data, 'id', '')
            
            logger.info(f"Processing message {message_id} of type: {message_type}")
            
            if message_type == 'button':
                if isinstance(message_data, dict):
                    button_data = message_data.get('button', {})
                else:
                    button_data = getattr(message_data, 'button', {})
                
                if button_data and len(button_data) > 0:
                    first_button = button_data.get(0) or button_data.get('0')
                    
                    if not first_button and isinstance(button_data, dict):
                        first_button = list(button_data.values())[0]
                    
                    if first_button:
                        if isinstance(first_button, dict):
                            question = first_button.get('question', '')
                            options = first_button.get('options', {})
                        else:
                            question = getattr(first_button, 'question', '')
                            options = getattr(first_button, 'options', {})
                        
                        formatted_question = self.format_message_content(question, user_name, course_name)
                        
                        # Create the message lines
                        message_lines = [formatted_question, ""]  # Question + empty line
                        
                        if options:
                            if isinstance(options, dict):
                                for i, key in enumerate(sorted(options.keys()), 1):
                                    option_text = options[key]
                                    if isinstance(option_text, bytes):
                                        option_text = option_text.decode('utf-8')
                                    
                                    # Add emojis for better visual appeal
                                    if 'english' in str(option_text).lower():
                                        emoji = "🇺🇸"
                                    elif 'hindi' in str(option_text).lower():
                                        emoji = "🇮🇳"
                                    else:
                                        emoji = "▶️"
                                    
                                    message_lines.append(f"{emoji} {i}. {option_text}")
                        
                        message_lines.append("")  # Empty line
                        message_lines.append("💬 Reply with number (1 or 2) or language name")
                        
                        message_body = "\n".join(message_lines)
                        
                    else:
                        message_body = self.format_message_content(content, user_name, course_name)
                        
                else:
                    message_body = self.format_message_content(content, user_name, course_name)
                    
            elif message_type == 'text':
                message_body = self.format_message_content(content, user_name, course_name)
                
            elif message_type == 'video':
                if isinstance(message_data, dict):
                    video_url = message_data.get('media_id', '')
                    video_caption = message_data.get('video_caption', '')
                    lesson_name = message_data.get('lesson_name', '')
                else:
                    video_url = getattr(message_data, 'media_id', '')
                    video_caption = getattr(message_data, 'video_caption', '')
                    lesson_name = getattr(message_data, 'lesson_name', '')
                
                if not video_caption and lesson_name:
                    video_caption = lesson_name
                elif not video_caption:
                    video_caption = "Video Lesson"
                
                # Format video message
                message_lines = [
                    f"🎬 {video_caption}",
                    "",
                    f"📹 Video: {video_url}",
                    "",
                    "Please watch the video and reply 'WATCHED' when you're done.",
                    "",
                    "Commands: WATCHED | NEXT | HELP"
                ]
                
                message_body = "\n".join(message_lines)
                
            elif message_type == 'quiz':
                if isinstance(message_data, dict):
                    quiz_data = message_data.get('quiz', {})
                else:
                    quiz_data = getattr(message_data, 'quiz', {})
                    
                first_quiz = quiz_data.get(0) if quiz_data else None
                
                if first_quiz:
                    if isinstance(first_quiz, dict):
                        question = first_quiz.get('question', '')
                        options = first_quiz.get('options', {})
                    else:
                        question = getattr(first_quiz, 'question', '')
                        options = getattr(first_quiz, 'options', {})
                    
                    formatted_question = self.format_message_content(question, user_name, course_name)
                    
                    message_lines = [formatted_question, ""]
                    
                    if options:
                        if isinstance(options, dict):
                            for i, key in enumerate(sorted(options.keys()), 1):
                                option_text = options[key]
                                if isinstance(option_text, bytes):
                                    option_text = option_text.decode('utf-8')
                                message_lines.append(f"{i}. {option_text}")
                    
                    message_lines.append("")
                    message_lines.append("💭 Reply with the number of your answer")
                    
                    message_body = "\n".join(message_lines)
                else:
                    message_body = "Quiz question not available."
            else:
                message_body = self.format_message_content(content, user_name, course_name)
            
            logger.info(f"Final message body: {message_body[:200]}...")
            return self.send_message(to_number, message_body)
            
        except Exception as e:
            logger.error(f"Failed to send dynamic message: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}
    
    def send_course_introduction_message(self, to_number, user_name, course_name):
        """Send personalized course introduction message"""
        intro_message = f"""🎉 Hello {user_name}! Welcome to Embyte LMS! 🎉

🎯 **You've been enrolled in: "{course_name}"**

🎓 **Your Learning Journey Starts Now!**

**Ready to transform your skills, {user_name}?**

Your journey in "{course_name}" begins now! 🚀

Type 'START' to begin your first lesson or 'HELP' if you need assistance.

---
*Embyte LMS Team - Making Learning Accessible & Engaging!* 📚✨

**Course:** {course_name}
**Student:** {user_name}
**Enrollment Date:** Today"""
        
        return self.send_message(to_number, intro_message)

# Create a global instance
whatsapp_service = WhatsAppService()