# utils.py
import requests
import json
from datetime import timedelta
from django.utils import timezone
from .models import OneTimeVideoToken

def get_vdocipher_otp_and_playbackinfo(video_id):
    url = f'https://www.vdocipher.com/api/videos/{video_id}/otp'
    headers = {'Authorization': 'Apisecret LoN6sVjiUrFfN4l9PHQZdXbGPEoAZN0EYd745NH74OiMzm04QzeKSrtL25k6FG4c'}
    body = {
        "ttl": 600,  # 10 minutes validity
        "forcedBitrate": 0,
        "annotate": [],
        "nocdn": 0,
        "whitelisthref": "",
        "ipGeoRules": ""
    }
    res = requests.post(url, data=json.dumps(body), headers=headers, timeout=10)
    res.raise_for_status()
    data = res.json()
    return data['otp'], data['playbackInfo']

def create_one_time_video_token(video_id, user_phone=None, ttl_hours=24):
    """Create a one-time use token for video access"""
    expires_at = timezone.now() + timedelta(hours=ttl_hours)
    
    token = OneTimeVideoToken.objects.create(
        video_id=video_id,
        user_phone=user_phone,
        expires_at=expires_at
    )
    
    return token
