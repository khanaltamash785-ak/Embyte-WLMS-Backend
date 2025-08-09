from django.urls import path, re_path
from .views import (
    CustomProviderAuthView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CustomTokenVerifyView,
    LogoutView,
    get_users_needing_reminders,
    send_course_resume_reminder,
    send_introduction_message,
    secure_video_view,
    validate_video_access,
    mark_video_viewed,
    WhatsAppWebhookView,
    debug_video_cache,
    get_user_progress_report, get_all_users_progress_report,
    get_comprehensive_user_analytics, get_detailed_course_report,
    get_learning_analytics_dashboard,
    get_all_users, get_all_courses,
    vdocipher_drm_player,
    drm_video_view,
    get_all_groups, get_groups_summary, get_group_by_id,
    get_group_users, send_group_introduction_message,
    get_user_groups,
    send_admin_reminder, get_reminder_statistics,
    cancel_user_reminders, get_user_reminders,
    manage_reminder_settings

)

urlpatterns = [
    re_path(
        r'^o/(?P<provider>\S+)/$',
        CustomProviderAuthView.as_view(),
        name='provider-auth'
    ),
    path('jwt/create/', CustomTokenObtainPairView.as_view()),
    path('jwt/refresh/', CustomTokenRefreshView.as_view()),
    path('jwt/verify/', CustomTokenVerifyView.as_view()),
    path('logout/', LogoutView.as_view()),

    # WhatsApp endpoints
    path('whatsapp/introduction/', send_introduction_message,
         name='send_introduction'),
    path('whatsapp-webhook/', WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),  # Use class-based view


    path('secure-video/', secure_video_view, name='secure_video'),
    path('validate-video-access/', validate_video_access,
         name='validate_video_access'),
    path('mark-video-viewed/', mark_video_viewed, name='mark_video_viewed'),

    path('debug-video-cache/', debug_video_cache, name='debug_video_cache'),

    path('users/<int:user_id>/progress/', get_user_progress_report, name='user-progress-report'),
    path('users/progress/', get_user_progress_report, name='current-user-progress-report'),
    path('userss/progress-report/', get_all_users_progress_report, name='all-users-progress-report'),

    path('client-analytics/<int:user_id>/', get_comprehensive_user_analytics, name='comprehensive-user-analytics'),
    path('course-report/<int:course_id>/', get_detailed_course_report, name='detailed-course-report'),
    path('learning-analytics-dashboard/', get_learning_analytics_dashboard, name='learning-analytics-dashboard'),


    path('users-data/', get_all_users, name='get_all_users'),
    path('courses-data/', get_all_courses, name='get_all_courses'),


    # VdoCipher DRM Player
    path('vdocipher-drm/', vdocipher_drm_player, name='vdocipher_drm_player'),
    path('drm-video/', drm_video_view, name='drm_video_view'),


    # Groups endpoints
    path('groups/', get_all_groups, name='get_all_groups'),
    path('groups/summary/', get_groups_summary, name='get_groups_summary'),
    path('groups/<int:group_id>/', get_group_by_id, name='get_group_by_id'),


    # Group-User relationship endpoints
    path('groups/<int:group_id>/users/', get_group_users, name='get_group_users'),
    path('groups/<int:group_id>/send-introduction/', send_group_introduction_message, name='send_group_introduction_message'),
    path('users/<int:user_id>/groups/', get_user_groups, name='get_user_groups'),
    
    path('reminders/send-admin/', send_admin_reminder, name='send_admin_reminder'),
    path('reminders/statistics/', get_reminder_statistics, name='get_reminder_statistics'),
    path('reminders/cancel/', cancel_user_reminders, name='cancel_user_reminders'),
    path('reminders/user/<int:user_id>/', get_user_reminders, name='get_user_reminders'),
    path('reminders/settings/', manage_reminder_settings, name='manage_reminder_settings'),
    # path('whatsapp/welcome-template/', send_welcome_template, name='send_welcome_template'),

    # Add these to your urlpatterns
    path('send-course-resume-reminder/', send_course_resume_reminder, name='send_course_resume_reminder'),
    path('get-users-needing-reminders/', get_users_needing_reminders, name='get_users_needing_reminders'),
    
    
]
