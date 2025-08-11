import jwt
import time
import hashlib
import secrets
from django.conf import settings
from django.core.cache import cache
import logging
import json
import traceback

logger = logging.getLogger(__name__)

class SecureVideoService:
    def __init__(self):
        self.secret_key = getattr(settings, 'VIDEO_SECURITY_KEY', 'your-secret-key-change-this')
        self.base_url = getattr(settings, 'SECURE_VIDEO_BASE_URL', 'https://yourdomain.com/secure-video')
    
    def generate_secure_video_url(self, video_url, user_id, lesson_id, expires_in=7200):
        """Generate a secure, time-limited video URL"""
        try:
            logger.info(f"🔐 Generating secure URL for user {user_id}, lesson {lesson_id}")
            
            # Generate unique session token
            session_token = secrets.token_urlsafe(32)
            logger.info(f"Generated session token: {session_token[:20]}...")
            
            # Create payload for JWT
            payload = {
                'video_url': video_url,
                'user_id': user_id,
                'lesson_id': lesson_id,
                'session_token': session_token,
                'exp': int(time.time()) + expires_in,
                'iat': int(time.time()),
                'max_views': 10  # Allow multiple views
            }
            
            # Create JWT token
            token = jwt.encode(payload, self.secret_key, algorithm='HS256')
            logger.info(f"JWT token created: {token[:50]}...")
            
            # Store session info in cache
            cache_key = f"video_session_{user_id}_{lesson_id}_{session_token}"
            cache_data = {
                'token': token,
                'viewed': False,
                'access_count': 0,
                'created_at': time.time(),
                'user_agent': None,
                'video_url': video_url,
                'user_id': user_id,
                'lesson_id': lesson_id,
                'session_token': session_token
            }
            
            # Use longer timeout and log the operation
            cache_timeout = expires_in
            logger.info(f"Setting cache with key: {cache_key}")
            logger.info(f"Cache timeout: {cache_timeout} seconds")
            
            # Set cache with retry mechanism
            cache_set_success = False
            for attempt in range(3):
                try:
                    cache.set(cache_key, cache_data, timeout=cache_timeout)
                    
                    # Immediately verify cache was set
                    cached_data = cache.get(cache_key)
                    if cached_data:
                        logger.info(f"✅ Cache set successfully on attempt {attempt + 1}")
                        cache_set_success = True
                        break
                    else:
                        logger.warning(f"❌ Cache verification failed on attempt {attempt + 1}")
                        time.sleep(0.5)  # Wait before retry
                except Exception as e:
                    logger.error(f"Cache set attempt {attempt + 1} failed: {e}")
                    time.sleep(0.5)
            
            if not cache_set_success:
                logger.error(f"❌ Failed to set cache after 3 attempts")
                return None
            
            # Also store a backup copy with just user_id and lesson_id
            backup_cache_key = f"video_backup_{user_id}_{lesson_id}"
            cache.set(backup_cache_key, {
                'session_token': session_token,
                'token': token,
                'video_url': video_url,
                'created_at': time.time(),
                'primary_cache_key': cache_key
            }, timeout=cache_timeout)
            logger.info(f"✅ Backup cache set with key: {backup_cache_key}")
            
            # Generate secure URL
            secure_url = f"{self.base_url}?token={token}"
            
            logger.info(f"✅ Generated secure video URL successfully")
            return secure_url
            
        except Exception as e:
            logger.error(f"❌ Error generating secure video URL: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def validate_video_access(self, token, user_agent=None):
        """Validate video access token with fallback mechanisms"""
        try:
            logger.info(f"🔍 Validating video access token: {token[:50]}...")
            
            # Decode JWT token
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            user_id = payload.get('user_id')
            lesson_id = payload.get('lesson_id')
            session_token = payload.get('session_token')

            logger.info(f"Token payload - user_id: {user_id}, lesson_id: {lesson_id}")
            logger.info(f"Session token: {session_token[:20]}...")
            
            # Primary cache lookup
            cache_key = f"video_session_{user_id}_{lesson_id}_{session_token}"
            logger.info(f"Looking for primary cache key: {cache_key}")
            
            session_info = cache.get(cache_key)
            
            # If primary cache miss, try backup cache
            if not session_info:
                logger.warning(f"❌ Primary cache miss, trying backup cache")
                
                backup_cache_key = f"video_backup_{user_id}_{lesson_id}"
                backup_info = cache.get(backup_cache_key)
                
                if backup_info and backup_info.get('session_token') == session_token:
                    logger.info(f"✅ Found backup cache, recreating session")
                    
                    # Recreate session info from backup
                    session_info = {
                        'token': backup_info.get('token'),
                        'viewed': False,
                        'access_count': 0,
                        'created_at': backup_info.get('created_at'),
                        'user_agent': user_agent,
                        'video_url': backup_info.get('video_url'),
                        'user_id': user_id,
                        'lesson_id': lesson_id,
                        'session_token': session_token
                    }
                    
                    # Restore primary cache
                    cache.set(cache_key, session_info, timeout=7200)
                    logger.info(f"✅ Restored primary cache from backup")
                else:
                    logger.error(f"❌ Backup cache also failed")
            
            # If still no session info, create a new one (fallback)
            if not session_info:
                logger.warning(f"⚠️ No cache found, creating emergency session")
                
                # This is a fallback - allow access but log the incident
                session_info = {
                    'token': token,
                    'viewed': False,
                    'access_count': 0,
                    'created_at': time.time(),
                    'user_agent': user_agent,
                    'video_url': payload.get('video_url'),
                    'user_id': user_id,
                    'lesson_id': lesson_id,
                    'session_token': session_token,
                    'emergency_created': True
                }
                
                # Set both primary and backup cache
                cache.set(cache_key, session_info, timeout=7200)
                backup_cache_key = f"video_backup_{user_id}_{lesson_id}"
                cache.set(backup_cache_key, {
                    'session_token': session_token,
                    'token': token,
                    'video_url': payload.get('video_url'),
                    'created_at': time.time(),
                    'primary_cache_key': cache_key
                }, timeout=7200)
                
                logger.info(f"✅ Emergency session created")
            
            logger.info(f"✅ Session found/created in cache")
            
            # Update access count
            access_count = session_info.get('access_count', 0) + 1
            session_info['access_count'] = access_count
            session_info['last_accessed'] = time.time()
            
            # Update user agent if provided
            if user_agent and not session_info.get('user_agent'):
                session_info['user_agent'] = user_agent
            
            # Allow multiple accesses but limit to prevent abuse
            if access_count > 15:
                logger.warning(f"Too many access attempts ({access_count}) for user {user_id}")
                return {'valid': False, 'error': 'Too many access attempts'}
            
            # Update cache with new access info
            cache.set(cache_key, session_info, timeout=7200)
            
            logger.info(f"✅ Access validated successfully (attempt #{access_count})")
            
            return {
                'valid': True,
                'video_url': payload.get('video_url'),
                'user_id': user_id,
                'lesson_id': lesson_id,
                'session_token': session_token,
                'access_count': access_count,
                'emergency_session': session_info.get('emergency_created', False)
            }
            
        except jwt.ExpiredSignatureError:
            logger.error("❌ JWT token expired")
            return {'valid': False, 'error': 'Video access expired'}
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ Invalid JWT token: {str(e)}")
            return {'valid': False, 'error': 'Invalid access token'}
        except Exception as e:
            logger.error(f"❌ Error validating video access: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'valid': False, 'error': 'Access validation failed'}

    def check_security_violations(self, user_id, lesson_id):
        """Check if user has security violations"""
        try:
            from ..models import WpUsermeta
            violations = WpUsermeta.objects.filter(
                user_id=user_id,
                meta_key__startswith='security_incident_'
            ).count()
            
            if violations > 5:  # More than 5 violations
                logger.warning(f"User {user_id} has {violations} security violations")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking security violations: {str(e)}")
            return False
        



    def generate_one_time_drm_link(video_url, otp, playback_info, user_id=None, expires_in=3600):
        logger.info(f"🔐 Generating one-time DRM link for user {user_id}...")
        # Ensure expires_in is an int
        expires_in = int(expires_in) if expires_in is not None else 3600
        import secrets
        token = secrets.token_urlsafe(32)
        logger.info(f"🔐 Generating one-time DRM link with token: {token[:20]}...")
        cache.set(f"drm_token_{token}", {
            "otp": otp,
            "playback_info": playback_info,
            "viewed": False,
            "user_id": user_id
        }, timeout=expires_in)
        cached_data = cache.get(f"drm_token_{token}")
        logger.info(f"Caching token {token}, retrieved after set: {cached_data}")
        return f"https://embyte-learn.com/django/api/drm-video/?token={token}"
        
    def mark_video_viewed(self, token):
        """Mark video as viewed"""
        try:
            logger.info(f"📝 Marking video as viewed")
            
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            lesson_id = payload.get('lesson_id')
            session_token = payload.get('session_token')
            
            # Update cache to mark as viewed
            cache_key = f"video_session_{user_id}_{lesson_id}_{session_token}"
            session_info = cache.get(cache_key)
            
            if session_info:
                session_info['viewed'] = True
                session_info['viewed_at'] = time.time()
                cache.set(cache_key, session_info, timeout=7200)
                
                # Store in database for permanent record
                try:
                    from ..models import WpUsermeta
                    WpUsermeta.objects.update_or_create(
                        user_id=user_id,
                        meta_key=f'video_viewed_{lesson_id}',
                        defaults={
                            'meta_value': json.dumps({
                                'viewed_at': time.time(),
                                'session_token': session_token,
                                'access_count': session_info.get('access_count', 1)
                            })
                        }
                    )
                    logger.info(f"✅ Video view recorded for user {user_id}, lesson {lesson_id}")
                except Exception as e:
                    logger.warning(f"Could not store video view record: {e}")
                
                return True
            else:
                logger.error(f"❌ Session not found when marking as viewed")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error marking video as viewed: {str(e)}")
            return False
        




# Create global instance
secure_video_service = SecureVideoService()



