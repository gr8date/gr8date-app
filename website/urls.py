# urls.py - COMPLETE WITH ALL WORKING URLS + LEGAL COMPLIANCE
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Basic pages
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('join/', views.join, name='join'),
    path('login/', views.login_page, name='login'),
    
    # Authentication
    path('logout/', auth_views.LogoutView.as_view(template_name='website/logged_out.html'), name='logout'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset-sent/', views.password_reset_sent, name='password_reset_sent'),    
    
    # Profile
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<int:user_id>/', views.profile_detail, name='profile_detail_legacy'),  # CHANGED NAME

    # Profile detail pages
    path('profile/<int:profile_id>/public/', views.profile_detail_public, name='profile_detail_public'),
    path('member/profile/<int:profile_id>/', views.profile_detail_member, name='profile_detail_member'),
    path('view-profile/<int:profile_id>/', views.profile_detail_redirect, name='profile_detail'),  # MAIN ENTRY POINT
    
    # Private Access Request - NEW
    path('request-private-access/<int:user_id>/', views.request_private_access, name='request_private_access'),
    path('member/request-private-access/<int:user_id>/', views.request_private_access, name='request_private_access'),
    path('api/private-access/request/<int:user_id>/', views.request_private_access, name='request_private_access_api'),
    
    # Messaging
    path('messages/', views.messages_list, name='messages_list'),
    path('messages/<int:user_id>/', views.message_detail, name='message_detail'),
    path('messages/thread/<int:user_id>/', views.message_detail, name='message_thread'),
    
    # LEGAL COMPLIANCE: Message deletion (soft delete only)
    path('api/message/delete/<int:message_id>/', views.delete_message, name='delete_message'),
    
    # Profile creation flow
    path('create-profile/', views.create_profile, name='create_profile'),
    path('create-profile/step1/', views.create_profile_step1, name='create_profile_step1'),
    path('create-profile/step2/', views.create_profile_step2, name='create_profile_step2'),
    path('create-profile/step3/', views.create_profile_step3, name='create_profile_step3'),
    path('create-profile/step4/', views.create_profile_step4, name='create_profile_step4'),
    path('join-success/', views.join_success, name='join_success'),
    
    # Matches & Dates
    path('matches/', views.matches_list, name='matches_list'),
    path('dates/', views.dates_list, name='dates_list'),
    path('dates/create/', views.dates_create, name='dates_create'),
    
    # Blog
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blog_post, name='blog_post'),
    
    # Marketing pages
    path('discover-elite-members/', views.discover, name='discover'),
    path('events/', views.events, name='events'),
    path('success-stories/', views.success_stories, name='success_stories'),
    path('about-us/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    
    # Legal pages
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('safety/', views.safety_center, name='safety'),
    path('trust-safety/', views.trust, name='trust'),
    
    # Help & Support
    path('help-center/', views.help_center, name='help_center'),
    path('faq/', views.faq, name='faq'),
    path('premium/', views.premium, name='premium'),
    path('help/', views.help_center, name='help'),

    # AJAX endpoints
    path('check-username/', views.check_username, name='check_username'),
    path('api/messages/unread-count/', views.messages_unread_count, name='messages_unread_count'),
    path('api/dates/new-count/', views.dates_new_count, name='dates_new_count'),
    
    # NEW: Combined notification counts endpoint
    path('api/notification-counts/', views.notification_counts, name='notification_counts'),
    
    # Likes & Matches API endpoints
    path('api/like/<int:user_id>/', views.like_profile, name='like_profile'),
    path('api/favorite/<int:user_id>/', views.favorite_profile, name='favorite_profile'),
    path('api/block/<int:user_id>/', views.block_profile, name='block_profile'),
    path('api/unblock/<int:user_id>/', views.unblock_profile, name='unblock_profile'),
    path('api/user-likes/', views.get_user_likes_data, name='user_likes_data'),
    path('api/likes-counts/', views.get_likes_counts, name='likes_counts'),
    path('api/mark-matches-viewed/', views.mark_matches_viewed, name='mark_matches_viewed'),
    
    # Individual notification viewing triggers
    path('api/like/viewed/<int:user_id>/', views.mark_like_viewed, name='mark_like_viewed'),
    path('api/mutual-match/viewed/<int:user_id>/', views.mark_mutual_match_viewed, name='mark_mutual_match_viewed'),
    
    # Messaging endpoints
    path('api/message/send/<int:user_id>/', views.send_message, name='send_message'),
    path('api/conversation/viewed/<int:user_id>/', views.mark_conversation_viewed, name='mark_conversation_viewed'),

    # Dates URLs
    path('dates/<int:dates_id>/mark-seen/', views.mark_date_seen, name='mark_date_seen'),
    path('dates/<int:dates_id>/cancel/', views.cancel_date, name='cancel_date'),
    
    # Profile Edit System URLs
    path('api/profile/edit-request/', views.profile_edit_request, name='profile_edit_request'),
    
    # LEGAL COMPLIANCE: Data export endpoints (Admin only)
    path('api/legal/export-user-data/', views.export_user_data, name='export_user_data'),
    path('api/legal/export-user-data/<int:user_id>/', views.export_user_data, name='export_user_data_detail'),
    
    # Private Access Management URLs - NEW
    path('api/private-access/request/<int:user_id>/', views.request_private_access, name='request_private_access_api'),
    path('api/private-access/check/<int:user_id>/', views.check_private_access_status, name='check_private_access_status'),
    path('api/private-access/grant/<int:request_id>/', views.grant_private_access, name='grant_private_access'),
    path('api/private-access/revoke/<int:user_id>/', views.revoke_private_access, name='revoke_private_access'),
    
    # Redirect for old URLs (keep compatibility)
    path('discover/', RedirectView.as_view(pattern_name='discover', permanent=True)),
    path('about/', RedirectView.as_view(pattern_name='about', permanent=True)),
    path('safety-guidelines/', RedirectView.as_view(pattern_name='safety', permanent=True)),
    path('trust-safety/', RedirectView.as_view(pattern_name='safety', permanent=True)),
    path('help/', RedirectView.as_view(pattern_name='help_center', permanent=True)),
]
