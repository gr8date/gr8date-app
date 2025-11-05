# pages/urls.py
from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # Core Pages
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # ======================
    # REMOVED ADMIN URLS - THEY ARE NOW IN core/urls.py
    # ======================

    # ======================
    # PASSWORD RESET - COMPLETE ROUTES
    # ======================
    path('password-reset/', views.custom_password_reset, name='custom_password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset-password-confirm/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset-password-complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # ======================
    # STATIC PAGES - CORRECTED TEMPLATE NAMES
    # ======================
    path('about/', TemplateView.as_view(template_name='pages/aboutus.html'), name='about'),
    path('privacy/', TemplateView.as_view(template_name='pages/privacy.html'), name='privacy'),
    path('terms/', TemplateView.as_view(template_name='pages/terms.html'), name='terms'),
    path('faq/', TemplateView.as_view(template_name='pages/faq.html'), name='faq'),
    path('contact/', TemplateView.as_view(template_name='pages/contact.html'), name='contact'),

    # ======================
    # PREVIEW USE - START (NEW ROUTES)
    # ======================
    path('join/', views.join_view, name='join'),
    path('preview-gate/', views.preview_gate, name='preview_gate'),
    path('browse-preview/', views.browse_preview, name='browse_preview'),
    # ======================
    # PREVIEW USE - END
    # ======================

    # Profile Management
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<int:user_id>/', views.profile_detail, name='profile_detail'),

    # Search & Discovery
    path('search/', views.search, name='search'),

    # Likes & Matching
    path('like/<int:user_id>/', views.like_user, name='like_user'),
    path('unfavorite/<int:user_id>/', views.unfavorite_user, name='unfavorite_user'),
    path('likes/received/', views.likes_received, name='likes_received'),
    path('likes/given/', views.likes_given, name='likes_given'),
    path('matches/', views.matches_list, name='matches_list'),

    # Messaging - FIXED: Changed name to match template
    path('messages/', views.messages_combined, name='messages_list'),  # CHANGED NAME
    path('messages/<int:user_id>/', views.message_thread, name='message_thread'),
    path('send-message/<int:user_id>/', views.send_quick_message, name='send_quick_message'),
    path('messages/delete-conversation/<int:thread_id>/', views.delete_conversation, name='delete_conversation'),
    path('messages/unread-count/', views.messages_unread_count, name='messages_unread_count'),

    # Hot Dates - ENHANCED WITH CANCELLATION
    path('hotdates/', views.hotdate_list, name='hotdate_list'),
    path('hotdates/create/', views.hotdate_create, name='hotdate_create'),
    path('hotdates/<int:hotdate_id>/', views.hotdate_detail, name='hotdate_detail'),
    path('hotdates/new-count/', views.hotdates_new_count, name='hotdates_new_count'),
    path('hotdates/<int:hotdate_id>/mark-seen/', views.hotdate_mark_seen, name='hotdate_mark_seen'),
    path('hotdates/<int:hotdate_id>/cancel/', views.hotdate_cancel, name='hotdate_cancel'),
    path('hotdates/notification/<int:notification_id>/mark-read/', views.hotdate_notification_mark_read, name='hotdate_notification_mark_read'),

    # Private Photo Access
    path('request-private-access/<int:user_id>/', views.request_private_access, name='request_private_access'),
    path('approve-private-access/<int:request_id>/', views.approve_private_access, name='approve_private_access'),
    path('deny-private-access/<int:request_id>/', views.deny_private_access, name='deny_private_access'),
    path('pending-requests/', views.pending_requests, name='pending_requests'),

    # Blog
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),

    # Blocking
    path('block/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock/<int:user_id>/', views.unblock_user, name='unblock_user'),

    # Images
    # ✅ FIXED (USE EXISTING FUNCTION):
    path('delete-image/<int:image_id>/', views.delete_image_api, name='delete_image'),    
    
# Create Profile
    path('create-profile/', views.create_profile, name='create_profile'),
    path('check-username/', views.check_username, name='check_username'),
    
    # Preview profile
    path('preview-profile/<int:user_id>/', views.preview_profile_detail, name='preview_profile_detail'),
    
    # API endpoints (CRITICAL - your frontend calls these)
    path('api/upload-profile-image/', views.upload_profile_image_api, name='upload_profile_image_api'),
    path('api/delete-image/<int:image_id>/', views.delete_image_api, name='delete_image_api'),
    path('api/create-profile/', views.create_profile_api, name='create_profile_api'),

    # Activity Tracking
    path('track-activity/<str:activity_type>/', views.track_activity, name='track_activity'),

    # Email Verification
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
]
