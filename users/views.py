from django.views import View
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, JsonResponse
from .services.secure_video_service import secure_video_service
import json
from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.http import HttpResponse
import xml.etree.ElementTree as ET


# Add these imports at the top
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
import logging
import phpserialize
import traceback
import threading
import time
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import jwt

# Import your models
from .models import CourseReminderLog, CourseReminderSettings, WpUsers, WpPosts, WpPostmeta, WpUsermeta
from .services.whatsapp_service import whatsapp_service
from .services.course_tracking_service import course_tracker


from djoser.social.views import ProviderAuthView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

logger = logging.getLogger(__name__)


class CustomProviderAuthView(ProviderAuthView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 201:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            response.set_cookie(
                'access',
                access_token,
                max_age=settings.AUTH_COOKIE_MAX_AGE,
                path=settings.AUTH_COOKIE_PATH,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )
            response.set_cookie(
                'refresh',
                refresh_token,
                max_age=settings.AUTH_COOKIE_MAX_AGE,
                path=settings.AUTH_COOKIE_PATH,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )

        return response


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            response.set_cookie(
                'access',
                access_token,
                max_age=settings.AUTH_COOKIE_MAX_AGE,
                path=settings.AUTH_COOKIE_PATH,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )
            response.set_cookie(
                'refresh',
                refresh_token,
                max_age=settings.AUTH_COOKIE_MAX_AGE,
                path=settings.AUTH_COOKIE_PATH,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )

        return response


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh')

        if refresh_token:
            request.data['refresh'] = refresh_token

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get('access')

            response.set_cookie(
                'access',
                access_token,
                max_age=settings.AUTH_COOKIE_MAX_AGE,
                path=settings.AUTH_COOKIE_PATH,
                secure=settings.AUTH_COOKIE_SECURE,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )

        return response


class CustomTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        access_token = request.COOKIES.get('access')

        if access_token:
            request.data['token'] = access_token

        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie('access')
        response.delete_cookie('refresh')

        return response


@api_view(['POST'])
@permission_classes([AllowAny])
def send_introduction_message(request):
    """Send dynamic introduction message using templates when possible"""
    try:
        user_id = request.data.get('user_id')
        course_id = request.data.get('course_id')
        use_template = request.data.get('use_template', True)
        force_template = request.data.get('force_template', False)  # New parameter

        if not user_id or not course_id:
            return Response(
                {'error': 'Both user_id and course_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset user state at the beginning
        logger.info(f"Resetting user state for user_id: {user_id}")
        reset_user_state(user_id, course_id)

        # Fetch user information
        try:
            user = WpUsers.objects.get(id=user_id)
            user_name = user.display_name or user.user_nicename or "Student"
        except WpUsers.DoesNotExist:
            return Response(
                {'error': f'User with ID {user_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Fetch phone number from WpUsermeta
        try:
            phone_meta = WpUsermeta.objects.get(
                user_id=user_id,
                meta_key='waid'
            )
            to_number = phone_meta.meta_value

            if not to_number:
                return Response(
                    {'error': f'WhatsApp number not found for user ID {user_id}'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Format phone number if needed
            if not to_number.startswith('+'):
                to_number = f'+{to_number}'

        except WpUsermeta.DoesNotExist:
            return Response(
                {'error': f'WhatsApp number (waid) not found for user ID {user_id}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Fetch course information
        try:
            course = WpPosts.objects.get(
                id=course_id, post_type='sfwd-courses')
            course_name = course.post_title or "Course"

        except WpPosts.DoesNotExist:
            return Response(
                {'error': f'Course with ID {course_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # NEW: Check if this is a new contact
        contact_eligibility = whatsapp_service.check_contact_eligibility(to_number)
        is_new_contact = not contact_eligibility.get('can_send_regular', False)
        
        logger.info(f"Contact eligibility for {to_number}: {contact_eligibility}")

        # If it's a new contact or force_template is True, use template approach
        # If it's a new contact or force_template is True, use template approach
        if is_new_contact or force_template:
            logger.info(f"Using template approach for new contact: {to_number}")
            
            # Send welcome template for new contacts
            welcome_template_sid = getattr(settings, 'WHATSAPP_WELCOME_TEMPLATE_SID', None)
            
            if welcome_template_sid:
                template_variables = {
                    "1": user_name
                }
                
                result = whatsapp_service.send_template_message(
                    to_number=to_number,
                    template_sid=welcome_template_sid,
                    template_variables=template_variables
                )
                
                if result.get('success'):
                    # FIXED: Store the actual course_id instead of 'welcome'
                    initial_state = {
                        'course_id': str(course_id),  # ✅ Store the REAL course_id here
                        'message_id': 'welcome',
                        'step': 'awaiting_response',
                        'language': None,
                        'user_id': user_id
                    }
                    
                    update_user_state(user_id, initial_state)
                    logger.info(f"Stored course_id {course_id} in user state for welcome template response")
                    
                    return Response({
                        'success': True,
                        'message': 'Welcome template sent to new contact',
                        'message_sid': result.get('message_sid', ''),
                        'to_number': to_number,
                        'user_name': user_name,
                        'course_name': course_name,
                        'user_id': user_id,
                        'course_id': course_id,  # ✅ Return the actual course_id
                        'method': 'template',
                        'is_new_contact': True,
                        'contact_status': contact_eligibility.get('reason', 'unknown')
                    }, status=status.HTTP_200_OK)
                else:
                    logger.error(f"Failed to send welcome template: {result.get('error')}")
                    return Response({
                        'success': False,
                        'error': 'Failed to send welcome template to new contact',
                        'details': result.get('error'),
                        'contact_status': contact_eligibility.get('reason', 'unknown')
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'success': False,
                    'error': 'No welcome template configured for new contacts',
                    'suggestion': 'Configure WHATSAPP_WELCOME_TEMPLATE_SID in settings'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # For existing contacts within 24-hour window, proceed with regular flow
        # Fetch messageData from WpPostmeta
        try:
            message_meta = WpPostmeta.objects.get(
                post_id=course_id,
                meta_key='messageData'
            )
            serialized_data = message_meta.meta_value

            if not serialized_data:
                return Response(
                    {'error': f'Message data not found for course ID {course_id}'},
                    status=status.HTTP_404_NOT_FOUND
                )

        except WpPostmeta.DoesNotExist:
            return Response(
                {'error': f'Message data (messageData) not found for course ID {course_id}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Parse the serialized message data
        try:
            message_data = whatsapp_service.parse_serialized_data(
                serialized_data)

            if not message_data:
                return Response(
                    {'error': 'Failed to parse message data'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"Failed to parse message data: {str(e)}")
            return Response(
                {'error': f'Invalid message data format: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Send the first message using the regular flow
        initial_state = {
            'course_id': str(course_id),
            'message_id': 'm-1',
            'step': 'course_selection',
            'language': None,
            'user_id': user_id
        }

        # Send the first message
        result = send_next_message_by_id(
            from_number=to_number,
            user_name=user_name,
            message_id='m-1',
            course_data=message_data,
            current_state=initial_state,
            language=None
        )

        if result.get('success'):
            # Update user state with the result
            if result.get('next_state'):
                update_user_state(user_id, result['next_state'])

            return Response({
                'success': True,
                'message': 'Introduction message sent successfully!',
                'message_sid': result.get('message_sid', ''),
                'to_number': to_number,
                'user_name': user_name,
                'course_name': course_name,
                'user_id': user_id,
                'course_id': course_id,
                'current_message': 'm-1',
                'method': 'regular',
                'is_new_contact': False,
                'contact_status': contact_eligibility.get('reason', 'within_window')
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'Failed to send introduction message',
                'details': result.get('error', 'Unknown error')
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Error in send_introduction_message: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



def reset_user_state(user_id, course_id):
    """Reset user's state to start a fresh course"""
    try:
        # Ensure course_id is valid
        if not course_id or course_id == 'None' or course_id == 'null':
            course_id = 10362  # Default course ID
            
        # Convert to string for consistent storage
        course_id = str(course_id)
        
        # Set initial state: course_id|m-1|course_selection|None
        initial_state = {
            'course_id': course_id,
            'message_id': 'm-1',
            'step': 'course_selection',
            'language': None,
            'user_id': user_id
        }

        # Format: course_id|message_id|step|language
        state_value = f"{initial_state['course_id']}|{initial_state['message_id']}|{initial_state['step']}|"

        # Update or create user state
        user_meta, created = WpUsermeta.objects.update_or_create(
            user_id=user_id,
            meta_key='whatsapp_current_state',
            defaults={'meta_value': state_value}
        )

        logger.info(f"Reset user {user_id} state to: {state_value} (course_id: {course_id})")

        # Also clear any other course-related meta data if needed
        # Clear previous progress
        WpUsermeta.objects.filter(
            user_id=user_id,
            meta_key='course_progress'
        ).delete()

        # Clear quiz scores
        WpUsermeta.objects.filter(
            user_id=user_id,
            meta_key='quiz_scores'
        ).delete()

        logger.info(f"Cleared previous progress data for user {user_id}")

    except Exception as e:
        logger.error(f"Error resetting user state: {str(e)}")
        raise e


def handle_preflight(request):
    if request.method == "OPTIONS":
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "*"
        response["Access-Control-Max-Age"] = "86400"
        return response
    return None


# Add these imports at the top

# Import your models

logger = logging.getLogger(__name__)

# COMPLETE WHATSAPP WEBHOOK IMPLEMENTATION


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):
    """Complete WhatsApp webhook handler with CORS support"""

    def dispatch(self, request, *args, **kwargs):
        """Handle CORS and routing"""
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            response = HttpResponse()
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "*"
            response["Access-Control-Max-Age"] = "86400"
            return response

        # Process normal requests
        response = super().dispatch(request, *args, **kwargs)

        # Add CORS headers to all responses
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "*"
        response["Access-Control-Allow-Credentials"] = "true"

        return response

    def get(self, request):
        """Handle webhook verification from WhatsApp/Meta"""
        try:
            # Get verification parameters from query string
            hub_mode = request.GET.get('hub.mode')
            hub_verify_token = request.GET.get('hub.verify_token')
            hub_challenge = request.GET.get('hub.challenge')

            logger.info(f"Webhook verification attempt:")
            logger.info(f"  Mode: {hub_mode}")
            logger.info(f"  Token: {hub_verify_token}")
            logger.info(f"  Challenge: {hub_challenge}")

            # Your webhook verify token (set this in your environment)
            expected_verify_token = getattr(
                settings, 'WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'your_webhook_verify_token')

            # Verify the token and mode
            if hub_mode == 'subscribe' and hub_verify_token == expected_verify_token:
                logger.info("Webhook verification successful")
                return HttpResponse(hub_challenge, content_type='text/plain', status=200)
            else:
                logger.warning("Webhook verification failed")
                logger.warning(f"Expected token: {expected_verify_token}")
                logger.warning(f"Received token: {hub_verify_token}")
                return HttpResponse("Verification failed", status=403)

        except Exception as e:
            logger.error(f"Webhook verification error: {e}")
            return HttpResponse("Verification error", status=500)

    def post(self, request):
        """Handle incoming WhatsApp messages"""
        try:
            logger.info("=" * 60)
            logger.info("WHATSAPP WEBHOOK RECEIVED")
            logger.info("=" * 60)

            # Parse the webhook payload
            logger.info(f"Request content type: {request}")
            webhook_data = self._parse_webhook_data(request)
            logger.info(f"Parsed webhook data: {webhook_data}")
            if not webhook_data:
                return self._empty_response()

            # Process each message in the webhook
            for message_data in webhook_data:
                logger.info(f"Processing message: {message_data}")
                self._process_message(message_data)

            return self._empty_response()

        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._empty_response()

    def _parse_webhook_data(self, request):
        """Parse webhook data from different sources"""
        try:
            # Try to parse as JSON first (Meta/Facebook format)
            if request.content_type and 'application/json' in request.content_type:
                body = json.loads(request.body.decode('utf-8'))
                logger.info("Received JSON webhook data")
                return self._parse_meta_webhook(body)

            # Parse as form data (Twilio format)
            elif request.POST:
                logger.info("Received form-encoded webhook data")
                return self._parse_twilio_webhook(request.POST)

            else:
                logger.error("Unsupported content type or empty request")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return None
        except Exception as e:
            logger.error(f"Data parsing error: {e}")
            return None

    def _parse_meta_webhook(self, body):
        """Parse Meta/Facebook WhatsApp webhook format"""
        try:
            messages = []

            if 'entry' in body:
                for entry in body['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if change.get('field') == 'messages':
                                value = change.get('value', {})

                                # Process messages
                                if 'messages' in value:
                                    for message in value['messages']:
                                        parsed_message = {
                                            'platform': 'meta',
                                            'from_number': message.get('from', ''),
                                            'message_id': message.get('id', ''),
                                            'timestamp': message.get('timestamp', ''),
                                            'type': message.get('type', 'text'),
                                            'body': '',
                                            'button_payload': '',
                                            'button_text': '',
                                            'profile_name': '',
                                            'wa_id': message.get('from', '')
                                        }

                                        # Extract message content based on type
                                        if message['type'] == 'text':
                                            parsed_message['body'] = message.get(
                                                'text', {}).get('body', '')
                                        elif message['type'] == 'button':
                                            parsed_message['button_payload'] = message.get(
                                                'button', {}).get('payload', '')
                                            parsed_message['button_text'] = message.get(
                                                'button', {}).get('text', '')
                                            parsed_message['body'] = parsed_message['button_text'] or parsed_message['button_payload']
                                        elif message['type'] == 'interactive':
                                            # Handle interactive messages (buttons, lists, etc.)
                                            interactive = message.get(
                                                'interactive', {})
                                            if interactive.get('type') == 'button_reply':
                                                button_reply = interactive.get(
                                                    'button_reply', {})
                                                parsed_message['button_payload'] = button_reply.get(
                                                    'id', '')
                                                parsed_message['button_text'] = button_reply.get(
                                                    'title', '')
                                                parsed_message['body'] = parsed_message['button_text'] or parsed_message['button_payload']

                                        # Get profile info
                                        contacts = value.get('contacts', [])
                                        for contact in contacts:
                                            if contact.get('wa_id') == message.get('from'):
                                                parsed_message['profile_name'] = contact.get(
                                                    'profile', {}).get('name', '')
                                                break

                                        messages.append(parsed_message)

                                        logger.info(f"Parsed Meta message:")
                                        logger.info(
                                            f"   From: {parsed_message['from_number']}")
                                        logger.info(
                                            f"   Type: {parsed_message['type']}")
                                        logger.info(
                                            f"   Body: {parsed_message['body']}")
                                        logger.info(
                                            f"   Button: {parsed_message['button_payload']}")

            return messages

        except Exception as e:
            logger.error(f"Meta webhook parsing error: {e}")
            return None

    def _parse_twilio_webhook(self, form_data):
        """Parse Twilio WhatsApp webhook format"""
        try:
            messages = []

            # Extract data from Twilio webhook (form-encoded)
            from_number = form_data.get('From', '').replace('whatsapp:', '')
            to_number = form_data.get('To', '').replace('whatsapp:', '')
            body = form_data.get('Body', '').strip()
            message_sid = form_data.get('MessageSid', '')
            wa_id = form_data.get('WaId', '')
            profile_name = form_data.get('ProfileName', '')
            message_type = form_data.get('MessageType', 'text')
            button_payload = form_data.get('ButtonPayload', '')
            button_text = form_data.get('ButtonText', '')


            logger.info(f"Received Twilio webhook data:")
            logger.info(f"   From: {from_number}")
            logger.info(f"   To: {to_number}")
            logger.info(f"   Body: {body}")
            logger.info(f"   Message SID: {message_sid}")
            logger.info(f"   WA ID: {wa_id}")
            logger.info(f"   Profile Name: {profile_name}")
            logger.info(f"   Message Type: {message_type}")
            logger.info(f"   Button Payload: {button_payload}")
            logger.info(f"   Button Text: {button_text}")



            # For button responses, use ButtonText or ButtonPayload instead of Body
            if message_type == 'button':
                if button_text:
                    body = button_text
                elif button_payload:
                    body = button_payload

            if message_type == 'interactive':
                # Handle interactive messages
                flow_data = form_data.get('FlowData', '')
                interactive_data = form_data.get('InteractiveData', '')
                body = '' # Initialize body for interactive messages

                logger.info(f"Interactive message data: {form_data}")
                logger.info(f"Flow data: {flow_data}")
                logger.info(f"Interactive data: {interactive_data}")

                # Parse FlowData
                if flow_data:
                    try:
                        logger.info(f"Parsing FlowData: {flow_data}")
                        # FlowData is double-encoded, so it needs to be parsed twice.
                        unwrapped_data = json.loads(flow_data)
                        flow_data_json = json.loads(unwrapped_data) if isinstance(unwrapped_data, str) else unwrapped_data
                        logger.info(f"FlowData JSON: {flow_data_json}")
                        
                        # Extract the answer from the nested structure
                        id_two_data = flow_data_json.get('id_two', {})
                        if isinstance(id_two_data, dict):
                            body = id_two_data.get('Select_the_correct_answer', '')
                            logger.info(f"Extracted answer from FlowData: {body}")
                        else:
                            logger.warning(f"id_two_data is not a dict: {type(id_two_data)}")
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing FlowData JSON: {str(e)}")
                    except Exception as e:
                        logger.error(f"FlowData parsing error: {str(e)}")

                # Parse InteractiveData if FlowData didn't provide an answer
                elif interactive_data and not body:
                    try:
                        logger.info(f"Parsing InteractiveData: {interactive_data}")
                        # The InteractiveData from Twilio is also a JSON string
                        interactive_data_json = json.loads(interactive_data)
                        logger.info(f"InteractiveData JSON: {interactive_data_json}")
                        
                        pages = interactive_data_json.get('pages', [])
                        for page in pages:
                            if isinstance(page, dict):
                                items = page.get('items', [])
                                for item in items:
                                    if isinstance(item, dict) and item.get('label') == 'Select_the_correct_answer':
                                        body = item.get('value', '')
                                        logger.info(f"Extracted answer from InteractiveData: {body}")
                                        break  # Found answer, break from items loop
                                if body:
                                    break  # Found answer, break from pages loop
                                    
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing InteractiveData JSON: {str(e)}")
                    except Exception as e:
                        logger.error(f"InteractiveData parsing error: {str(e)}")

                # Default to "continue" if no valid answer is found
                if not body:
                    body = "continue"
                    logger.info(f"No answer extracted, using default: {body}")

            parsed_message = {
                'platform': 'twilio',
                'from_number': from_number,
                'to_number': to_number,
                'message_id': message_sid,
                'wa_id': wa_id,
                'profile_name': profile_name,
                'type': message_type,
                'body': body,
                'button_payload': button_payload,
                'button_text': button_text,
                'timestamp': str(int(time.time()))
            }

            messages.append(parsed_message)

            logger.info(f"   Parsed Twilio message:")
            logger.info(f"   From: {from_number}")
            logger.info(f"   Type: {message_type}")
            logger.info(f"   Body: {body}")
            logger.info(f"   Button: {button_payload}")

            return messages

        except Exception as e:
            logger.error(f"Twilio webhook parsing error: {e}")
            return None

    def _process_message(self, message_data):
        """Process individual message"""
        try:
            from_number = message_data['from_number']
            body = message_data['body']
            message_type = message_data['type']
            button_payload = message_data.get('button_payload', '')
            profile_name = message_data.get('profile_name', '')
            wa_id = message_data.get('wa_id', '')

            logger.info(f"   Processing message from {from_number}")
            logger.info(f"   Body: {body}")
            logger.info(f"   Type: {message_type}")

            if not from_number:
                logger.error("Missing From number in message")
                return

            # Find user by phone number
            user_info = self._find_user_by_phone(from_number, wa_id)
            if not user_info:
                self._handle_unregistered_user(from_number, body)
                return

            user_id = user_info['user_id']
            user_name = user_info['user_name']

            logger.info(f"Found user: {user_id} ({user_name})")

            # Get user's current progress/state
            current_state = get_user_current_state(user_id)
            logger.info(f"User {user_id} current state: {current_state}")

            step = current_state.get('step')

            logger.info(f"Current step for user {user_id}: {step}")

            logger.info(f"Message type: {message_type}")
            
            # ENHANCED: IGNORE UNSOLICITED TEXT MESSAGES
            # If the system is waiting for a button or interactive response,
            # ignore plain text messages to prevent accidental processing.
            if message_type == 'text' and step in ['waiting_quiz', 'waiting_button', 'waiting_video_watched']:
                logger.warning(f"Ignoring plain text message '{body}' from {from_number} during step '{step}'. Expected button/interactive response.")
                return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>', content_type='application/xml')  # FIXED: Return proper response

            # ENHANCED: Check if course is completed - ignore all messages
            if step == 'completed':
                logger.warning(f"User {user_id} has already completed the course. Ignoring incoming message '{body}'.")
                # Optionally send a completion reminder
                completion_reminder = "You have already completed this course. Thank you for learning with us!"
                whatsapp_service.send_message(from_number, completion_reminder)
                return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>', content_type='application/xml')  # FIXED: Return proper response

            # Process the message based on current state
            response_result = process_user_message(
                user_id=user_id,
                user_name=user_name,
                from_number=from_number,
                message_body=body,
                current_state=current_state,
                message_type=message_type,
                button_payload=button_payload
            )

            # Update user state
            if response_result.get('next_state'):
                update_user_state(user_id, response_result.get('next_state'))

            logger.info(f"Message processed successfully: {response_result.get('success', False)}")

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    def _find_user_by_phone(self, from_number, wa_id=None):
        try:
            clean_phone = wa_id if wa_id else from_number.replace('+', '').replace(' ', '')
            logger.info(f"Looking for user with phone: {clean_phone}")

            # Try with wa_id first
            user_meta = WpUsermeta.objects.filter(
                meta_key='waid',
                meta_value__icontains=clean_phone
            ).first()

            # Try with original number (with +)
            if not user_meta:
                user_meta = WpUsermeta.objects.filter(
                    meta_key='waid',
                    meta_value__icontains=from_number
                ).first()

            # Try with + stripped
            if not user_meta and from_number.startswith('+'):
                user_meta = WpUsermeta.objects.filter(
                    meta_key='waid',
                    meta_value__icontains=from_number[1:]
                ).first()

            

            if not user_meta:
                logger.warning(f"User not found for phone: {from_number}")
                return None

            # Get user details
            user = WpUsers.objects.get(id=user_meta.user_id)
            user_name = user.display_name or user.user_nicename or "Student"

            return {
                'user_id': user_meta.user_id,
                'user_name': user_name,
                'user': user
            }

        except WpUsers.DoesNotExist:
            logger.warning(
                f"User ID {user_meta.user_id} not found in users table")
            return None
        except Exception as e:
            logger.error(f"Error finding user: {e}")
            return None

    def _handle_unregistered_user(self, from_number, message_body):
        """Handle messages from unregistered users"""
        try:
            registration_message = """
**Welcome!**

It looks like you're not registered in our system yet. 

 **Please visit our website to complete your registration and get access to our courses:**
https://embyte-learn.com

**Need help?** Contact our support team.

Thank you! 
            """

            result = whatsapp_service.send_message(
                from_number, registration_message)
            logger.info(
                f"Registration message sent to unregistered user: {result.get('success', False)}")

        except Exception as e:
            logger.error(f"Error handling unregistered user: {str(e)}")

    def _empty_response(self):
        """Return empty response for WhatsApp webhook"""
        return HttpResponse(
            '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            content_type='application/xml',
            status=200
        )

# Function-based webhook alternative


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def whatsapp_webhook_function(request):
    """Alternative function-based webhook handler"""

    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "*"
        response["Access-Control-Max-Age"] = "86400"
        return response

    try:
        # Handle GET request (webhook verification)
        if request.method == 'GET':
            hub_mode = request.GET.get('hub.mode')
            hub_verify_token = request.GET.get('hub.verify_token')
            hub_challenge = request.GET.get('hub.challenge')

            expected_verify_token = getattr(
                settings, 'WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'your_webhook_verify_token')

            if hub_mode == 'subscribe' and hub_verify_token == expected_verify_token:
                logger.info("Function webhook verification successful")
                response = HttpResponse(
                    hub_challenge, content_type='text/plain')
            else:
                logger.warning("Function webhook verification failed")
                response = HttpResponse("Verification failed", status=403)

        # Handle POST request (incoming messages)
        elif request.method == 'POST':
            try:
                # Try JSON format first
                if request.content_type and 'application/json' in request.content_type:
                    body = json.loads(request.body.decode('utf-8'))
                    logger.info("Function received JSON webhook")
                    # Process JSON webhook (Meta format)
                    # Add your JSON processing logic here

                else:
                    # Process form data (Twilio format)
                    logger.info("Function received form webhook")

                    # Extract Twilio data
                    from_number = request.POST.get(
                        'From', '').replace('whatsapp:', '')
                    body_text = request.POST.get('Body', '').strip()
                    message_type = request.POST.get('MessageType', 'text')
                    button_payload = request.POST.get('ButtonPayload', '')

                    if message_type == 'button' and button_payload:
                        body_text = button_payload

                    if not body_text:
                        body_text = "continue"

                    logger.info(f"Processing: {from_number} -> {body_text}")

                    # Find user and process message
                    # Add your message processing logic here

                response = HttpResponse(
                    '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                    content_type='application/xml'
                )

            except Exception as e:
                logger.error(f"Function webhook processing error: {e}")
                response = HttpResponse(
                    '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                    content_type='application/xml'
                )

        # Add CORS headers
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "*"

        return response

    except Exception as e:
        logger.error(f"Function webhook error: {str(e)}")
        response = HttpResponse("Error", status=500)
        response["Access-Control-Allow-Origin"] = "*"
        return response

# Main webhook API view (current implementation improved)


@csrf_exempt
@api_view(['GET', 'POST', 'OPTIONS'])
@permission_classes([AllowAny])
def whatsapp_webhook(request):
    """Main WhatsApp webhook handler"""
    
    # Handle preflight OPTIONS
    if request.method == 'OPTIONS':
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "*"
        response["Access-Control-Max-Age"] = "86400"
        return response

    # Handle GET (webhook verification)
    if request.method == 'GET':
        try:
            verify_token = request.GET.get('hub.verify_token')
            challenge = request.GET.get('hub.challenge')
            mode = request.GET.get('hub.mode')

            expected_token = getattr(settings, 'WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'your_webhook_verify_token')

            if mode == 'subscribe' and verify_token == expected_token:
                logger.info("Webhook verification successful")
                response = HttpResponse(challenge, content_type='text/plain')
            else:
                logger.warning("Webhook verification failed")
                response = HttpResponse("Verification failed", status=403)

            response["Access-Control-Allow-Origin"] = "*"
            return response

        except Exception as e:
            logger.error(f"Verification error: {e}")
            response = HttpResponse("Error", status=500)
            response["Access-Control-Allow-Origin"] = "*"
            return response

    # Handle POST (incoming messages)
    try:
        logger.info("=" * 50)
        logger.info("WEBHOOK RECEIVED")
        logger.info("=" * 50)
        logger.info(f"Request Method: {request.method}")
        logger.info(f"Content Type: {request.content_type}")

        # Only use request.POST for form-encoded data from Twilio
        form_data = request.POST.copy()
        logger.info(f"Form data keys: {list(form_data.keys())}")

        # Extract data from Twilio webhook (form-encoded)
        from_number = form_data.get('From', '').replace('whatsapp:', '')
        to_number = form_data.get('To', '').replace('whatsapp:', '')
        body = form_data.get('Body', '').strip()
        message_sid = form_data.get('MessageSid', '')
        wa_id = form_data.get('WaId', '')
        profile_name = form_data.get('ProfileName', '')
        message_type = form_data.get('MessageType', 'text')
        button_payload = form_data.get('ButtonPayload', '')
        button_text = form_data.get('ButtonText', '')

        logger.info(f"Parsed Data:")
        logger.info(f"  From: {from_number}")
        logger.info(f"  Body: {body}")
        logger.info(f"  MessageType: {message_type}")
        logger.info(f"  ButtonPayload: {button_payload}")
        logger.info(f"  ButtonText: {button_text}")

        if not from_number:
            logger.error("Missing From number in request")
            return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                                content_type='application/xml', status=400)
        
        # For button responses, use ButtonText or ButtonPayload instead of Body
        if message_type == 'button':
            if button_text:
                body = button_text
            elif button_payload:
                body = button_payload

        if not body:
            body = "continue"  # Default action if no body

        logger.info(f"Final processed body: {body}")

        # Find user by phone number
        try:
            clean_phone = wa_id if wa_id else from_number.replace(
                '+', '').replace(' ', '')
            logger.info(f"Looking for user with phone: {clean_phone}")

            user_meta = WpUsermeta.objects.filter(
                meta_key='waid',
                meta_value__icontains=clean_phone
            ).first()

            if not user_meta:
                user_meta = WpUsermeta.objects.filter(
                    meta_key='waid',
                    meta_value__icontains=from_number
                ).first()

            if not user_meta:
                logger.warning(f"User not found for phone: {from_number}")
                # Send registration message but return empty response to Twilio
                handle_unregistered_user(from_number, body)
                return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                                    content_type='application/xml')

            user_id = user_meta.user_id
            user = WpUsers.objects.get(id=user_id)
            user_name = user.display_name or user.user_nicename or profile_name or "Student"

            logger.info(f"Found user: {user_id} ({user_name})")

        except WpUsers.DoesNotExist:
            logger.warning(
                f"User ID {user_meta.user_id} not found in users table")
            handle_unregistered_user(from_number, body)
            return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                                content_type='application/xml')

        # Get user's current progress/state
        current_state = get_user_current_state(user_id)
        logger.info(f"User {user_id} current state: {current_state}")

        # Process the message based on current state
        response_result = process_user_message(
            user_id=user_id,
            user_name=user_name,
            from_number=from_number,
            message_body=body,
            current_state=current_state,
            message_type=message_type,
            button_payload=button_payload
        )

        # Update user state
        if response_result.get('next_state'):
            update_user_state(user_id, response_result.get('next_state'))

        logger.info(f"Response result: {response_result}")

        # Return empty TwiML response to Twilio
        return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                            content_type='application/xml')

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Return empty TwiML response even on error
        return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                            content_type='application/xml')


def handle_unregistered_user(from_number, message_body):
    """Handle messages from unregistered users"""
    try:
        registration_message = """
Welcome! 👋 

It looks like you're not registered in our system yet. 
Please visit our website to complete your registration and get access to our courses.

Website: https://embyte-learn.com
        """

        result = whatsapp_service.send_message(
            from_number, registration_message)

        return Response({
            'success': True,
            'message': 'Registration message sent to unregistered user',
            'message_sent': result.get('success', False)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error handling unregistered user: {str(e)}")
        return Response({
            'error': 'Failed to handle unregistered user',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_user_current_state(user_id):
    """Get user's current learning state with detailed logging"""
    try:
        logger.info(f"Getting current state for user_id: {user_id}")

        # Get current state from user meta
        state_meta = WpUsermeta.objects.filter(
            user_id=user_id,
            meta_key='whatsapp_current_state'
        ).first()
        logger.info(f"State meta object: {state_meta}")

        if state_meta:
            logger.info(f"State meta value: {state_meta.meta_value}")
            state_parts = state_meta.meta_value.split('|')
            logger.info(f"State parts after split: {state_parts}")

            state_dict = {
                'course_id': state_parts[0] if len(state_parts) > 0 and state_parts[0] else None,
                'message_id': state_parts[1] if len(state_parts) > 1 else 'm-1',
                'step': state_parts[2] if len(state_parts) > 2 else 'start',
                'language': state_parts[3] if len(state_parts) > 3 else None
            }
            logger.info(f"Returning state dict: {state_dict}")
            return state_dict

        # Default state for new users
        logger.info("No state meta found, returning default state")
        default_state = {
            'course_id': None,
            'message_id': 'm-1',
            'step': 'start',
            'language': None
        }
        logger.info(f"Default state dict: {default_state}")
        return default_state

    except Exception as e:
        logger.error(f"Error getting user state: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        error_state = {
            'course_id': None,
            'message_id': 'm-1',
            'step': 'start',
            'language': None
        }
        logger.info(f"Error state dict: {error_state}")
        return error_state




def process_user_message(user_id, user_name, from_number, message_body, current_state, message_type='text', button_payload=''):
    """Process user message based on current state with enhanced welcome handling"""
    try:
        # NEW: Update user activity when they send a message
        whatsapp_service.update_user_activity(user_id)
        
        # Handle welcome template responses
        current_message_id = current_state.get('message_id', 'm-1')
        current_step = current_state.get('step', 'start')
        
        logger.info(f"Processing message - Message ID: {current_message_id}, Step: {current_step}")
        logger.info(f"User message: '{message_body}', Type: {message_type}, Button: '{button_payload}'")
        
        # CRITICAL FIX: Handle welcome template responses for "Get Started" button
        if current_message_id == 'welcome' and current_step == 'awaiting_response':
            logger.info(f"User {user_id} responded to welcome template, starting course")
            
            # Get course data
            course_id = current_state.get('course_id')
            logger.info(f"Course ID from state: {course_id}")
            
            course_data = get_course_data(course_id)
            
            if not course_data:
                error_msg = "⚠️ Sorry, I couldn't load your course data. Please contact support."
                whatsapp_service.send_message(from_number, error_msg)
                return {'success': False, 'error': 'Course data not available'}
            
            logger.info(f"Course data loaded successfully for course ID: {course_id}")
            # Start the actual course with m-1 (language selection)
            initial_state = {
                'course_id': str(course_id),
                'message_id': 'm-1',
                'step': 'course_selection',
                'language': None,
                'user_id': user_id
            }
            
            # Small delay before sending the actual course content
            time.sleep(2)
            
            result = send_next_message_by_id(
                from_number=from_number,
                user_name=user_name,
                message_id='m-1',
                course_data=course_data,
                current_state=initial_state
            )
            
            if result.get('success') and result.get('next_state'):
                update_user_state(user_id, result['next_state'])
                logger.info(f"Successfully started course for user {user_id}")
            
            return result

        # PRIORITY FIX: Handle "CONTINUE" command from reminders BEFORE video rewatch check
        if (message_body.upper().strip() == 'CONTINUE'):
            logger.info(f"User {user_id} sent CONTINUE command - checking context")
            
            # Cancel any pending reminders first
            course_id = current_state.get('course_id')
            if course_id:
                try:
                    reminder_service.cancel_pending_reminders(user_id, course_id)
                    logger.info(f"Cancelled pending reminders for user {user_id}")
                except:
                    logger.info(f"Would cancel pending reminders for user {user_id}")
            
            # FIXED: Check if this is a reminder response vs video rewatch response
            # If user is in waiting_video_watched but sent CONTINUE (not a button), 
            # treat it as course continuation, not video rewatch
            if current_step == 'waiting_video_watched' and message_type == 'text':
                logger.info(f"User {user_id} sent text CONTINUE during video state - treating as course continuation")
                
                # Move to next lesson instead of handling as video rewatch
                confirmation_msg = "Continuing to next lesson..."
                whatsapp_service.send_message(from_number, confirmation_msg)
                
                # Clean up video info
                try:
                    WpUsermeta.objects.filter(
                        user_id=user_id,
                        meta_key__startswith='current_video_'
                    ).delete()
                    logger.info(f"Cleaned up video info for user {user_id}")
                except Exception as e:
                    logger.warning(f"Could not clean up video info: {e}")
                
                # Proceed to next message
                next_message_id = get_next_message_id(current_message_id)
                if next_message_id:
                    logger.info(f"Proceeding to next message: {next_message_id}")
                    
                    course_data = get_course_data(course_id)
                    if course_data:
                        result = send_next_message_by_id(
                            from_number=from_number,
                            user_name=user_name,
                            message_id=next_message_id,
                            course_data=course_data,
                            current_state=current_state
                        )
                        
                        if result.get('success') and result.get('next_state'):
                            update_user_state(user_id, result['next_state'])
                        
                        return result
                    else:
                        return {'success': False, 'error': 'Course data not available'}
                else:
                    # Course completed
                    completion_msg = "🎉 Congratulations! You have completed the course successfully!"
                    whatsapp_service.send_message(from_number, completion_msg)
                    
                    completed_state = {
                        **current_state,
                        'step': 'completed'
                    }
                    
                    return {
                        'success': True,
                        'message': 'Course completed',
                        'next_state': completed_state
                    }
            
            # For other states, handle normally
            elif current_step not in ['waiting_video_watched', 'waiting_quiz', 'waiting_button']:
                logger.info(f"User {user_id} responded to reminder with CONTINUE in step: {current_step}")
                
                # Continue from where they left off
                current_message_id = current_state.get('message_id', 'm-1')
                course_data = get_course_data(course_id)
                
                if course_data:
                    result = send_next_message_by_id(
                        from_number=from_number,
                        user_name=user_name,
                        message_id=current_message_id,
                        course_data=course_data,
                        current_state=current_state
                    )
                    
                    if result.get('success') and result.get('next_state'):
                        update_user_state(user_id, result['next_state'])
                    
                    return result
                else:
                    return {'success': False, 'error': 'Course data not available'}

        # ORIGINAL: Handle video rewatch responses ONLY for button clicks
        if (current_message_id.startswith('m-') and 
            current_step == 'waiting_video_watched' and 
            message_type == 'button'):

            course_id = current_state.get('course_id')
            course_data = get_course_data(course_id)

            # Handle rewatch template buttons
            if button_payload and button_payload.lower() in ['rewatch', 'rewatch_video', 'video_rewatch', '1', 'yes']:
                logger.info(f"Handling video rewatch button response for user {user_id}")
                return handle_video_rewatch_response(from_number, user_name, button_payload, course_data, {**current_state, 'user_id': user_id})

            # Handle "Continue" from rewatch template (advance to next lesson)
            elif button_payload and button_payload.lower() in ['continue', '2']:
                logger.info(f"User {user_id} clicked continue on rewatch template - advancing to next lesson")
                # Cancel any pending reminders first
                if course_id:
                    try:
                        reminder_service.cancel_pending_reminders(user_id, course_id)
                        logger.info(f"Cancelled pending reminders for user {user_id}")
                    except:
                        logger.info(f"Would cancel pending reminders for user {user_id}")

                # Clean up video info
                try:
                    WpUsermeta.objects.filter(
                        user_id=user_id,
                        meta_key__startswith='current_video_'
                    ).delete()
                    logger.info(f"Cleaned up video info for user {user_id}")
                except Exception as e:
                    logger.warning(f"Could not clean up video info: {e}")

                # Proceed to next message
                next_message_id = get_next_message_id(current_message_id)
                if next_message_id:
                    logger.info(f"Proceeding to next message: {next_message_id}")
                    if course_data:
                        result = send_next_message_by_id(
                            from_number=from_number,
                            user_name=user_name,
                            message_id=next_message_id,
                            course_data=course_data,
                            current_state={**current_state, 'user_id': user_id}  # <-- Ensure user_id is present
                        )
                        if result.get('success') and result.get('next_state'):
                            update_user_state(user_id, result['next_state'])
                        return result
                    else:
                        return {'success': False, 'error': 'Course data not available'}
                else:
                    # Course completed
                    completion_msg = "🎉 Congratulations! You have completed the course successfully!"
                    whatsapp_service.send_message(from_number, completion_msg)
                    completed_state = {
                        **current_state,
                        'step': 'completed'
                    }
                    return {
                        'success': True,
                        'message': 'Course completed',
                        'next_state': completed_state
                    }

            # Handle "Continue Learning" from reminder (repeat current message)
            elif button_payload and button_payload.lower() in ['continue learning', 'course_learning']:
                logger.info(f"User {user_id} clicked continue learning from reminder - repeating current message")
                if course_data:
                    result = send_next_message_by_id(
                        from_number=from_number,
                        user_name=user_name,
                        message_id=current_message_id,  # <-- Repeat current message
                        course_data=course_data,
                        current_state=current_state
                    )
                    if result.get('success') and result.get('next_state'):
                        update_user_state(user_id, result['next_state'])
                    return result
                else:
                    return {'success': False, 'error': 'Course data not available'}

            else:
                logger.info(f"Unknown button payload during video state: {button_payload}")
                return {'success': False, 'error': 'Unknown button action'}

        # Continue with existing message processing logic...
        course_id = current_state.get('course_id')
        language = current_state.get('language')

        # Handle special case where course_id is string 'None'
        if course_id == 'None' or course_id is None:
            course_id = 10362  # Default course ID if not set

        # Get course data
        course_data = get_course_data(course_id)

        if not course_data:
            logger.error("Course data not available")
            return {'success': False, 'error': 'Course content not available'}

        # Handle different states based on current state
        if current_message_id == 'm-1' and current_step in ['start', 'course_selection']:
            if message_body.lower() in ['english', 'hindi'] or button_payload in ['0', '1']:
                return handle_language_selection(from_number, user_name, message_body, course_data, current_state, button_payload)
            else:
                return send_language_selection_message(from_number, user_name, course_data, current_state)

        elif current_message_id == 'm-1' and current_step == 'waiting_language':
            return handle_language_selection(from_number, user_name, message_body, course_data, current_state, button_payload)

        elif current_message_id.startswith('m-') and current_step == 'waiting_quiz':
            # Intercept reminder button payloads
            if message_type == 'button' and button_payload and button_payload.lower() in ['continue learning', 'course_learning']:
                logger.info(f"User {user_id} clicked continue learning during quiz - repeating current quiz message")
                # Repeat the current quiz message (do not treat as answer)
                result = send_next_message_by_id(
                    from_number=from_number,
                    user_name=user_name,
                    message_id=current_message_id,  # repeat current quiz
                    course_data=course_data,
                    current_state={**current_state, 'user_id': user_id}
                )
                if result.get('success') and result.get('next_state'):
                    update_user_state(user_id, result['next_state'])
                return result

            # Normal quiz answer handling
            if message_type == 'button' and button_payload:
                processed_answer = button_payload
                if str(button_payload).isdigit():
                    ...
                return handle_quiz_answer(from_number, user_name, processed_answer, course_data, {**current_state, 'user_id': user_id})
            else:
                return handle_quiz_answer(from_number, user_name, message_body, course_data, {**current_state, 'user_id': user_id})

        elif current_message_id.startswith('m-') and current_step == 'waiting_button':
            return handle_button_response(from_number, user_name, message_body, course_data, current_state, button_payload)

        elif current_message_id.startswith('m-') and current_step in ['waiting_next']:
            return send_next_message(from_number, user_name, course_data, current_state)

        else:
            return handle_navigation(from_number, user_name, message_body, course_data, current_state)

    except Exception as e:
        logger.error(f"Error processing user message: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'success': False, 'error': str(e)}




def handle_video_rewatch_response(from_number, user_name, button_payload, course_data, current_state):
    """Handle video rewatch template button responses with ONE-TIME TOKEN validation"""
    try:
        current_message_id = current_state.get('message_id')
        user_id = current_state.get('user_id')
        message_index = int(current_message_id.replace('m-', '')) - 1
        message_data = course_data.get(message_index)

        logger.info(f"Handling video rewatch response for user {user_id}")
        logger.info(f"Current message ID: {current_message_id}")
        logger.info(f"Button payload: {button_payload}")

        # CRITICAL: Check if there's a valid one-time rewatch token for this user+message
        from .models import OneTimeReWatchToken
        
        active_token = OneTimeReWatchToken.objects.filter(
            user_id=user_id,
            message_id=current_message_id,
            is_used=False
        ).first()

        # ENHANCED VALIDATION: Check token validity
        if not active_token:
            logger.warning(f"User {user_id} clicked rewatch button but no active token found for {current_message_id}")
            # expired_msg = "⚠️ This video rewatch option has expired or been used.\n\nYou can no longer use this rewatch template. Please continue with your course."
            # whatsapp_service.send_message(from_number, expired_msg)
            return {'success': True, 'message': 'No active rewatch token', 'next_state': current_state}

        if active_token.is_expired():
            logger.warning(f"User {user_id} clicked rewatch button but token {active_token.token} has expired")
            # expired_msg = "⚠️ This video rewatch option has expired.\n\nThe time limit for rewatching has passed. Please continue with your course."
            # whatsapp_service.send_message(from_number, expired_msg)
            
            # Mark token as used since it's expired
            active_token.mark_as_used()
            return {'success': True, 'message': 'Rewatch token expired', 'next_state': current_state}

        # TOKEN IS VALID - Mark it as used IMMEDIATELY to prevent double-clicks
        active_token.mark_as_used()
        logger.info(f"Marked rewatch token {active_token.token} as used for user {user_id}")

        # CRITICAL: Check if this is an outdated template click (additional safety)
        if not message_data or message_data.get('type') != 'video':
            logger.warning(f"User {user_id} clicked rewatch button but current message {current_message_id} is not a video")
            ignore_msg = "This video option is no longer active. Please continue with your current lesson."
            whatsapp_service.send_message(from_number, ignore_msg)
            return {'success': True, 'message': 'Ignored outdated rewatch click', 'next_state': current_state}

        # Get stored video data
        try:
            video_meta = WpUsermeta.objects.filter(
                user_id=user_id,
                meta_key=f'current_video_{current_message_id}'
            ).first()

            if video_meta:
                video_info = json.loads(video_meta.meta_value)
                video_url = video_info.get('media_id', '')
                video_caption = video_info.get('video_caption', '')
                original_delay = video_info.get('delay_used', 8)
            else:
                # Fallback to message data
                video_url = message_data.get('media_id', '')
                video_caption = message_data.get('video_caption', '')
                original_delay = int(message_data.get('delay', 8))
                
            # FIXED: Ensure video_caption is never empty
            if not video_caption or video_caption.strip() == '':
                video_caption = message_data.get('lesson_name', 'Video Lesson')
            if not video_caption or video_caption.strip() == '':
                video_caption = 'Video Lesson'
                
            logger.info(f"Video caption for rewatch: '{video_caption}'")
            
        except Exception as e:
            logger.warning(f"Could not get stored video info: {e}")
            video_url = message_data.get('media_id', '')
            video_caption = message_data.get('video_caption') or message_data.get('lesson_name', 'Video Lesson')
            if not video_caption or video_caption.strip() == '':
                video_caption = 'Video Lesson'
            original_delay = int(message_data.get('delay', 8))

        # Handle different button responses
        response_lower = str(button_payload).lower().strip()

        if (button_payload == '1' or 'yes' in response_lower):
            # User wants to rewatch - TOKEN ALREADY MARKED AS USED
            logger.info(f"User {user_id} wants to rewatch video {current_message_id} - Token consumed")

            # Send rewatch message
            rewatch_msg = f"🔄 Rewatching: {video_caption}\n\nSending the video again..."
            whatsapp_service.send_message(from_number, rewatch_msg)

            # Send the video template again with NEW one-time system
            def send_video_template_again():
                try:
                    time.sleep(2)
                    video_template_sid = getattr(settings, 'WHATSAPP_VIDEO_LESSON_TEMPLATE_SID', None)
                    if video_template_sid:
                        rewatch_result = whatsapp_service.send_video_template_message(
                            to_number=from_number,
                            template_sid=video_template_sid,
                            video_url=video_url,
                            video_caption=video_caption,
                            user_name=user_name,
                            video_delay=original_delay
                        )
                        
                        logger.info(f"Rewatch video sent, scheduling NEW rewatch template after {original_delay}s delay")
                        time.sleep(original_delay)

                        # Send NEW one-time rewatch template
                        # rewatch_template_sid = getattr(settings, 'WHATSAPP_VIDEO_REWATCH_TEMPLATE_SID', None)
                        # if rewatch_template_sid and rewatch_template_sid.strip():
                        #     logger.info(f"Sending NEW one-time rewatch template with SID: {rewatch_template_sid}")
                        #     new_rewatch_result = whatsapp_service.send_video_rewatch_template_message(
                        #         to_number=from_number,
                        #         template_sid=rewatch_template_sid,
                        #         video_caption=video_caption,
                        #         user_name=user_name
                        #     )
                            
                        #     if new_rewatch_result.get('success'):
                        #         logger.info(f"NEW one-time rewatch template sent successfully")
                        #     else:
                        #         logger.error(f"Failed to send NEW rewatch template: {new_rewatch_result}")
                        # else:
                        #     logger.warning(f"No rewatch template SID found for NEW rewatch")
                except Exception as e:
                    logger.error(f"Error sending rewatch templates: {e}")

            # Start thread for delayed rewatch templates
            thread = threading.Thread(target=send_video_template_again)
            thread.daemon = True
            thread.start()

            return {
                'success': True,
                'message': 'Video sent for rewatch - token consumed',
                'next_state': current_state
            }

        elif (button_payload == '2' or 'continue' in response_lower):
            # User wants to continue - TOKEN ALREADY MARKED AS USED
            logger.info(f"User {user_id} wants to continue to next lesson - Token consumed")

            confirmation_msg = "Continuing to next lesson..."
            whatsapp_service.send_message(from_number, confirmation_msg)

            # Clean up ALL stored video info for this user
            try:
                WpUsermeta.objects.filter(
                    user_id=user_id,
                    meta_key__startswith='current_video_'
                ).delete()
                logger.info(f"Cleaned up ALL video info for user {user_id}")
            except Exception as e:
                logger.warning(f"Could not clean up video info: {e}")


            # Proceed to next message
            next_message_id = get_next_message_id(current_message_id)
            if next_message_id:
                logger.info(f"Proceeding to next message: {next_message_id}")
                
                result = send_next_message_by_id(
                    from_number=from_number,
                    user_name=user_name,
                    message_id=next_message_id,
                    course_data=course_data,
                    current_state=current_state
                )
                
                logger.info(f"Next message send result: {result}")
                return result
                
            else:
                # Course completed
                completion_msg = "🎉 Congratulations! You have completed the course successfully!"
                whatsapp_service.send_message(from_number, completion_msg)
                
                completed_state = {
                    **current_state,
                    'step': 'completed'
                }
                
                return {
                    'success': True,
                    'message': 'Course completed',
                    'next_state': completed_state
                }

        else:
            # Invalid response - TOKEN STILL CONSUMED to prevent abuse
            logger.warning(f"Invalid video rewatch response from user {user_id}: {button_payload} - Token still consumed")
            
            help_msg = "⚠️ Invalid response detected.\n\nThe rewatch option has been consumed. Please continue with your course."
            whatsapp_service.send_message(from_number, help_msg)
            return {
                'success': True,
                'message': 'Invalid response - token consumed',
                'next_state': current_state
            }

    except Exception as e:
        logger.error(f"Error handling video rewatch response: {str(e)}")
        return {'success': False, 'error': str(e)}

def deactivate_other_rewatch_templates(user_id, current_message_id):
    """Deactivate rewatch templates for other videos"""
    try:
        # Get all current_video_* entries for this user
        video_metas = WpUsermeta.objects.filter(
            user_id=user_id,
            meta_key__startswith='current_video_'
        ).exclude(meta_key=f'current_video_{current_message_id}')
        
        for meta in video_metas:
            try:
                video_info = json.loads(meta.meta_value)
                video_info['deactivated'] = True
                video_info['deactivated_at'] = time.time()
                meta.meta_value = json.dumps(video_info)
                meta.save()
                logger.info(f"Deactivated rewatch template for {meta.meta_key}")
            except Exception as e:
                logger.warning(f"Could not deactivate {meta.meta_key}: {e}")
                
    except Exception as e:
        logger.warning(f"Error deactivating other rewatch templates: {e}")

def deactivate_all_rewatch_templates(user_id):
    """Deactivate all rewatch templates for this user"""
    try:
        # Mark all current_video_* entries as deactivated
        video_metas = WpUsermeta.objects.filter(
            user_id=user_id,
            meta_key__startswith='current_video_'
        )
        
        for meta in video_metas:
            try:
                video_info = json.loads(meta.meta_value)
                video_info['deactivated'] = True
                video_info['deactivated_at'] = time.time()
                meta.meta_value = json.dumps(video_info)
                meta.save()
                logger.info(f"Deactivated rewatch template for {meta.meta_key}")
            except Exception as e:
                # If JSON parsing fails, just delete the meta
                meta.delete()
                logger.info(f"Deleted corrupted video meta: {meta.meta_key}")
                
    except Exception as e:
        logger.warning(f"Error deactivating all rewatch templates: {e}")





def get_course_data(course_id):
    """Get course message data"""
    try:
        # FIXED: Handle 'None' or invalid course_id
        if not course_id or course_id == 'None' or course_id == 'null':
            logger.warning(f"Invalid course_id '{course_id}', using default course")
            course_id = 10362  # Use default course ID
        
        # Convert to int to ensure it's valid
        try:
            course_id = int(course_id)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert course_id '{course_id}' to int, using default")
            course_id = 10362

        logger.info(f"Getting course data for course_id: {course_id}")

        # Get course message data from post meta
        message_meta = WpPostmeta.objects.get(
            post_id=course_id,
            meta_key='messageData'
        )

        # Parse the serialized data
        course_data = whatsapp_service.parse_serialized_data(
            message_meta.meta_value)
        print(course_data, "course_data")

        if course_data and len(course_data) > 0:
            logger.info(
                f"Course data loaded successfully for course {course_id}. Messages: {len(course_data)}")
            # The course_data is already in the correct format, just return it
            return course_data

        return None

    except WpPostmeta.DoesNotExist:
        logger.error(f"Course data not found for course_id: {course_id}")
        return None
    except Exception as e:
        logger.error(f"Error getting course data: {str(e)}")
        return None

# ADD THE NEW FUNCTION HERE:
def get_lesson_info_from_message_id(course_data, message_id):
    """Get lesson information from message ID"""
    try:
        message_index = int(message_id.replace('m-', '')) - 1
        if message_index < 0:
            message_index = 0
            
        if message_index < len(course_data):
            message_data = course_data.get(message_index, {})
            return {
                'lesson_name': message_data.get('lesson_name', f'Lesson {message_index + 1}'),
                'lesson_type': message_data.get('type', 'unknown'),
                'content': message_data.get('content', ''),
                'media_id': message_data.get('media_id', ''),
                'video_caption': message_data.get('video_caption', ''),
                'quiz_data': message_data.get('quiz', {}),
                'button_data': message_data.get('button', {}),
                'delay': message_data.get('delay', '1'),
                'video_length': message_data.get('video_length', '0'),
            }
        
        return {
            'lesson_name': f'Lesson {message_index + 1}',
            'lesson_type': 'unknown',
            'content': '',
            'media_id': '',
            'video_caption': '',
            'quiz_data': {},
            'button_data': {},
            'delay': '1',
            'video_length': '0',
        }
        
    except Exception as e:
        logger.error(f"Error getting lesson info: {e}")
        return {
            'lesson_name': 'Unknown Lesson',
            'lesson_type': 'unknown',
            'content': '',
            'media_id': '',
            'video_caption': '',
            'quiz_data': {},
            'button_data': {},
            'delay': '1',
            'video_length': '0',
        }

def get_default_course_id(user_id):
    """Get default course ID for user"""
    try:
        # Get first available course for the user
        course = WpPosts.objects.filter(
            post_type='sfwd-courses',
            post_status='publish'
        ).first()

        return course.id if course else None

    except Exception as e:
        logger.error(f"Error getting default course: {str(e)}")
        return None




def send_language_selection_message(from_number, user_name, course_data, current_state):
    """Send language selection message"""
    try:
        logger.info(f"Sending language selection to {from_number}")
        logger.info(f"Course data type: {type(course_data)}")

        # Get the first message (m-1) from course data - index 0
        first_message = course_data.get(
            0) if isinstance(course_data, dict) else None

        if first_message and isinstance(first_message, dict) and first_message.get('type') == 'button':
            logger.info("Using course data for language selection")
            # Use the course data button message
            result = whatsapp_service.send_dynamic_message_with_course(
                from_number,
                first_message,
                user_name,
                "POSH"
            )

            logger.info(
                f"Language selection message sent via course data: {result}")

            return {
                'success': result.get('success', False),
                'next_state': {
                    **current_state,
                    'step': 'waiting_language'
                }
            }
        else:
            logger.info("Using fallback language selection message")
            # Fallback to manual message
            message = f""" Hello {user_name}!

Welcome to the POSH (Prevention of Sexual Harassment) course.

Please select your preferred language:

🇺🇸 0. English
🇮🇳 1. Hindi

 Reply with 0 or 1, or type the language name."""

            result = whatsapp_service.send_message(from_number, message)
            logger.info(f"Fallback language selection sent: {result}")

            return {
                'success': result.get('success', False),
                'next_state': {
                    **current_state,
                    'step': 'waiting_language'
                }
            }

    except Exception as e:
        logger.error(f"Error sending language selection: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'success': False, 'error': str(e)}


def handle_language_selection(from_number, user_name, message_body, course_data, current_state, button_payload=''):
    """Handle language selection response"""
    try:
        # Use button payload if available, otherwise use message body
        user_choice = button_payload if button_payload else message_body
        user_choice = str(user_choice).lower().strip()

        logger.info(
            f"Language selection - user_choice: '{user_choice}', button_payload: '{button_payload}', message_body: '{message_body}'")

        # Map user input to language
        selected_language = None

        if user_choice in ['0', 'english']:
            selected_language = 'en'
        elif user_choice in ['1', 'hindi']:
            selected_language = 'hi'
        elif 'english' in user_choice:
            selected_language = 'en'
        elif 'hindi' in user_choice:
            selected_language = 'hi'

        logger.info(f"Selected language: {selected_language}")

        if not selected_language:
            # Invalid selection, ask again
            error_msg = """ Invalid selection. Please choose:

🇺🇸 0. English  
🇮🇳 1. Hindi

Reply with 0 or 1, or type the language name."""

            result = whatsapp_service.send_message(from_number, error_msg)
            logger.info(f"Sent error message: {result}")

            return {
                'success': True,
                'next_state': current_state  # Stay in same state
            }

        # CRITICAL FIX: Get user_id from the database lookup
        try:
            clean_phone = from_number.replace('+', '').replace(' ', '')
            user_meta = WpUsermeta.objects.filter(
                meta_key='waid',
                meta_value__icontains=clean_phone
            ).first()

            if user_meta:
                user_id = user_meta.user_id
                logger.info(f"Found user_id from database: {user_id}")
            else:
                logger.error("Could not find user_id from phone number")
                return {'success': False, 'error': 'User not found'}
        except Exception as e:
            logger.error(f"Error finding user_id: {str(e)}")
            return {'success': False, 'error': 'User lookup failed'}

        # Save language preference
        try:
            if user_id:
                WpUsermeta.objects.update_or_create(
                    user_id=user_id,
                    meta_key='preferred_language',
                    defaults={'meta_value': selected_language}
                )
                logger.info(
                    f"Saved language preference for user {user_id}: {selected_language}")
        except Exception as e:
            logger.warning(f"Could not save language preference: {e}")

        # Now send m-2 (first lesson)
        logger.info("Proceeding to send m-2 message")

        # Get course_id for current state
        course_id = current_state.get(
            'course_id') or get_default_course_id(user_id)

        # CRITICAL FIX: Pass user_id in the current_state
        next_result = send_next_message_by_id(
            from_number=from_number,
            user_name=user_name,
            message_id='m-2',
            course_data=course_data,
            current_state={
                **current_state,
                'course_id': course_id,
                'user_id': user_id  # This is the critical fix
            },
            language=selected_language
        )

        logger.info(f"Next message (m-2) result: {next_result}")

        return next_result

    except Exception as e:
        logger.error(f"Error handling language selection: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'success': False, 'error': str(e)}
    




def send_next_message_by_id(from_number, user_name, message_id, course_data, current_state, language=None):
    """Send specific message by ID with comprehensive tracking"""
    try:
        logger.info(f"=== SENDING MESSAGE {message_id} ===")
        
        # Get user_id from current_state
        user_id = current_state.get('user_id')
        course_id = current_state.get('course_id')
        
        # TRACK LESSON START
        if user_id and course_id:
            lesson_id = f"lesson_{message_id}"
            course_tracker.track_lesson_start(user_id, course_id, lesson_id, message_id)
        
        
        # Check if course_data is valid
        if not isinstance(course_data, dict):
            logger.error(f"Course data is not a dictionary: {type(course_data)}")
            return send_error_message(from_number, "Course data is corrupted. Please contact support.")

        # Get message index from ID
        message_index = int(message_id.replace('m-', '')) - 1
        
        # CHECK FOR COURSE COMPLETION
        if message_index >= len(course_data):
            logger.info(f"Course completed - requested message index {message_index} >= course length {len(course_data)}")
            
            # TRACK COURSE COMPLETION
            if user_id and course_id:
                course_tracker.track_course_completion(user_id, course_id, 'full')
            
            # Send completion message
            completion_message = """🎉 **Congratulations!** 🎉

You have successfully completed the course!

**Course Summary:**
• All lessons completed
• All quizzes answered
• Learning objectives achieved

Thank you for learning with ILead! 

---
*Keep learning, keep growing!* 💪"""

            result = whatsapp_service.send_message(from_number, completion_message)
            
            completed_state = {
                **current_state,
                'step': 'completed',
                'message_id': message_id,
                'user_id': user_id
            }

            if user_id:
                update_user_state(user_id, completed_state)
                # TRACK FINAL PROGRESS
                course_tracker.track_course_progress(user_id, course_id, message_id, 'completed', 100)

            return {
                'success': True,
                'message': 'Course completed successfully',
                'next_state': completed_state
            }

        # Get message data
        message_data = course_data.get(message_index)
        
        if message_data is None:
            logger.error(f"Message at index {message_index} not found in course data")
            return send_error_message(from_number, "Course content error. Please contact support.")

        # Validate message structure
        if not isinstance(message_data, dict) or 'type' not in message_data:
            logger.error(f"Invalid message data structure")
            return send_error_message(from_number, "Invalid message structure. Please contact support.")

        message_type = message_data.get('type', 'text')
        logger.info(f"Processing message type: {message_type}")

        # Send the message using appropriate method
        if message_type in ['video', 'button', 'quiz', 'text']:
            result = whatsapp_service.send_dynamic_message_with_template(
                to_number=from_number,
                message_data=message_data,
                user_name=user_name,
                course_name="Corporate Etiquette"
            )
        else:
            result = whatsapp_service.send_dynamic_message_with_course(
                to_number=from_number,
                message_data=message_data,
                user_name=user_name,
                course_name="Corporate Etiquette"
            )

        # Determine next step based on message type
        if message_type == 'quiz':
            next_step = 'waiting_quiz'
        elif message_type == 'button':
            next_step = 'waiting_button'
        elif message_type == 'video':
            next_step = 'waiting_video_watched'
        else:
            next_step = 'waiting_next'

        # Update user state
        new_state = {
            'course_id': current_state.get('course_id'),
            'message_id': message_id,
            'step': next_step,
            'language': language or current_state.get('language'),
            'user_id': user_id
        }

        # TRACK PROGRESS UPDATE
        if user_id and course_id:
            completion_percentage = ((message_index + 1) / len(course_data)) * 100
            course_tracker.track_course_progress(user_id, course_id, message_id, next_step, completion_percentage)

        # Special handling for video messages
        if message_type == 'video' and result.get('success'):
            video_url = message_data.get('media_id', '')
            # FIXED: Ensure video_caption is always populated
            video_caption = message_data.get('video_caption') or message_data.get('lesson_name', 'Video Lesson')
            if not video_caption or video_caption.strip() == '':
                video_caption = 'Video Lesson'
                
            # Get dynamic delay
            video_delay = None
            try:
                delay = message_data.get('delay', '8')
                video_delay = int(delay)
                logger.info(f"Video delay extracted: {video_delay} seconds")
            except:
                try:
                    video_length = message_data.get('video_length', '300')
                    video_delay = int(video_length)
                    logger.info(f"Using video_length as delay: {video_delay} seconds")
                except:
                    video_delay = 8  # Default delay
                    logger.warning(f"Could not parse delay, using default: {video_delay} seconds")
            
            logger.info(f"Video sent successfully. Caption: '{video_caption}', Will send rewatch template after {video_delay} seconds")
            
            # def send_rewatch_template_after_delay():
            #     try:
            #         logger.info(f"Starting {video_delay}s delay for rewatch template...")
            #         time.sleep(video_delay)
                    
            #         logger.info(f"Delay completed! Sending rewatch template with caption: '{video_caption}'")
                    
            #         rewatch_template_sid = getattr(settings, 'WHATSAPP_VIDEO_REWATCH_TEMPLATE_SID', None)
                    
            #         if rewatch_template_sid and rewatch_template_sid.strip():
            #             logger.info(f"Sending rewatch template with SID: {rewatch_template_sid}")
                        
            #             rewatch_result = whatsapp_service.send_video_rewatch_template_message(
            #                 to_number=from_number,
            #                 template_sid=rewatch_template_sid,
            #                 video_caption=video_caption,  # Pass the proper caption
            #                 user_name=user_name
            #             )
                        
            #             logger.info(f"Rewatch template result: {rewatch_result}")
                        
            #             if rewatch_result.get('success') and user_id:
            #                 # Store video info for potential rewatch
            #                 WpUsermeta.objects.update_or_create(
            #                     user_id=user_id,
            #                     meta_key=f'current_video_{message_id}',
            #                     defaults={
            #                         'meta_value': json.dumps({
            #                             'video_url': video_url,
            #                             'media_id': video_url,
            #                             'video_caption': video_caption,
            #                             'message_id': message_id,
            #                             'delay_used': video_delay
            #                         })
            #                     }
            #                 )
            #                 logger.info(f"Rewatch template sent successfully after {video_delay}s delay")
            #             else:
            #                 logger.error(f"Failed to send rewatch template: {rewatch_result}")
            #         else:
            #             logger.error(f"No rewatch template SID configured. Current value: '{rewatch_template_sid}'")
                        
            #     except Exception as e:
            #         logger.error(f"Error sending rewatch template: {str(e)}")
            #         logger.error(f"Traceback: {traceback.format_exc()}")

            # # Start thread for delayed rewatch template
            # thread = threading.Thread(target=send_rewatch_template_after_delay)
            # thread.daemon = True
            # thread.start()
            # logger.info(f"Started background thread for rewatch template (delay: {video_delay}s)")


        # For text/pdf messages, schedule next message
        elif message_type in ['text', 'pdf']:
            delay_seconds = int(message_data.get('delay', 1))
            
            def send_delayed_message():
                try:
                    time.sleep(delay_seconds)
                    
                    # TRACK LESSON COMPLETION
                    if user_id and course_id:
                        lesson_id = f"lesson_{message_id}"
                        course_tracker.track_lesson_completion(user_id, course_id, lesson_id, message_id, delay_seconds)
                    
                    next_index = message_index + 1
                    
                    if next_index >= len(course_data):
                        # Course completed in auto-send
                        if user_id and course_id:
                            course_tracker.track_course_completion(user_id, course_id, 'full')
                        
                        completion_message = """🎉 **Congratulations!** 🎉

You have successfully completed the course!

Thank you for learning with Embyte! 🚀"""

                        whatsapp_service.send_message(from_number, completion_message)
                        
                        completed_state = {**new_state, 'step': 'completed'}
                        update_user_state(user_id, completed_state)
                        return

                    next_message_id = f'm-{next_index + 1}'
                    
                    auto_result = send_next_message_by_id(
                        from_number=from_number,
                        user_name=user_name,
                        message_id=next_message_id,
                        course_data=course_data,
                        current_state=new_state,
                        language=language
                    )

                    if auto_result.get('success') and auto_result.get('next_state'):
                        auto_next_state = auto_result['next_state']
                        if not auto_next_state.get('user_id'):
                            auto_next_state['user_id'] = user_id
                        update_user_state(user_id, auto_next_state)

                except Exception as e:
                    logger.error(f"Error in delayed message sending: {str(e)}")

            thread = threading.Thread(target=send_delayed_message)
            thread.daemon = True
            thread.start()

        return {
            'success': result.get('success', False),
            'next_state': new_state
        }

    except Exception as e:
        logger.error(f"Error sending message {message_id}: {str(e)}")
        return {'success': False, 'error': str(e)}



def send_next_message(from_number, user_name, course_data, current_state):
    """Send the next message in the course sequence"""
    try:
        # Get the current message ID and increment it
        current_message_id = current_state.get('message_id', 'm-1')
        current_index = int(current_message_id.replace('m-', '')) - 1
        next_index = current_index + 1
        next_message_id = f'm-{next_index + 1}'

        logger.info(
            f"Sending next message: {current_message_id} -> {next_message_id}")

        # Check if next message exists
        if next_index >= len(course_data):
            logger.info("Course completed - no more messages")
            return {
                'success': True,
                'message': 'Course completed',
                'next_state': {
                    **current_state,
                    'step': 'completed'
                }
            }

        # Send the next message
        return send_next_message_by_id(
            from_number=from_number,
            user_name=user_name,
            message_id=next_message_id,
            course_data=course_data,
            current_state=current_state,
            language=current_state.get('language')
        )

    except Exception as e:
        logger.error(f"Error in send_next_message: {str(e)}")
        return {'success': False, 'error': str(e)}


def send_error_message(from_number, error_message):
    """Send error message to user"""
    try:
        result = whatsapp_service.send_message(from_number, error_message)
        return {'success': True, 'error': error_message}
    except Exception as e:
        logger.error(f"Failed to send error message: {str(e)}")
        return {'success': False, 'error': str(e)}


def handle_quiz_answer(from_number, user_name, message_body, course_data, current_state):
    """Handle quiz answer with comprehensive tracking and context validation"""
    try:
        current_message_id = current_state.get('message_id')
        user_id = current_state.get('user_id')
        course_id = current_state.get('course_id')
        message_index = int(current_message_id.replace('m-', '')) - 1
        message_data = course_data.get(message_index)

        # CRITICAL: Verify this is actually a quiz message
        if not message_data or message_data.get('type') != 'quiz':
            logger.error(f"handle_quiz_answer called but message {current_message_id} is not a quiz type: {message_data.get('type') if message_data else 'No data'}")
            return send_error_message(from_number, "This is not a quiz question.")

        quiz_data = message_data.get('quiz', {})
        first_quiz = quiz_data.get(0) if quiz_data else None

        if not first_quiz:
            return send_error_message(from_number, "Quiz question not available.")

        correct_answer = first_quiz.get('answer', '')
        options = first_quiz.get('options', {})
        question = first_quiz.get('question', '')
        
        logger.info(f"QUIZ CONTEXT - Question: {question}")
        logger.info(f"QUIZ CONTEXT - Options: {options}")
        logger.info(f"QUIZ CONTEXT - Correct Answer: {correct_answer}")
        logger.info(f"QUIZ CONTEXT - User Answer: {message_body}")


        
        # --- FIX START: ISOLATED ATTEMPT COUNTING ---

        # 1. Determine max attempts for THIS specific quiz
        number_pass_quiz = message_data.get('number_pass_quiz', '')
        max_attempts = 2  # Default value
        
        logger.info(f"QUIZ: Checking max attempts for quiz {current_message_id}.")
        if number_pass_quiz and str(number_pass_quiz).strip():
            try:
                parsed_attempts = int(str(number_pass_quiz).strip())
                if parsed_attempts > 0:
                    max_attempts = parsed_attempts
                    logger.info(f"QUIZ: Custom max attempts set from course data: {max_attempts}")
                else:
                    logger.warning(f"QUIZ: Invalid number_pass_quiz value '{parsed_attempts}', using default {max_attempts}.")
                    max_attempts = 2
            except (ValueError, TypeError):
                logger.warning(f"QUIZ: Could not parse number_pass_quiz '{number_pass_quiz}', using default {max_attempts}.")
                max_attempts = 2
        else:
            logger.info(f"QUIZ: No custom max attempts set, using default {max_attempts}.")

        # 2. Get current attempt count for THIS quiz using a unique key
        attempt_key = f"quiz_attempts_{user_id}_{course_id}_{current_message_id}"
        current_attempts = 0
        try:
            attempt_meta = WpUsermeta.objects.filter(
                user_id=user_id,
                meta_key=attempt_key
            ).first()

            if attempt_meta:
                attempt_data = json.loads(attempt_meta.meta_value)
                current_attempts = attempt_data.get('attempt_count', 0)
                logger.info(f"QUIZ: Found previous attempt data for {attempt_key}. Current attempts: {current_attempts}")
            else:
                logger.info(f"QUIZ: No previous attempt data found for {attempt_key}. This is the first try.")
        except Exception as e:
            logger.error(f"QUIZ: Error reading attempt data for {attempt_key}: {e}. Resetting attempts to 0.")
        
        current_attempts += 1
        logger.info(f"QUIZ: This is attempt number {current_attempts} of {max_attempts} for quiz {current_message_id}.")



        # ENHANCED: Process user's answer with quiz-specific logic
        user_answer = str(message_body).strip()
        user_answer_text = ""

        # First, try direct text matching (for Yes/No answers)
        user_answer_lower = user_answer.lower()
        
        # Check if user gave a direct text answer that matches options
        option_values_lower = {str(v).lower().strip(): str(v) for v in options.values()}
        
        if user_answer_lower in option_values_lower:
            user_answer_text = option_values_lower[user_answer_lower]
            logger.info(f"QUIZ: Direct text match - '{user_answer}' -> '{user_answer_text}'")
        
        # If not found, try numeric index mapping
        # Prioritize this mapping.
        if user_answer.isdigit():
            option_index = int(user_answer)
            if option_index in options:
                user_answer_text = options[option_index]
                logger.info(f"QUIZ: Mapped numeric answer '{user_answer}' to option '{user_answer_text}'")
            else:
                # Fallback for text-based answers that happen to be numbers
                user_answer_text = user_answer
                logger.warning(f"QUIZ: Numeric answer '{user_answer}' not a valid option index, using as-is.")
        else:
            # Handle text-based answers (e.g., user types "Yes")
            user_answer_lower = user_answer.lower()
            option_values_lower = {str(v).lower().strip(): str(v) for v in options.values()}
            
            if user_answer_lower in option_values_lower:
                user_answer_text = option_values_lower[user_answer_lower]
                logger.info(f"QUIZ: Direct text match - '{user_answer}' -> '{user_answer_text}'")
            else:
                # Fallback: use the answer as-is
                user_answer_text = user_answer
                logger.info(f"QUIZ: No direct match, using answer as-is - '{user_answer_text}'")

        # Check if answer is correct (case-insensitive comparison)
        is_correct = user_answer_text.lower().strip() == correct_answer.lower().strip()
        
        logger.info(f"QUIZ RESULT: '{user_answer_text}' vs '{correct_answer}' = {is_correct}")

        # TRACK QUIZ ATTEMPT
        if user_id and course_id:
            quiz_id = f"quiz_{current_message_id}"
            course_tracker.track_quiz_attempt(
                user_id, course_id, quiz_id, current_message_id,
                question, user_answer_text, correct_answer, is_correct,
                current_attempts, max_attempts
            )

        # Save attempt data
        try:
            if user_id:
                attempt_data = {
                    'attempt_count': current_attempts,
                    'max_attempts': max_attempts,
                    'last_attempt': {
                        'answer': user_answer_text,
                        'is_correct': is_correct,
                        'timestamp': int(time.time())
                    }
                }
                
                WpUsermeta.objects.update_or_create(
                    user_id=user_id,
                    meta_key=attempt_key,
                    defaults={'meta_value': json.dumps(attempt_data)}
                )
        except Exception as e:
            logger.warning(f"Could not save attempt data: {e}")

        # Handle correct answer
        if is_correct:
            # FIXED: Don't show correct answer when user got it right
            success_msg = f"🎉 **Excellent! Correct Answer!** 🎉\n\n**Your Answer:** {user_answer_text}\n\n**Well done!** You got it right on attempt {current_attempts}/{max_attempts}.\n\nMoving to the next lesson..."
            whatsapp_service.send_message(from_number, success_msg)

            # Clean up attempt data - IMPORTANT: This prevents reattempts
            try:
                WpUsermeta.objects.filter(
                    user_id=user_id,
                    meta_key=attempt_key
                ).delete()
                logger.info(f"Cleaned up quiz attempt data for user {user_id}, quiz {current_message_id}")
            except Exception as e:
                logger.warning(f"Could not clean up attempt data: {e}")

            # FIXED: Mark quiz as completed to prevent re-attempts
            try:
                if user_id:
                    WpUsermeta.objects.update_or_create(
                        user_id=user_id,
                        meta_key=f'quiz_completed_{current_message_id}',
                        defaults={'meta_value': json.dumps({
                            'is_correct': True,
                            'attempts_used': current_attempts,
                            'completed_at': int(time.time()),
                            'final_answer': user_answer_text
                        })}
                    )
                    logger.info(f"Marked quiz {current_message_id} as completed for user {user_id}")
            except Exception as e:
                logger.warning(f"Could not mark quiz as completed: {e}")

            # FIXED: Update user state to 'waiting_next' to prevent quiz re-attempts
            next_state = {
                **current_state,
                'step': 'waiting_next'
            }
            
            if user_id:
                update_user_state(user_id, next_state)

            # Proceed to next message after a delay
            def send_next_after_success():
                time.sleep(2)
                next_message_id = get_next_message_id(current_message_id)
                if next_message_id:
                    result = send_next_message_by_id(
                        from_number=from_number,
                        user_name=user_name,
                        message_id=next_message_id,
                        course_data=course_data,
                        current_state=next_state
                    )
                    
                    # Update state with result
                    if result.get('success') and result.get('next_state') and user_id:
                        update_user_state(user_id, result['next_state'])

            thread = threading.Thread(target=send_next_after_success)
            thread.daemon = True
            thread.start()

            return {
                'success': True,
                'message': f'Quiz answered correctly on attempt {current_attempts}',
                'next_state': next_state,
                'quiz_completed': True
            }

        # Handle incorrect answer (rest of the function remains the same)
        else:
            if current_attempts < max_attempts:
                remaining_attempts = max_attempts - current_attempts
                # FIXED: Don't show correct answer during reattempts
                retry_msg = f" **Incorrect Answer**\n\n**Your Answer:** {user_answer_text}\n\n**Attempts Remaining:** {remaining_attempts}\n\n🔄 Please try again with a different option!"
                
                whatsapp_service.send_message(from_number, retry_msg)
                
                def resend_quiz():
                    time.sleep(3)
                    # Resend the same quiz template for reattempt
                    result = whatsapp_service.send_dynamic_message_with_template(
                        to_number=from_number,
                        message_data=message_data,
                        user_name=user_name,
                        course_name="Corporate Etiquette"
                    )
                    logger.info(f"Resent quiz for reattempt {current_attempts + 1}/{max_attempts}")
                
                thread = threading.Thread(target=resend_quiz)
                thread.daemon = True
                thread.start()
                
                return {
                    'success': True,
                    'message': f'Quiz answered incorrectly, {remaining_attempts} attempts remaining',
                    'next_state': current_state  # Stay in waiting_quiz state
                }
            
            else:
                # No more attempts - ONLY NOW show the correct answer
                final_msg = f" **Quiz Failed**\n\n**Your Final Answer:** {user_answer_text}\n**Correct Answer:** {correct_answer}\n\n**Attempts Used:** {current_attempts}/{max_attempts}\n\n⏭️ Don't worry! Moving to the next lesson..."
                
                whatsapp_service.send_message(from_number, final_msg)
                
                # Clean up attempt data and mark as completed
                try:
                    WpUsermeta.objects.filter(
                        user_id=user_id,
                        meta_key=attempt_key
                    ).delete()
                    
                    # Mark quiz as failed but completed
                    WpUsermeta.objects.update_or_create(
                        user_id=user_id,
                        meta_key=f'quiz_completed_{current_message_id}',
                        defaults={'meta_value': json.dumps({
                            'is_correct': False,
                            'attempts_used': current_attempts,
                            'completed_at': int(time.time()),
                            'final_answer': user_answer_text,
                            'correct_answer': correct_answer
                        })}
                    )
                except Exception as e:
                    logger.warning(f"Could not mark failed quiz as completed: {e}")

                # Update state to waiting_next
                next_state = {
                    **current_state,
                    'step': 'waiting_next'
                }
                
                if user_id:
                    update_user_state(user_id, next_state)

                # Proceed to next message
                def send_next_after_failure():
                    time.sleep(3)
                    next_message_id = get_next_message_id(current_message_id)
                    if next_message_id:
                        result = send_next_message_by_id(
                            from_number=from_number,
                            user_name=user_name,
                            message_id=next_message_id,
                            course_data=course_data,
                            current_state=next_state
                        )
                        
                        # Update state with result
                        if result.get('success') and result.get('next_state') and user_id:
                            update_user_state(user_id, result['next_state'])

                thread = threading.Thread(target=send_next_after_failure)
                thread.daemon = True
                thread.start()

                return {
                    'success': True,
                    'message': f'Quiz failed after {current_attempts} attempts, proceeding to next lesson',
                    'next_state': next_state,
                    'quiz_completed': True
                }

    except Exception as e:
        logger.error(f"Error handling quiz answer: {str(e)}")
        return {'success': False, 'error': str(e)}




    
# Update the handle_button_response function definition (around line 1075)
def handle_button_response(from_number, user_name, message_body, course_data, current_state, button_payload=''):
    """Handle button response"""
    try:
        current_message_id = current_state.get('message_id')

        # Use button_payload if available, otherwise use message_body
        user_response = button_payload if button_payload else message_body

        logger.info(
            f"Handling button response: payload='{button_payload}', body='{message_body}', using='{user_response}'")

        # For assessment buttons, just proceed to next
        if 'assessment' in user_response.lower() or 'start' in user_response.lower() or user_response.strip() == '0':
            next_message_id = get_next_message_id(current_message_id)
            return send_next_message_by_id(from_number, user_name, next_message_id, course_data, current_state)

        # For retake course button
        elif 'retake' in user_response.lower():
            # Restart from m-2 (skip language selection)
            return send_next_message_by_id(from_number, user_name, 'm-2', course_data, current_state)

        # For continue button (like in video rewatch)
        elif 'continue' in user_response.lower() or user_response.strip() == '2':
            # Proceed to next message
            next_message_id = get_next_message_id(current_message_id)
            return send_next_message_by_id(from_number, user_name, next_message_id, course_data, current_state)

        else:
            # Default: proceed to next message
            next_message_id = get_next_message_id(current_message_id)
            return send_next_message_by_id(from_number, user_name, next_message_id, course_data, current_state)

    except Exception as e:
        logger.error(f"Error handling button response: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'success': False, 'error': str(e)}


def handle_navigation(from_number, user_name, message_body, course_data, current_state):
    """Handle general navigation commands"""
    try:
        command = message_body.lower().strip()
        current_message_id = current_state.get('message_id')
        step = current_state.get('step')

        # Handle video template button responses
        if step == 'waiting_video_watched':
            if command in ['watched', 'done', 'completed', 'next', 'continue'] or 'view video' in command.lower():
                # User has watched the video, proceed to next message
                next_message_id = get_next_message_id(current_message_id)
                if next_message_id:
                    return send_next_message_by_id(from_number, user_name, next_message_id, course_data, current_state)
                else:
                    # Course completed
                    completion_msg = " Congratulations! You have completed the course successfully! "
                    whatsapp_service.send_message(from_number, completion_msg)
                    return {'success': True, 'next_state': {**current_state, 'step': 'completed'}}

        # Handle other navigation commands
        if command in ['next', 'continue', 'watched', 'done', 'ok']:
            # Move to next message
            next_message_id = get_next_message_id(current_message_id)
            if next_message_id:
                return send_next_message_by_id(from_number, user_name, next_message_id, course_data, current_state)
            else:
                # Course completed
                completion_msg = " Congratulations! You have completed the course successfully! "
                whatsapp_service.send_message(from_number, completion_msg)
                return {'success': True, 'next_state': {**current_state, 'step': 'completed'}}

        elif command in ['back', 'previous']:
            # Move to previous message
            prev_message_id = get_previous_message_id(current_message_id)
            if prev_message_id:
                return send_next_message_by_id(from_number, user_name, prev_message_id, course_data, current_state)
            else:
                help_msg = "You're at the beginning of the course. Type 'next' to continue."
                whatsapp_service.send_message(from_number, help_msg)
                return {'success': True, 'next_state': current_state}

        elif command in ['help', 'menu']:
            help_msg = """
 **Course Navigation Help**

Commands you can use:
• **next** - Go to next lesson
• **watched** - After watching a video
• **back** - Go to previous lesson  
• **help** - Show this help menu
• **status** - Show current progress

For quizzes: Reply with option number (1, 2, 3, etc.)
For videos: Click the "View Video" button, then reply **'watched'** when done
            """
            whatsapp_service.send_message(from_number, help_msg)
            return {'success': True, 'next_state': current_state}

        else:
            # Auto-advance for any other message
            next_message_id = get_next_message_id(current_message_id)
            if next_message_id:
                return send_next_message_by_id(from_number, user_name, next_message_id, course_data, current_state)
            else:
                return {'success': True, 'next_state': current_state}

    except Exception as e:
        logger.error(f"Error handling navigation: {str(e)}")
        return {'success': False, 'error': str(e)}


def get_next_message_id(current_message_id):
    """Get next message ID"""
    try:
        current_num = int(current_message_id.replace('m-', ''))
        return f'm-{current_num + 1}'
    except:
        return None


def get_previous_message_id(current_message_id):
    """Get previous message ID"""
    try:
        current_num = int(current_message_id.replace('m-', ''))
        if current_num > 1:
            return f'm-{current_num - 1}'
        return None
    except:
        return None


def send_error_message(from_number, error_text):
    """Send error message to user"""
    try:
        result = whatsapp_service.send_message(from_number, f" {error_text}")
        return {'success': result.get('success', False), 'error': error_text}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def send_invalid_option_message(from_number, options):
    """Send invalid option message"""
    try:
        msg = " **Invalid option selected**\n\nPlease choose from the available options:\n\n"

        for i, option in options.items():
            msg += f"**{int(i) + 1}.** {option}\n"

        msg += "\n **Tip:** Click one of the buttons or reply with the option number (1, 2, etc.)"

        result = whatsapp_service.send_message(from_number, msg)
        return {'success': result.get('success', False)}
    except Exception as e:
        logger.error(f"Error sending invalid option message: {e}")
        return {'success': False, 'error': str(e)}


# Add these imports at the top

# Add these new views to your existing views.py file


@api_view(['GET'])
@permission_classes([AllowAny])
def secure_video_view(request):
    """Serve the secure video viewing page"""
    token = request.GET.get('token')

    if not token:
        return render(request, 'error.html', {'error': 'Invalid access token'})

    return render(request, 'secure_video.html', {'token': token})


from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def vdocipher_drm_player(request):
    """
    Serve the VdoCipher DRM video player page.
    Users can enter OTP and playbackInfo to play the video.
    """
    return render(request, 'VdoCipher_DRM.html')


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_video_access(request):
    """Validate video access token"""
    try:
        data = json.loads(request.body)
        token = data.get('token')
        user_agent = data.get('user_agent')

        result = secure_video_service.validate_video_access(
            token=token,
            user_agent=user_agent
        )

        return Response(result)

    except Exception as e:
        logger.error(f"Error validating video access: {str(e)}")
        return Response({'valid': False, 'error': 'Validation failed'})
    

@api_view(['GET'])
@permission_classes([AllowAny])
def debug_video_cache(request):
    """Debug endpoint to check video cache status"""
    try:
        token = request.GET.get('token')
        if not token:
            return Response({'error': 'Token required'})
        
        # Decode token
        payload = jwt.decode(token, settings.VIDEO_SECURITY_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        lesson_id = payload.get('lesson_id')
        session_token = payload.get('session_token')
        
        # Check cache
        cache_key = f"video_session_{user_id}_{lesson_id}_{session_token}"
        session_info = cache.get(cache_key)
        
        return Response({
            'cache_key': cache_key,
            'session_exists': session_info is not None,
            'session_info': session_info,
            'payload': payload,
            'current_time': time.time()
        })
        
    except Exception as e:
        return Response({'error': str(e), 'traceback': traceback.format_exc()})


@api_view(['POST'])
@permission_classes([AllowAny])
def mark_video_viewed(request):
    """Mark video as viewed"""
    try:
        data = json.loads(request.body)
        token = data.get('token')

        result = secure_video_service.mark_video_viewed(token)

        return Response({'success': result})

    except Exception as e:
        logger.error(f"Error marking video as viewed: {str(e)}")
        return Response({'success': False, 'error': 'Failed to mark as viewed'})


# Add this new view to your existing views.py file

@api_view(['POST'])
@permission_classes([AllowAny])
def log_security_incident(request):
    """Log security incidents like screen recording attempts"""
    try:
        data = json.loads(request.body)
        token = data.get('token')
        incident_type = data.get('incident_type')
        detection_method = data.get('detection_method')
        user_agent = data.get('user_agent')
        timestamp = data.get('timestamp')

        # Validate token first
        result = secure_video_service.validate_video_access(token=token)

        if result.get('valid'):
            user_id = result.get('user_id')
            lesson_id = result.get('lesson_id')

            # Log the incident to database
            try:
                WpUsermeta.objects.create(
                    user_id=user_id,
                    meta_key=f'security_incident_{int(time.time())}',
                    meta_value=json.dumps({
                        'incident_type': incident_type,
                        'detection_method': detection_method,
                        'lesson_id': lesson_id,
                        'user_agent': user_agent,
                        'timestamp': timestamp,
                        # Partial token for reference
                        'token_used': token[:20] + '...'
                    })
                )

                logger.warning(
                    f"SECURITY INCIDENT: User {user_id} - {incident_type} - {detection_method}")

                # Optionally send alert to admins
                # send_security_alert_email(user_id, incident_type, detection_method)

            except Exception as e:
                logger.error(f"Failed to log security incident: {e}")

            return Response({'success': True, 'logged': True})
        else:
            return Response({'success': False, 'error': 'Invalid token'})

    except Exception as e:
        logger.error(f"Error logging security incident: {str(e)}")
        return Response({'success': False, 'error': 'Logging failed'})




import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Q

from .services.course_data_service import CourseDataService

@api_view(['GET'])
@permission_classes([AllowAny])  # Or use IsAuthenticated if needed
def get_user_progress_report(request, user_id=None):
    """Get detailed course progress report in tabular format with all lessons"""
    try:
        # Get user ID - either from URL or current authenticated user
        if not user_id:
            if request.user.is_authenticated:
                user_id = request.user.id
            else:
                return Response({"error": "User ID required"}, status=401)
        
        # Get user details
        try:
            user = WpUsers.objects.get(id=user_id)
            
            # Get user metadata
            user_meta = WpUsermeta.objects.filter(user_id=user_id)
            
            # Get basic profile info
            user_info = {
                "name": user.display_name,
                "email": user.user_email,
                "user_registered": user.user_registered,
                "department": "",
                "employee_id": "",
                "phone_number": "",
                "region": ""
            }
            
            # Get additional metadata fields
            for meta in user_meta:
                if meta.meta_key == 'waid':
                    user_info["phone_number"] = meta.meta_value
                elif meta.meta_key == 'department':
                    user_info["department"] = meta.meta_value
                elif meta.meta_key == 'employee_id':
                    user_info["employee_id"] = meta.meta_value
                elif meta.meta_key == 'region':
                    user_info["region"] = meta.meta_value
                    
            # Get current state
            current_state_meta = user_meta.filter(meta_key='whatsapp_current_state').first()
            
            current_state = ""
            current_course_id = None
            
            if current_state_meta:
                current_state = current_state_meta.meta_value
                state_parts = current_state.split("|")
                if len(state_parts) > 0:
                    current_course_id = state_parts[0]
            
            # Use course ID from state or default to 1760 (from your provided data)
            course_id = current_course_id if current_course_id and current_course_id != 'None' else 1760
            
            # Get lessons from course data
            dynamic_lessons = CourseDataService.get_course_lessons(course_id)
            logger.info(f"Dynamic lessons extracted for course {course_id}: {dynamic_lessons}")
            
            # If dynamic extraction failed, fall back to hardcoded structure
            if not dynamic_lessons:
                logger.warning(f"Could not extract dynamic lessons for course {course_id}, using default structure")
                dynamic_lessons = [
                    {"id": "lesson_1", "title": "LESSON 1. WHAT IS WORKPLACE SEXUAL HARASSMENT?", "message_ids": ["m-2"]},
                    {"id": "lesson_2", "title": "LESSON 2 WHAT CONSTITUTES A \"WORKPLACE\"?", "message_ids": ["m-3"]},
                    {"id": "lesson_3", "title": "LESSON 3: IMPACT VS. INTENT", "message_ids": ["m-4"]},
                    {"id": "quiz_1", "title": "QUIZ 1", "message_ids": ["m-5"], "is_quiz": True},
                    {"id": "lesson_4", "title": "PORNOGRAPHY IN THE WORKPLACE", "message_ids": ["m-6"]},
                    {"id": "lesson_5", "title": "SEXUALLY COLOURED REMARKS", "message_ids": ["m-7"]},
                    {"id": "lesson_6", "title": "DEMANDING SEXUAL FAVOURS", "message_ids": ["m-8"]},
                    {"id": "quiz_2", "title": "QUIZ 2", "message_ids": ["m-9"], "is_quiz": True},
                    {"id": "lesson_7", "title": "UNWELCOME GESTURES", "message_ids": ["m-10"]},
                    {"id": "lesson_8", "title": "FACING SEXUAL HARASSMENT? WHAT YOU SHOULD DO", "message_ids": ["m-11"]},
                    {"id": "lesson_9", "title": "CASE FILING & INQUIRY PROCESS", "message_ids": ["m-12"]},
                    {"id": "assessment", "title": "Post Course Assessment", "message_ids": ["m-13"], "is_assessment": True},
                    {"id": "learning_journey", "title": "Learning Journey", "message_ids": ["m-14"]}
                ]
            
            # Find current progress
            current_message_id = ""
            if current_state:
                state_parts = current_state.split("|")
                if len(state_parts) > 1:
                    current_message_id = state_parts[1]
            
            # Get current message number
            current_msg_num = 0
            if current_message_id.startswith("m-"):
                try:
                    current_msg_num = int(current_message_id.replace("m-", ""))
                except:
                    pass
            
            # Process lesson completion and points
            lesson_progress = []
            total_points = 0
            completed_lessons = 0
            
            for lesson in dynamic_lessons:
                # Default status is Not Started
                status = "Not Started"
                earned_points = 0
                
                # Get highest message ID in this lesson
                highest_msg_id = 0
                for msg_id in lesson["message_ids"]:
                    if msg_id.startswith("m-"):
                        try:
                            msg_num = int(msg_id.replace("m-", ""))
                            if msg_num > highest_msg_id:
                                highest_msg_id = msg_num
                        except:
                            pass
                
                # Check if lesson has been reached/passed
                if current_msg_num > highest_msg_id:
                    status = "Completed"
                    earned_points = 100
                    completed_lessons += 1
                elif current_msg_num == highest_msg_id:
                    status = "In Progress"
                    earned_points = 50
                    
                # For quizzes, check if they've been answered correctly
                if lesson.get("is_quiz", False):
                    for msg_id in lesson["message_ids"]:
                        quiz_meta = user_meta.filter(meta_key=f"quiz_answered_{msg_id}").first()
                        if quiz_meta and quiz_meta.meta_value:
                            # Quiz was attempted
                            try:
                                quiz_data = json.loads(quiz_meta.meta_value)
                                if quiz_data.get("is_correct", False):
                                    status = "Completed"
                                    earned_points = 100
                                    completed_lessons += 1
                                else:
                                    status = "Failed"
                                    earned_points = 50
                            except:
                                status = "Attempted"
                                earned_points = 50
                
                # Add videos viewed logic
                if not lesson.get("is_quiz", False):
                    # Check if relevant videos were viewed
                    video_viewed = False
                    for msg_id in lesson["message_ids"]:
                        video_meta = user_meta.filter(meta_key=f"video_viewed_video_{msg_id.replace('m-', '')}").exists()
                        if video_meta:
                            video_viewed = True
                            if status == "Not Started":
                                status = "In Progress"
                                earned_points = max(earned_points, 50)
                
                lesson_progress.append({
                    "id": lesson["id"],
                    "title": lesson["title"],
                    "status": status,
                    "earned_points": earned_points
                })
                
                total_points += earned_points
            
            # Calculate average points
            avg_points = 0
            if len(dynamic_lessons) > 0:
                avg_points = round(total_points / len(dynamic_lessons), 1)
                
            # Format the response as a table-friendly structure
            response_data = {
                "user_info": user_info,
                "progress": lesson_progress,
                "summary": {
                    "completed_lessons": completed_lessons,
                    "total_lessons": len(dynamic_lessons),
                    "completion_percentage": round((completed_lessons / len(dynamic_lessons)) * 100, 1) if dynamic_lessons else 0,
                    "average_points": avg_points,
                    "current_message": current_message_id,
                    "course_id": course_id
                }
            }
            
            return Response(response_data, status=200)
                
        except WpUsers.DoesNotExist:
            return Response({"error": f"User with ID {user_id} not found"}, status=404)
            
    except Exception as e:
        import traceback
        return Response({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_users_progress_report(request):
    """Get progress report for all users"""
    try:
        logger.info("Getting progress report for all users")
        
        # Get all users who have WhatsApp interaction data
        users_with_progress = WpUsermeta.objects.filter(
            meta_key='whatsapp_current_state'
        ).values_list('user_id', flat=True).distinct()
        
        logger.info(f"Found {len(users_with_progress)} users with WhatsApp progress")
        
        # If no users with progress, get all users
        if not users_with_progress:
            logger.info("No users with WhatsApp progress found, getting all users")
            users_with_progress = WpUsers.objects.all().values_list('id', flat=True)
        
        all_users_data = []
        
        for user_id in users_with_progress:
            try:
                logger.info(f"Processing user {user_id}")
                
                # Get user details
                try:
                    user = WpUsers.objects.get(id=user_id)
                except WpUsers.DoesNotExist:
                    logger.warning(f"User {user_id} not found")
                    continue
                
                # Get user metadata
                user_meta = WpUsermeta.objects.filter(user_id=user_id)
                
                # Get basic profile info
                user_info = {
                    "user_id": user_id,
                    "name": user.display_name,
                    "email": user.user_email,
                    "user_registered": user.user_registered,
                    "department": "",
                    "employee_id": "",
                    "phone_number": "",
                    "region": ""
                }
                
                # Get additional metadata fields
                for meta in user_meta:
                    if meta.meta_key == 'waid':
                        user_info["phone_number"] = meta.meta_value
                    elif meta.meta_key == 'department':
                        user_info["department"] = meta.meta_value
                    elif meta.meta_key == 'employee_id':
                        user_info["employee_id"] = meta.meta_value
                    elif meta.meta_key == 'region':
                        user_info["region"] = meta.meta_value
                
                # Get current state
                current_state_meta = user_meta.filter(meta_key='whatsapp_current_state').first()
                current_state = ""
                current_course_id = None
                completion_status = "Not Started"
                logger.info(f"Current state meta: {current_state_meta}")
                if current_state_meta:
                    current_state = current_state_meta.meta_value
                    state_parts = current_state.split("|")
                    if len(state_parts) > 0 and state_parts[0] not in ['None', '']:
                        current_course_id = state_parts[0]
                    
                    # Determine completion status from state
                    if len(state_parts) > 2:
                        step = state_parts[2]
                        if step == 'completed':
                            completion_status = "Completed"
                        elif current_course_id:
                            completion_status = "In Progress"
                
                # Get course ID
                course_id = current_course_id if current_course_id and current_course_id != 'None' else 1760
                
                # Get lessons from course data using CourseDataService
                dynamic_lessons = CourseDataService.get_course_lessons(course_id)
                
                # If dynamic extraction failed, use default structure
                if not dynamic_lessons:
                    dynamic_lessons = [
                        {"id": "lesson_1", "title": "LESSON 1. WHAT IS WORKPLACE SEXUAL HARASSMENT?", "message_ids": ["m-2"]},
                        {"id": "lesson_2", "title": "LESSON 2 WHAT CONSTITUTES A \"WORKPLACE\"?", "message_ids": ["m-3"]},
                        {"id": "lesson_3", "title": "LESSON 3: IMPACT VS. INTENT", "message_ids": ["m-4"]},
                        {"id": "quiz_1", "title": "QUIZ 1", "message_ids": ["m-5"], "is_quiz": True},
                        {"id": "lesson_4", "title": "PORNOGRAPHY IN THE WORKPLACE", "message_ids": ["m-6"]},
                        {"id": "lesson_5", "title": "SEXUALLY COLOURED REMARKS", "message_ids": ["m-7"]},
                        {"id": "lesson_6", "title": "DEMANDING SEXUAL FAVOURS", "message_ids": ["m-8"]},
                        {"id": "quiz_2", "title": "QUIZ 2", "message_ids": ["m-9"], "is_quiz": True},
                        {"id": "lesson_7", "title": "UNWELCOME GESTURES", "message_ids": ["m-10"]},
                        {"id": "lesson_8", "title": "FACING SEXUAL HARASSMENT? WHAT YOU SHOULD DO", "message_ids": ["m-11"]},
                        {"id": "lesson_9", "title": "CASE FILING & INQUIRY PROCESS", "message_ids": ["m-12"]},
                        {"id": "assessment", "title": "Post Course Assessment", "message_ids": ["m-13"], "is_assessment": True},
                        {"id": "learning_journey", "title": "Learning Journey", "message_ids": ["m-14"]}
                    ]
                
                # Calculate progress summary
                current_message_id = ""
                if current_state:
                    state_parts = current_state.split("|")
                    if len(state_parts) > 1:
                        current_message_id = state_parts[1]
                
                current_msg_num = 0
                if current_message_id.startswith("m-"):
                    try:
                        current_msg_num = int(current_message_id.replace("m-", ""))
                    except:
                        pass
                
                # Calculate lesson progress
                completed_lessons = 0
                total_points = 0
                lesson_progress = []
                
                for lesson in dynamic_lessons:
                    status = "Not Started"
                    earned_points = 0
                    
                    # Get highest message ID in this lesson
                    highest_msg_id = 0
                    for msg_id in lesson["message_ids"]:
                        if msg_id.startswith("m-"):
                            try:
                                msg_num = int(msg_id.replace("m-", ""))
                                if msg_num > highest_msg_id:
                                    highest_msg_id = msg_num
                            except:
                                pass
                    
                    # Check lesson completion
                    if current_msg_num > highest_msg_id:
                        status = "Completed"
                        earned_points = 100
                        completed_lessons += 1
                    elif current_msg_num == highest_msg_id:
                        status = "In Progress"
                        earned_points = 50
                    
                    # Check quiz completion
                    if lesson.get("is_quiz", False):
                        for msg_id in lesson["message_ids"]:
                            quiz_meta = user_meta.filter(meta_key=f"quiz_answered_{msg_id}").first()
                            if quiz_meta and quiz_meta.meta_value:
                                try:
                                    quiz_data = json.loads(quiz_meta.meta_value)
                                    if quiz_data.get("is_correct", False):
                                        status = "Completed"
                                        earned_points = 100
                                        completed_lessons += 1
                                    else:
                                        status = "Failed"
                                        earned_points = 50
                                except:
                                    status = "Attempted"
                                    earned_points = 50
                    
                    lesson_progress.append({
                        "id": lesson["id"],
                        "title": lesson["title"],
                        "status": status,
                        "earned_points": earned_points
                    })
                    
                    total_points += earned_points
                
                # Calculate completion percentage
                completion_percentage = round((completed_lessons / len(dynamic_lessons)) * 100, 1) if dynamic_lessons else 0
                avg_points = round(total_points / len(dynamic_lessons), 1) if dynamic_lessons else 0
                
                # Update completion status based on actual progress
                if completion_percentage == 100:
                    completion_status = "Completed"
                elif completion_percentage > 0:
                    completion_status = "In Progress"
                
                user_data = {
                    'user_info': user_info,
                    'progress_summary': {
                        'completed_lessons': completed_lessons,
                        'total_lessons': len(dynamic_lessons),
                        'completion_percentage': completion_percentage,
                        'average_points': avg_points,
                        'current_message': current_message_id,
                        'course_id': course_id
                    },
                    'completion_status': completion_status,
                    'lesson_progress': lesson_progress
                }
                
                all_users_data.append(user_data)
                logger.info(f"Processed user {user_id}: {completion_status} ({completion_percentage}%)")
                        
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {str(e)}")
                # Add error entry for this user
                try:
                    user = WpUsers.objects.get(id=user_id)
                    all_users_data.append({
                        'user_info': {
                            'user_id': user_id,
                            'name': user.display_name,
                            'email': user.user_email,
                            'error': f'Processing error: {str(e)}'
                        },
                        'progress_summary': {},
                        'completion_status': 'Error',
                        'lesson_progress': []
                    })
                except WpUsers.DoesNotExist:
                    logger.warning(f"User {user_id} not found")
        
        # Summary statistics
        total_users = len(all_users_data)
        completed_users = len([u for u in all_users_data if u.get('completion_status') == 'Completed'])
        in_progress_users = len([u for u in all_users_data if u.get('completion_status') == 'In Progress'])
        not_started_users = len([u for u in all_users_data if u.get('completion_status') == 'Not Started'])
        
        response_data = {
            'summary': {
                'total_users': total_users,
                'completed_users': completed_users,
                'in_progress_users': in_progress_users,
                'not_started_users': not_started_users,
                'completion_rate': round((completed_users / total_users) * 100, 2) if total_users > 0 else 0
            },
            'users': all_users_data,
            'generated_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logger.info(f"Successfully generated report for {total_users} users")
        logger.info(f"Completed: {completed_users}, In Progress: {in_progress_users}, Not Started: {not_started_users}")
        
        return Response(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Error in get_all_users_progress_report: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response({
            'error': 'Failed to generate progress report',
            'details': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
    

# Add these new endpoints at the end of the file

@api_view(['GET'])
@permission_classes([AllowAny])
def get_comprehensive_user_analytics(request, user_id=None):
    """Get comprehensive analytics for a specific user"""
    try:
        if not user_id:
            if request.user.is_authenticated:
                user_id = request.user.id
            else:
                return Response({"error": "User ID required"}, status=401)
        
        analytics = course_tracker.get_comprehensive_user_analytics(user_id)
        
        if analytics:
            return Response(analytics, status=200)
        else:
            return Response({"error": "User not found or no data available"}, status=404)
            
    except Exception as e:
        logger.error(f"Error getting comprehensive analytics: {str(e)}")
        return Response({
            "error": "Failed to get analytics",
            "details": str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_detailed_course_report(request, course_id=None):
    """Get detailed report for a specific course with paginated user details"""
    try:
        if not course_id:
            course_id = 10362  # Default course ID

        # Pagination params
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))

        # Get all users who have interacted with this course
        course_users = WpUsermeta.objects.filter(
            meta_key__contains=f'course_{course_id}'
        ).values_list('user_id', flat=True).distinct()

        # Also get users from whatsapp_current_state
        state_users = WpUsermeta.objects.filter(
            meta_key='whatsapp_current_state',
            meta_value__startswith=f'{course_id}|'
        ).values_list('user_id', flat=True)

        all_users = list(set(list(course_users) + list(state_users)))
        total_users = len(all_users)

        # Paginate users
        start = (page - 1) * limit
        end = start + limit
        paginated_users = all_users[start:end]

        detailed_report = {
            'course_id': course_id,
            'total_users': total_users,
            'users_detail': [],
            'pagination': {
                'page': page,
                'limit': limit,
                'total_users': total_users,
                'total_pages': (total_users + limit - 1) // limit
            },
            'aggregated_stats': {
                'enrollment_count': 0,
                'completion_count': 0,
                'in_progress_count': 0,
                'not_started_count': 0,
                'average_completion_rate': 0,
                'total_video_views': 0,
                'total_quiz_attempts': 0,
                'quiz_success_rate': 0
            }
        }

        total_video_views = 0
        total_quiz_attempts = 0
        total_quiz_successes = 0

        for user_id in paginated_users:
            try:
                user_analytics = course_tracker.get_comprehensive_user_analytics(user_id)

                if user_analytics:
                    # Filter data for this specific course
                    course_enrollments = [e for e in user_analytics['course_enrollments'] if e.get('course_id') == str(course_id)]
                    course_completions = [c for c in user_analytics['course_completions'] if c.get('course_id') == str(course_id)]

                    # Determine status
                    status = 'Not Started'
                    if course_completions:
                        status = 'Completed'
                        detailed_report['aggregated_stats']['completion_count'] += 1
                    elif course_enrollments:
                        status = 'In Progress'
                        detailed_report['aggregated_stats']['in_progress_count'] += 1
                    else:
                        detailed_report['aggregated_stats']['not_started_count'] += 1

                    if course_enrollments:
                        detailed_report['aggregated_stats']['enrollment_count'] += 1

                    # Count video views
                    video_views = len(user_analytics['video_interactions'])
                    total_video_views += video_views

                    # Count quiz attempts and successes
                    quiz_attempts = len(user_analytics['quiz_performance'])
                    quiz_successes = len([q for q in user_analytics['quiz_performance'] if q.get('is_correct')])
                    total_quiz_attempts += quiz_attempts
                    total_quiz_successes += quiz_successes

                    user_detail = {
                        'user_id': user_id,
                        'user_info': user_analytics['user_info'],
                        'status': status,
                        'enrollment_date': course_enrollments[0].get('enrolled_at') if course_enrollments else None,
                        'completion_date': course_completions[0].get('completed_at') if course_completions else None,
                        'video_views': video_views,
                        'quiz_attempts': quiz_attempts,
                        'quiz_successes': quiz_successes,
                        'current_progress': user_analytics['overall_progress']
                    }

                    detailed_report['users_detail'].append(user_detail)

            except Exception as e:
                logger.error(f"Error processing user {user_id} for course report: {e}")

        # Calculate aggregated statistics
        if detailed_report['aggregated_stats']['enrollment_count'] > 0:
            detailed_report['aggregated_stats']['average_completion_rate'] = round(
                (detailed_report['aggregated_stats']['completion_count'] / detailed_report['aggregated_stats']['enrollment_count']) * 100, 2
            )

        detailed_report['aggregated_stats']['total_video_views'] = total_video_views
        detailed_report['aggregated_stats']['total_quiz_attempts'] = total_quiz_attempts

        if total_quiz_attempts > 0:
            detailed_report['aggregated_stats']['quiz_success_rate'] = round(
                (total_quiz_successes / total_quiz_attempts) * 100, 2
            )

        return Response(detailed_report, status=200)

    except Exception as e:
        logger.error(f"Error getting detailed course report: {str(e)}")
        return Response({
            "error": "Failed to get course report",
            "details": str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_learning_analytics_dashboard(request):
    """Get comprehensive learning analytics dashboard data with search"""
    try:
        # Get overall statistics
        total_users = WpUsers.objects.count()
        active_users = WpUsermeta.objects.filter(
            meta_key='whatsapp_current_state'
        ).values_list('user_id', flat=True).distinct().count()
        completed_users = WpUsermeta.objects.filter(
            meta_key__endswith='_completion'
        ).values_list('user_id', flat=True).distinct().count()
        total_video_views = WpUsermeta.objects.filter(
            meta_key__startswith='video_viewed_'
        ).count()
        total_quiz_attempts = WpUsermeta.objects.filter(
            meta_key__startswith='quiz_answered_'
        ).count()

        # Get search query
        search = request.GET.get('search', '').strip()

        # Dynamically get all published course IDs with optional search
        courses_query = WpPosts.objects.filter(post_type='sfwd-courses', post_status='publish')
        if search:
            courses_query = courses_query.filter(post_title__icontains=search)

        course_ids = list(courses_query.values_list('id', flat=True))

        # Course-wise statistics
        course_stats = {}
        for course_id in course_ids:
            try:
                course = WpPosts.objects.get(id=course_id, post_type='sfwd-courses')
                course_name = course.post_title

                enrolled_count = WpUsermeta.objects.filter(
                    meta_key=f'course_{course_id}_access_from'
                ).count()

                completed_count = WpUsermeta.objects.filter(
                    meta_key=f'course_{course_id}_completion'
                ).count()

                course_stats[course_id] = {
                    'name': course_name,
                    'enrolled_users': enrolled_count,
                    'completed_users': completed_count,
                    'completion_rate': round((completed_count / enrolled_count) * 100, 2) if enrolled_count > 0 else 0
                }
            except WpPosts.DoesNotExist:
                continue

        # Recent activity
        recent_activities = []
        recent_completions = WpUsermeta.objects.filter(
            meta_key__endswith='_completion'
        ).order_by('-umeta_id')[:10]

        for completion in recent_completions:
            try:
                completion_data = json.loads(completion.meta_value)
                user = WpUsers.objects.get(id=completion.user_id)

                recent_activities.append({
                    'user_name': user.display_name,
                    'activity_type': 'course_completion',
                    'course_id': completion_data.get('course_id'),
                    'timestamp': completion_data.get('completed_at')
                })
            except Exception:
                continue

        dashboard_data = {
            'overview_stats': {
                'total_users': total_users,
                'active_users': active_users,
                'completed_users': completed_users,
                'total_video_views': total_video_views,
                'total_quiz_attempts': total_quiz_attempts,
                'engagement_rate': round((active_users / total_users) * 100, 2) if total_users > 0 else 0
            },
            'course_statistics': course_stats,
            'recent_activities': recent_activities,
            'generated_at': timezone.now().isoformat()
        }

        return Response(dashboard_data, status=200)

    except Exception as e:
        logger.error(f"Error getting learning analytics dashboard: {str(e)}")
        return Response({
            "error": "Failed to get dashboard data",
            "details": str(e)
        }, status=500)
    



@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_users(request):
    """Get all users with optional filtering"""
    try:
        # Get query parameters for filtering
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 10))
        search = request.GET.get('search', '')

        # Base queryset
        users_query = WpUsers.objects.all()
        # Apply search filter if provided
        if search:
            users_query = users_query.filter(
                Q(display_name__icontains=search) |
                Q(user_email__icontains=search) |
                Q(user_login__icontains=search)
            )

        # Pagination
        start = (page - 1) * limit
        end = start + limit
        users = users_query[start:end]
        total_count = users_query.count()

        # Format user data
        users_data = []
        for user in users:
            # Fetch the WhatsApp number (waid) from WpUsermeta
            waid_meta = WpUsermeta.objects.filter(
                user_id=user.id, meta_key='waid'
            ).first()
            waid = waid_meta.meta_value if waid_meta else None

            users_data.append({
                'id': user.id,
                'user_login': user.user_login,
                'user_nicename': user.user_nicename,
                'user_email': user.user_email,
                'user_url': user.user_url,
                'user_registered': user.user_registered,
                'user_status': user.user_status,
                'display_name': user.display_name,
                'whatsapp_number': waid  # Add WhatsApp number here
            })

        response_data = {
            'users': users_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total_count': total_count,
                'total_pages': (total_count + limit - 1) // limit
            }
        }

        return Response(response_data, status=200)

    except Exception as e:
        return Response({'error': str(e)}, status=500)




from django.db import models
from .models import WpPosts, WpPostmeta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import json

@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_courses(request):
    """Get all courses with optional filtering and pagination"""
    try:
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        search = request.GET.get('search', '')
        status = request.GET.get('status', 'publish')
        
        # Base queryset for courses
        courses_query = WpPosts.objects.filter(
            post_type='sfwd-courses',
            post_status=status
        ).order_by('-post_date')
        
        # Apply search filter if provided
        if search:
            courses_query = courses_query.filter(
                models.Q(post_title__icontains=search) |
                models.Q(post_content__icontains=search) |
                models.Q(post_excerpt__icontains=search)
            )
        
        # Pagination
        start = (page - 1) * limit
        end = start + limit
        courses = courses_query[start:end]
        total_count = courses_query.count()
        
        # Format course data
        courses_data = []
        for course in courses:
            # Get course metadata
            course_meta = WpPostmeta.objects.filter(post_id=course.id)
            metadata = {meta.meta_key: meta.meta_value for meta in course_meta}
            
            course_data = {
                'id': course.id,
                'title': course.post_title,
                'content': course.post_content,
                'excerpt': course.post_excerpt,
                'status': course.post_status,
                'author_id': course.post_author,
                'created_date': course.post_date,
                'modified_date': course.post_modified,
                'slug': course.post_name,
                'guid': course.guid,
                'menu_order': course.menu_order,
                'comment_count': course.comment_count,
                # Course specific metadata
                'course_price': metadata.get('_sfwd-courses_course_price', ''),
                'course_price_type': metadata.get('_sfwd-courses_course_price_type', ''),
                'course_access_list': metadata.get('_sfwd-courses_course_access_list', ''),
                'course_lesson_orderby': metadata.get('_sfwd-courses_course_lesson_orderby', ''),
                'course_materials': metadata.get('_sfwd-courses_course_materials', ''),
                'course_certificate': metadata.get('_sfwd-courses_certificate', ''),
                'course_points': metadata.get('_sfwd-courses_course_points', ''),
                'course_disable_lesson_progression': metadata.get('_sfwd-courses_course_disable_lesson_progression', ''),
                'metadata': metadata
            }
            courses_data.append(course_data)
        
        response_data = {
            'courses': courses_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total_count': total_count,
                'total_pages': (total_count + limit - 1) // limit
            }
        }
        
        return Response(response_data, status=200)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    

# views.py
from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .utils import get_vdocipher_otp_and_playbackinfo
from .models import OneTimeVideoToken

# ...existing code...
@api_view(['GET'])
@permission_classes([AllowAny])
def drm_video_view(request):
    """Render DRM video player with one-time token validation"""
    import json, time, threading, traceback
    token = request.GET.get('token')
    if not token:
        return render(request, 'VdoCipher_DRM.html', {
            'error': 'Access token is required',
            'vdocipher_url': None,
            'redirect_delay': None,
            'token_metadata': '{}'
        })
    try:
        video_token = OneTimeVideoToken.objects.get(token=token, is_used=False)
        if video_token.is_used:
            return render(request, 'VdoCipher_DRM.html', {
                'error': 'This video link has already been used',
                'vdocipher_url': None,
                'redirect_delay': None,
                'token_metadata': '{}'
            })
        if video_token.is_expired():
            return render(request, 'VdoCipher_DRM.html', {
                'error': 'This video link has expired',
                'vdocipher_url': None,
                'redirect_delay': None,
                'token_metadata': '{}'
            })

        # Mark used
        video_token.mark_as_used()
        logger.info(f"Marked token {token} as used")

        # Metadata
        token_metadata = {}
        if video_token.meta_data:
            try:
                token_metadata = json.loads(video_token.meta_data)
            except Exception:
                logger.warning("Invalid token meta_data JSON")

        # Base delay (video length) + buffer (redirect extra)
        delay_seconds =  int(token_metadata.get('dynamic_delay', 205))
        video_caption = token_metadata.get('video_caption', 'Video Lesson')

        # Get VdoCipher OTP
        otp, playback_info = get_vdocipher_otp_and_playbackinfo(video_token.video_id)
        if not (otp and playback_info):
            return render(request, 'VdoCipher_DRM.html', {
                'error': 'Unable to generate secure video URL',
                'vdocipher_url': None,
                'redirect_delay': None,
                'token_metadata': json.dumps(token_metadata)
            })
        vdocipher_url = f"https://player.vdocipher.com/v2/?otp={otp}&playbackInfo={playback_info}"

        # Prepare WhatsApp rewatch template send after delay_seconds
        def send_rewatch_template_after_delay():
            try:
                time.sleep(delay_seconds)
                rewatch_template_sid = getattr(settings, 'WHATSAPP_VIDEO_REWATCH_TEMPLATE_SID', None)
                if not rewatch_template_sid:
                    logger.warning("No rewatch template SID configured")
                    return
                user_phone = video_token.user_phone
                if not user_phone.startswith('+'):
                    user_phone = f'+{user_phone}'
                if not user_phone.startswith('whatsapp:'):
                    user_phone = f'whatsapp:{user_phone}'
                user_name = "Student"
                try:
                    from .models import WpUsermeta, WpUsers
                    clean_phone = video_token.user_phone.replace('+', '')
                    meta = WpUsermeta.objects.filter(meta_key='waid', meta_value__icontains=clean_phone).first()
                    if meta:
                        u = WpUsers.objects.get(id=meta.user_id)
                        user_name = u.display_name or u.user_nicename or "Student"
                except Exception as e:
                    logger.warning(f"User lookup failed: {e}")
                res = whatsapp_service.send_video_rewatch_template_message(
                    to_number=user_phone,
                    template_sid=rewatch_template_sid,
                    video_caption=video_caption,
                    user_name=user_name
                )
                if res.get('success'):
                    logger.info(f"Rewatch template sent after {delay_seconds}s (SID {res.get('message_sid')})")
                else:
                    logger.error(f"Failed rewatch template: {res.get('error')}")
            except Exception as e:
                logger.error(f"Delayed rewatch template error: {e}")
                logger.error(traceback.format_exc())

        threading.Thread(target=send_rewatch_template_after_delay, daemon=True).start()

        # Redirect delay = video delay + buffer (30s)
        redirect_delay_seconds = delay_seconds + 30
        logger.info(f"Rendering DRM template: redirect_delay={redirect_delay_seconds}")

        return render(request, 'VdoCipher_DRM.html', {
            'vdocipher_url': vdocipher_url,
            'error': None,
            'redirect_delay': redirect_delay_seconds,
            'token_metadata': json.dumps(token_metadata)
        })

    except OneTimeVideoToken.DoesNotExist:
        return render(request, 'VdoCipher_DRM.html', {
            'error': 'Invalid or expired video token',
            'vdocipher_url': None,
            'redirect_delay': None,
            'token_metadata': '{}'
        })
    except Exception as e:
        logger.error(f"Error in drm_video_view: {e}")
        return render(request, 'VdoCipher_DRM.html', {
            'error': 'An error occurred while loading the video',
            'vdocipher_url': None,
            'redirect_delay': None,
            'token_metadata': '{}'
        })
# ...existing code...


@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_groups(request):
    """Get all groups from wp_posts table with optional filtering and pagination"""
    try:
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        search = request.GET.get('search', '')
        status = request.GET.get('status', 'publish')
        
        # Base queryset for groups - equivalent to your SQL query
        groups_query = WpPosts.objects.filter(
            post_type='groups',
            post_status=status
        ).order_by('-post_date')
        
        # Apply search filter if provided
        if search:
            groups_query = groups_query.filter(
                Q(post_title__icontains=search) |
                Q(post_content__icontains=search) |
                Q(post_excerpt__icontains=search)
            )
        
        # Pagination
        start = (page - 1) * limit
        end = start + limit
        groups = groups_query[start:end]
        total_count = groups_query.count()
        
        # Format group data - matching your SQL SELECT fields
        groups_data = []
        for group in groups:
            
            group_data = {
                'ID': group.id,  # Matching your SQL field name
                'post_title': group.post_title,
                'post_status': group.post_status,
                'post_date': group.post_date,
                # Additional useful fields
                'post_content': group.post_content,
                'post_excerpt': group.post_excerpt,
                'post_author': group.post_author,
                'post_modified': group.post_modified,
                'post_name': group.post_name,  # slug
                'guid': group.guid,
                'menu_order': group.menu_order,
                'comment_count': group.comment_count,
                # Group specific metadata (if any)
            }
            groups_data.append(group_data)
        
        response_data = {
            'success': True,
            'message': f'Found {total_count} groups',
            'groups': groups_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total_count': total_count,
                'total_pages': (total_count + limit - 1) // limit,
                'has_next': page * limit < total_count,
                'has_previous': page > 1
            },
            'filters_applied': {
                'search': search,
                'status': status
            }
        }
        
        logger.info(f"Successfully retrieved {len(groups_data)} groups (page {page})")
        return Response(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Error getting groups: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve groups',
            'details': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_group_by_id(request, group_id):
    """Get a specific group by ID"""
    try:
        group = WpPosts.objects.get(
            id=group_id,
            post_type='groups'
        )
        
        
        group_data = {
            'ID': group.id,
            'post_title': group.post_title,
            'post_status': group.post_status,
            'post_date': group.post_date,
            'post_content': group.post_content,
            'post_excerpt': group.post_excerpt,
            'post_author': group.post_author,
            'post_modified': group.post_modified,
            'post_name': group.post_name,
            'guid': group.guid,
            'menu_order': group.menu_order,
            'comment_count': group.comment_count,
          
        }
        
        return Response({
            'success': True,
            'group': group_data
        }, status=200)
        
    except WpPosts.DoesNotExist:
        return Response({
            'success': False,
            'error': f'Group with ID {group_id} not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting group {group_id}: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve group',
            'details': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_groups_summary(request):
    """Get summary statistics for groups"""
    try:
        # Get counts by status
        total_groups = WpPosts.objects.filter(post_type='groups').count()
        published_groups = WpPosts.objects.filter(post_type='groups', post_status='publish').count()
        draft_groups = WpPosts.objects.filter(post_type='groups', post_status='draft').count()
        private_groups = WpPosts.objects.filter(post_type='groups', post_status='private').count()
        
        # Get recent groups
        recent_groups = WpPosts.objects.filter(
            post_type='groups',
            post_status='publish'
        ).order_by('-post_date')[:5]
        
        recent_groups_data = []
        for group in recent_groups:
            recent_groups_data.append({
                'ID': group.id,
                'post_title': group.post_title,
                'post_date': group.post_date,
                'post_status': group.post_status
            })
        
        summary_data = {
            'success': True,
            'summary': {
                'total_groups': total_groups,
                'published_groups': published_groups,
                'draft_groups': draft_groups,
                'private_groups': private_groups,
                'publish_rate': round((published_groups / total_groups) * 100, 2) if total_groups > 0 else 0
            },
            'recent_groups': recent_groups_data,
            'generated_at': timezone.now().isoformat()
        }
        
        return Response(summary_data, status=200)
        
    except Exception as e:
        logger.error(f"Error getting groups summary: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve groups summary',
            'details': str(e)
        }, status=500)
    


@api_view(['GET'])
@permission_classes([AllowAny])
def get_group_users(request, group_id):
    """Get all user IDs from a specific group"""
    try:
        # Construct the meta_key pattern for the group
        meta_key = f'learndash_group_users_{group_id}'
        
        logger.info(f"Looking for group users with meta_key: {meta_key}")
        
        # Query wp_usermeta table for the specific meta_key
        group_users_meta = WpUsermeta.objects.filter(
            meta_key=meta_key
        )
        
        if not group_users_meta.exists():
            return Response({
                'success': False,
                'message': f'No users found for group {group_id}',
                'group_id': group_id,
                'meta_key': meta_key,
                'users': []
            }, status=404)
        
        # Extract user IDs and get user details
        users_data = []
        total_users = 0
        
        for meta in group_users_meta:
            user_id = meta.user_id
            total_users += 1
            
            try:
                # Get user details from wp_users
                user = WpUsers.objects.get(id=user_id)
                
                # Get additional user metadata
                user_meta = WpUsermeta.objects.filter(user_id=user_id)
                
                # Build user info
                user_info = {
                    'user_id': user_id,
                    'user_login': user.user_login,
                    'user_email': user.user_email,
                    'display_name': user.display_name,
                    'user_registered': user.user_registered,
                    'user_status': user.user_status,
                    'meta_value': meta.meta_value,  # The actual meta_value from wp_usermeta
                }
                
                # Add relevant metadata
                for user_meta_item in user_meta:
                    if user_meta_item.meta_key in ['waid', 'department', 'employee_id', 'region', 'phone']:
                        user_info[user_meta_item.meta_key] = user_meta_item.meta_value
                
                users_data.append(user_info)
                
            except WpUsers.DoesNotExist:
                logger.warning(f"User with ID {user_id} not found in wp_users table")
                # Still add the user_id even if user details not found
                users_data.append({
                    'user_id': user_id,
                    'error': 'User details not found',
                    'meta_value': meta.meta_value
                })
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {e}")
                users_data.append({
                    'user_id': user_id,
                    'error': str(e),
                    'meta_value': meta.meta_value
                })
        
        # Also get group details if available
        group_info = None
        try:
            group = WpPosts.objects.get(id=group_id, post_type='groups')
            group_info = {
                'group_id': group_id,
                'group_name': group.post_title,
                'group_status': group.post_status,
                'created_date': group.post_date,
                'modified_date': group.post_modified
            }
        except WpPosts.DoesNotExist:
            logger.warning(f"Group with ID {group_id} not found")
            group_info = {
                'group_id': group_id,
                'error': 'Group details not found'
            }
        
        response_data = {
            'success': True,
            'message': f'Found {total_users} users in group {group_id}',
            'group_info': group_info,
            'meta_key': meta_key,
            'total_users': total_users,
            'users': users_data
        }
        
        logger.info(f"Successfully retrieved {total_users} users for group {group_id}")
        return Response(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Error getting group users for group {group_id}: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve group users',
            'details': str(e),
            'group_id': group_id
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_group_introduction_message(request, group_id):
    """Send introduction message to all users in a specific group"""
    try:
        course_id = request.data.get('course_id')
        use_template = request.data.get('use_template', True)
        
        if not course_id:
            return Response({
                'error': 'course_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"Sending introduction messages to group {group_id} for course {course_id}")
        
        # Get all users in the group
        meta_key = f'learndash_group_users_{group_id}'
        group_users_meta = WpUsermeta.objects.filter(meta_key=meta_key)
        
        if not group_users_meta.exists():
            return Response({
                'success': False,
                'error': f'No users found in group {group_id}',
                'group_id': group_id,
                'course_id': course_id
            }, status=404)
        
        # Verify course exists
        try:
            course = WpPosts.objects.get(id=course_id, post_type='sfwd-courses')
            course_name = course.post_title
        except WpPosts.DoesNotExist:
            return Response({
                'error': f'Course with ID {course_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get course message data
        try:
            message_meta = WpPostmeta.objects.get(
                post_id=course_id,
                meta_key='messageData'
            )
            serialized_data = message_meta.meta_value
            
            if not serialized_data:
                return Response({
                    'error': f'Message data not found for course ID {course_id}'
                }, status=status.HTTP_404_NOT_FOUND)
        except WpPostmeta.DoesNotExist:
            return Response({
                'error': f'Message data (messageData) not found for course ID {course_id}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Parse the serialized message data
        try:
            message_data = whatsapp_service.parse_serialized_data(serialized_data)
            if not message_data:
                return Response({
                    'error': 'Failed to parse message data'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Failed to parse message data: {str(e)}")
            return Response({
                'error': f'Invalid message data format: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process each user in the group
        success_count = 0
        failed_count = 0
        results = []
        
        for meta in group_users_meta:
            user_id = meta.user_id
            
            try:
                # Get user details
                user = WpUsers.objects.get(id=user_id)
                user_name = user.display_name or user.user_nicename or "Student"
                
                # Get WhatsApp number
                phone_meta = WpUsermeta.objects.filter(
                    user_id=user_id,
                    meta_key='waid'
                ).first()
                
                if not phone_meta or not phone_meta.meta_value:
                    logger.warning(f"No WhatsApp number found for user {user_id}")
                    results.append({
                        'user_id': user_id,
                        'user_name': user_name,
                        'success': False,
                        'error': 'No WhatsApp number found'
                    })
                    failed_count += 1
                    continue
                
                to_number = phone_meta.meta_value
                if not to_number.startswith('+'):
                    to_number = f'+{to_number}'
                
                # Reset user state
                logger.info(f"Resetting user state for user_id: {user_id}")
                reset_user_state(user_id, course_id)
                
                # Send introduction message
                initial_state = {
                    'course_id': str(course_id),
                    'message_id': 'm-1',
                    'step': 'course_selection',
                    'language': None,
                    'user_id': user_id
                }
                
                result = send_next_message_by_id(
                    from_number=to_number,
                    user_name=user_name,
                    message_id='m-1',
                    course_data=message_data,
                    current_state=initial_state,
                    language=None
                )
                
                if result.get('success'):
                    # Update user state with the result
                    if result.get('next_state'):
                        update_user_state(user_id, result['next_state'])
                    
                    success_count += 1
                    results.append({
                        'user_id': user_id,
                        'user_name': user_name,
                        'phone_number': to_number,
                        'success': True,
                        'message_sid': result.get('message_sid', ''),
                        'current_message': 'm-1'
                    })
                    logger.info(f"Successfully sent introduction message to user {user_id}")
                else:
                    failed_count += 1
                    results.append({
                        'user_id': user_id,
                        'user_name': user_name,
                        'phone_number': to_number,
                        'success': False,
                        'error': result.get('error', 'Unknown error')
                    })
                    logger.error(f"Failed to send introduction message to user {user_id}: {result.get('error')}")
                
            except WpUsers.DoesNotExist:
                logger.warning(f"User {user_id} not found")
                results.append({
                    'user_id': user_id,
                    'success': False,
                    'error': 'User not found'
                })
                failed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {str(e)}")
                results.append({
                    'user_id': user_id,
                    'success': False,
                    'error': str(e)
                })
                failed_count += 1
        
        # Prepare response
        response_data = {
            'success': True,
            'message': f'Processed {len(group_users_meta)} users from group {group_id}',
            'group_id': group_id,
            'course_id': course_id,
            'course_name': course_name,
            'summary': {
                'total_users': len(group_users_meta),
                'success_count': success_count,
                'failed_count': failed_count,
                'success_rate': round((success_count / len(group_users_meta)) * 100, 2) if group_users_meta else 0
            },
            'results': results,
            'use_template': use_template
        }
        
        logger.info(f"Group introduction messages completed. Success: {success_count}, Failed: {failed_count}")
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in send_group_introduction_message: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'details': str(e),
            'group_id': group_id
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_groups(request, user_id):
    """Get all groups that a specific user belongs to"""
    try:
        # Find all meta_keys that start with 'learndash_group_users_' for this user
        user_group_meta = WpUsermeta.objects.filter(
            user_id=user_id,
            meta_key__startswith='learndash_group_users_'
        )
        
        if not user_group_meta.exists():
            return Response({
                'success': False,
                'message': f'User {user_id} is not assigned to any groups',
                'user_id': user_id,
                'groups': []
            }, status=404)
        
        # Get user details
        try:
            user = WpUsers.objects.get(id=user_id)
            user_info = {
                'user_id': user_id,
                'user_login': user.user_login,
                'user_email': user.user_email,
                'display_name': user.display_name,
                'user_registered': user.user_registered
            }
        except WpUsers.DoesNotExist:
            return Response({
                'success': False,
                'error': f'User with ID {user_id} not found'
            }, status=404)
        
        # Extract group information
        groups_data = []
        for meta in user_group_meta:
            # Extract group_id from meta_key
            group_id = meta.meta_key.replace('learndash_group_users_', '')
            
            # Get group details
            try:
                group = WpPosts.objects.get(id=group_id, post_type='groups')
                group_info = {
                    'group_id': group_id,
                    'group_name': group.post_title,
                    'group_status': group.post_status,
                    'created_date': group.post_date,
                    'meta_key': meta.meta_key,
                    'meta_value': meta.meta_value
                }
            except WpPosts.DoesNotExist:
                group_info = {
                    'group_id': group_id,
                    'group_name': 'Group not found',
                    'group_status': 'unknown',
                    'meta_key': meta.meta_key,
                    'meta_value': meta.meta_value,
                    'error': 'Group details not found'
                }
            
            groups_data.append(group_info)
        
        response_data = {
            'success': True,
            'message': f'User {user_id} belongs to {len(groups_data)} groups',
            'user_info': user_info,
            'total_groups': len(groups_data),
            'groups': groups_data
        }
        
        return Response(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Error getting user groups for user {user_id}: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve user groups',
            'details': str(e),
            'user_id': user_id
        }, status=500)
    



from .services.reminder_service import reminder_service

# Update the update_user_state function to trigger reminders
def update_user_state(user_id, next_state):
    """Update user's current state and handle reminders"""
    try:
        if not next_state:
            return

        # Format: course_id|message_id|step|language
        state_value = f"{next_state.get('course_id', '')}|{next_state.get('message_id', 'm-1')}|{next_state.get('step', 'start')}|{next_state.get('language', '')}"

        # Update or create user state
        user_meta, created = WpUsermeta.objects.update_or_create(
            user_id=user_id,
            meta_key='whatsapp_current_state',
            defaults={'meta_value': state_value}
        )

        logger.info(f"Updated user {user_id} state to: {state_value}")
        
        # IMPORTANT: Cancel any pending reminders when user is active
        course_id = next_state.get('course_id')
        if course_id and course_id != 'None':
            reminder_service.cancel_pending_reminders(user_id, course_id)
            logger.info(f"Cancelled pending reminders for active user {user_id}")
            
            # Schedule new reminders for future inactivity
            current_message_id = next_state.get('message_id', 'm-1')
            
            # Only schedule reminders if not completed
            if next_state.get('step') != 'completed':
                # Schedule 30-minute reminder
                logger.info(f"Scheduling 30-minute reminder for user {user_id}, course {course_id}, message {current_message_id}")
                reminder_service.schedule_30_minute_reminder(user_id, course_id, current_message_id)
                
                # Schedule first 6-hour reminder
                reminder_service.schedule_6_hour_reminder(user_id, course_id, current_message_id, 0)

    except Exception as e:
        logger.error(f"Error updating user state: {str(e)}")

# Add new API endpoints for reminder management

@api_view(['POST'])
@permission_classes([AllowAny])
def send_admin_reminder(request):
    """Send admin-triggered reminder to specific users"""
    try:
        user_ids = request.data.get('user_ids', [])
        course_id = request.data.get('course_id')
        admin_user_id = request.data.get('admin_user_id')
        custom_message = request.data.get('custom_message', '')
        
        if not user_ids or not course_id or not admin_user_id:
            return Response({
                'error': 'user_ids, course_id, and admin_user_id are required'
            }, status=400)
        
        logger.info(f"Admin {admin_user_id} sending reminder to {len(user_ids)} users for course {course_id}")
        
        results = reminder_service.send_admin_reminder(
            user_ids=user_ids,
            course_id=course_id,
            admin_user_id=admin_user_id,
            custom_message=custom_message if custom_message else None
        )
        
        success_count = len([r for r in results if r.get('success')])
        failed_count = len(results) - success_count
        
        return Response({
            'success': True,
            'message': f'Reminders sent to {success_count} users, {failed_count} failed',
            'results': results,
            'summary': {
                'total_users': len(user_ids),
                'success_count': success_count,
                'failed_count': failed_count
            }
        })
        
    except Exception as e:
        logger.error(f"Error in send_admin_reminder: {e}")
        return Response({
            'error': 'Failed to send admin reminders',
            'details': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_reminder_statistics(request):
    """Get reminder statistics"""
    try:
        days = int(request.GET.get('days', 7))
        stats = reminder_service.get_reminder_statistics(days)
        
        return Response({
            'success': True,
            'statistics': stats,
            'period_days': days
        })
        
    except Exception as e:
        logger.error(f"Error getting reminder statistics: {e}")
        return Response({
            'error': 'Failed to get statistics',
            'details': str(e)
        }, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def cancel_user_reminders(request):
    """Cancel all pending reminders for a user"""
    try:
        user_id = request.data.get('user_id')
        course_id = request.data.get('course_id')
        
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)
        
        if course_id:
            cancelled = reminder_service.cancel_pending_reminders(user_id, course_id)
        else:
            cancelled = reminder_service.cancel_all_user_reminders(user_id)
        
        return Response({
            'success': True,
            'message': f'Cancelled {cancelled} pending reminders',
            'cancelled_count': cancelled
        })
        
    except Exception as e:
        logger.error(f"Error cancelling reminders: {e}")
        return Response({
            'error': 'Failed to cancel reminders',
            'details': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_reminders(request, user_id):
    """Get reminder history for a specific user"""
    try:
        days = int(request.GET.get('days', 30))
        since_date = timezone.now() - datetime.timedelta(days=days)

        reminders = CourseReminderLog.objects.filter(
            user_id=user_id,
            created_at__gte=since_date
        ).order_by('-created_at')
        
        reminder_data = []
        for reminder in reminders:
            reminder_data.append({
                'id': reminder.id,
                'course_id': reminder.course_id,
                'course_name': reminder.course_name,
                'reminder_type': reminder.reminder_type,
                'scheduled_time': reminder.scheduled_time,
                'sent_time': reminder.sent_time,
                'status': reminder.status,
                'reminder_count': reminder.reminder_count,
                'triggered_by': reminder.triggered_by,
                'error_message': reminder.error_message,
                'created_at': reminder.created_at
            })
        
        return Response({
            'success': True,
            'user_id': user_id,
            'reminders': reminder_data,
            'total_count': len(reminder_data),
            'period_days': days
        })
        
    except Exception as e:
        logger.error(f"Error getting user reminders: {e}")
        return Response({
            'error': 'Failed to get user reminders',
            'details': str(e)
        }, status=500)

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def manage_reminder_settings(request):
    """Get or update reminder settings"""
    try:
        if request.method == 'GET':
            settings = CourseReminderSettings.objects.first()
            if not settings:
                reminder_service.ensure_default_settings()
                settings = CourseReminderSettings.objects.first()
            
            return Response({
                'success': True,
                'settings': {
                    'reminder_30_min_enabled': settings.reminder_30_min_enabled,
                    'reminder_6_hour_enabled': settings.reminder_6_hour_enabled,
                    'max_6_hour_reminders': settings.max_6_hour_reminders,
                    'dnd_start_time': settings.dnd_start_time,
                    'dnd_end_time': settings.dnd_end_time,
                    'created_at': settings.created_at,
                    'updated_at': settings.updated_at
                }
            })
        
        elif request.method == 'POST':
            settings = CourseReminderSettings.objects.first()
            if not settings:
                settings = CourseReminderSettings.objects.create()
            
            # Update settings
            if 'reminder_30_min_enabled' in request.data:
                settings.reminder_30_min_enabled = request.data['reminder_30_min_enabled']
            if 'reminder_6_hour_enabled' in request.data:
                settings.reminder_6_hour_enabled = request.data['reminder_6_hour_enabled']
            if 'max_6_hour_reminders' in request.data:
                settings.max_6_hour_reminders = request.data['max_6_hour_reminders']
            if 'dnd_start_time' in request.data:
                settings.dnd_start_time = request.data['dnd_start_time']
            if 'dnd_end_time' in request.data:
                settings.dnd_end_time = request.data['dnd_end_time']
            
            settings.save()
            
            return Response({
                'success': True,
                'message': 'Reminder settings updated successfully',
                'settings': {
                    'reminder_30_min_enabled': settings.reminder_30_min_enabled,
                    'reminder_6_hour_enabled': settings.reminder_6_hour_enabled,
                    'max_6_hour_reminders': settings.max_6_hour_reminders,
                    'dnd_start_time': settings.dnd_start_time,
                    'dnd_end_time': settings.dnd_end_time,
                    'updated_at': settings.updated_at
                }
            })
        
    except Exception as e:
        logger.error(f"Error managing reminder settings: {e}")
        return Response({
            'error': 'Failed to manage settings',
            'details': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_course_resume_reminder(request):
    """Send template-based resume reminder to specific users"""
    try:
        user_ids = request.data.get('user_ids', [])
        course_id = request.data.get('course_id')
        admin_user_id = request.data.get('admin_user_id')
        use_template = request.data.get('use_template', True)
        
        if not user_ids or not course_id:
            return Response({
                'error': 'user_ids and course_id are required'
            }, status=400)
        
        logger.info(f"Sending resume reminders to {len(user_ids)} users with template: {use_template}")
        
        results = []
        success_count = 0
        
        for user_id in user_ids:
            try:
                # Get user's current state
                current_state = get_user_current_state(user_id)
                current_message_id = current_state.get('message_id', 'm-1')
                
                # Get user info
                user_info = reminder_service._get_user_info(user_id)
                course_info = reminder_service._get_course_info(course_id)
                
                if not user_info or not course_info:
                    results.append({
                        'user_id': user_id,
                        'success': False,
                        'error': 'User or course not found'
                    })
                    continue
                
                if use_template:
                    # FIXED: Use shorter reminder type that fits the database column
                    reminder = CourseReminderLog.objects.create(
                        user_id=user_id,
                        course_id=course_id,
                        reminder_type='admin',  # Changed from 'admin_template' to 'admin'
                        message_id=current_message_id,
                        scheduled_time=timezone.now(),
                        phone_number=user_info['phone'],
                        user_name=user_info['name'],
                        course_name=course_info['name'],
                        triggered_by=f'admin_{admin_user_id}' if admin_user_id else 'system',
                        meta_data=json.dumps({
                            'admin_user_id': admin_user_id,
                            'use_template': True,  # Store template preference in meta_data
                            'template_method': 'resume_template',
                            'sent_immediately': True
                        })
                    )
                    
                    # Send template reminder
                    success = reminder_service.send_reminder_with_resume_template(reminder.id)
                else:
                    # Use regular reminder
                    success = reminder_service.send_admin_reminder([user_id], course_id, admin_user_id)
                    success = len([r for r in success if r.get('success')]) > 0
                
                results.append({
                    'user_id': user_id,
                    'success': success,
                    'method': 'template' if use_template else 'regular'
                })
                
                if success:
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"Error sending resume reminder to user {user_id}: {e}")
                results.append({
                    'user_id': user_id,
                    'success': False,
                    'error': str(e)
                })
        
        return Response({
            'success': True,
            'message': f'Resume reminders processed for {len(user_ids)} users',
            'summary': {
                'total_users': len(user_ids),
                'success_count': success_count,
                'failed_count': len(user_ids) - success_count,
                'use_template': use_template
            },
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error in send_course_resume_reminder: {e}")
        return Response({
            'error': 'Failed to send resume reminders',
            'details': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_users_needing_reminders(request):
    """Get list of users who haven't completed courses and might need reminders"""
    try:
        # Get users who have started but not completed courses
        from django.db.models import Q
        from datetime import datetime, timedelta
        
        # Look for users with incomplete courses (not at 'completed' step)
        incomplete_users = WpUsermeta.objects.filter(
            meta_key='whatsapp_current_state'
        ).exclude(
            meta_value__contains='|completed|'
        ).exclude(
            meta_value__contains='|m-1|'  # Exclude those who just started
        )
        
        user_data = []
        
        for user_meta in incomplete_users:
            try:
                # Parse user state
                state_parts = user_meta.meta_value.split('|')
                course_id = state_parts[0] if len(state_parts) > 0 else None
                message_id = state_parts[1] if len(state_parts) > 1 else 'm-1'
                step = state_parts[2] if len(state_parts) > 2 else 'start'
                
                if not course_id or course_id == 'None':
                    continue
                
                # Get user info
                user = WpUsers.objects.get(id=user_meta.user_id)
                phone_meta = WpUsermeta.objects.filter(
                    user_id=user_meta.user_id,
                    meta_key='waid'
                ).first()
                
                if not phone_meta:
                    continue
                
                # Get course info
                course = WpPosts.objects.filter(
                    id=course_id,
                    post_type='sfwd-courses'
                ).first()
                
                if not course:
                    continue
                
                # Get progress info
                progress_info = reminder_service._get_user_progress_info(
                    user_meta.user_id, course_id, message_id
                )
                
                user_data.append({
                    'user_id': user_meta.user_id,
                    'user_name': user.display_name or user.user_nicename,
                    'phone_number': phone_meta.meta_value,
                    'course_id': course_id,
                    'course_name': course.post_title,
                    'current_message_id': message_id,
                    'current_step': step,
                    'progress_percentage': progress_info.get('progress_percentage', 0),
                    'lesson_name': progress_info.get('lesson_name', 'Unknown'),
                    'completed_lessons': progress_info.get('completed_lessons', 0),
                    'total_lessons': progress_info.get('total_lessons', 0)
                })
                
            except Exception as e:
                logger.error(f"Error processing user {user_meta.user_id}: {e}")
                continue
        
        return Response({
            'success': True,
            'total_users': len(user_data),
            'users': user_data
        })
        
    except Exception as e:
        logger.error(f"Error getting users needing reminders: {e}")
        return Response({
            'error': 'Failed to get users needing reminders',
            'details': str(e)
        }, status=500)