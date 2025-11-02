# pages/admin.py
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.db import models
from django.urls import path, reverse
from django.shortcuts import render
from django.utils.html import format_html
from . import views
from .models import (
    Profile, Message, Thread, Like, Block, PrivateAccessRequest,
    HotDate, HotDateView, HotDateNotification, Blog, UserActivity, 
    ProfileImage, AdminMessage
)

# ✅ SAFE CUSTOM ADMIN URLS (without breaking Django admin)
def get_admin_urls():
    urls = [
        path('new-signups/', admin.site.admin_view(views.admin_new_signups), name='admin_new_signups'),
        path('send-message/<int:profile_id>/', admin.site.admin_view(views.admin_send_message), name='admin_send_message'),
    ]
    return urls

# ✅ SAFE: Add custom URLs to existing admin site
original_get_urls = admin.site.get_urls

def custom_get_urls():
    return get_admin_urls() + original_get_urls()

admin.site.get_urls = custom_get_urls

# ✅ ADD CUSTOM LINKS TO ADMIN INDEX
class CustomAdminSite(admin.AdminSite):
    def get_app_list(self, request):
        """Add custom links to the admin index"""
        app_list = super().get_app_list(request)
        
        # Only show these links to staff users
        if request.user.is_staff:
            # Create custom section for GR8DATE Admin Tools
            custom_app = {
                'name': '🚀 GR8DATE Admin',
                'app_label': 'gr8date_admin',
                'app_url': '/admin/new-signups/',
                'has_module_perms': True,
                'models': [
                    {
                        'name': '📊 All User Signups',
                        'object_name': 'new_signups',
                        'admin_url': '/admin/new-signups/',
                        'view_only': True,
                    },
                    {
                        'name': '📝 Quick Profile Approvals', 
                        'object_name': 'profile_approvals',
                        'admin_url': '/admin/approvals/',
                        'view_only': True,
                    },
                    {
                        'name': '🆕 New Profiles Review',
                        'object_name': 'new_profiles',
                        'admin_url': '/admin/new-profiles/',
                        'view_only': True,
                    },
                ],
            }
            app_list.append(custom_app)
        
        return app_list

# ✅ SAFE: Apply custom admin site without replacing
admin.site.__class__ = CustomAdminSite

# ✅ FIXED: ProfileInline with fk_name to resolve multiple ForeignKey issue
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ('headline', 'location', 'is_approved', 'email_verified', 'approval_status')

# Extend User Admin
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

# Model Admins
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'headline', 'location', 'is_approved', 'email_verified', 'approval_status', 'created_at', 'admin_actions')
    list_filter = ('is_approved', 'email_verified', 'approval_status', 'my_gender', 'looking_for', 'created_at')
    search_fields = ('user__username', 'headline', 'location', 'about')
    readonly_fields = ('created_at', 'updated_at', 'email_verification_token', 'email_verification_sent_at')
    actions = ['approve_profiles', 'reject_profiles', 'mark_as_verified', 'mark_pending_review']

    def admin_actions(self, obj):
        """Add quick action links to profile list"""
        return format_html(
            '<a href="/admin/send-message/{}/" class="button">📝 Message</a> '
            '<a href="/admin/approve-profile/{}/" class="button">✅ Approve</a>',
            obj.id, obj.id
        )
    admin_actions.short_description = 'Quick Actions'

    def approve_profiles(self, request, queryset):
        queryset.update(is_approved=True, approval_status='approved')
    approve_profiles.short_description = "Approve selected profiles"

    def reject_profiles(self, request, queryset):
        queryset.update(is_approved=False, approval_status='rejected')
    reject_profiles.short_description = "Reject selected profiles"

    def mark_as_verified(self, request, queryset):
        queryset.update(email_verified=True)
    mark_as_verified.short_description = "Mark selected profiles as email verified"

    def mark_pending_review(self, request, queryset):
        queryset.update(approval_status='pending_review')
    mark_pending_review.short_description = "Mark selected profiles as pending review"

# ✅ FIXED: AdminMessageAdmin - removed invalid fields
@admin.register(AdminMessage)
class AdminMessageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'admin_user', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('profile__user__username', 'message')
    readonly_fields = ('created_at', 'resolved_at')
    fields = ('profile', 'admin_user', 'message', 'is_resolved', 'resolved_at', 'created_at')

@admin.register(ProfileImage)
class ProfileImageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'image', 'is_private', 'is_primary', 'created_at')
    list_filter = ('is_private', 'is_primary')
    search_fields = ('profile__user__username',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('thread', 'sender', 'recipient', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('text', 'sender__username', 'recipient__username')
    readonly_fields = ('created_at',)

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('user_a', 'user_b', 'created_at', 'updated_at')
    search_fields = ('user_a__username', 'user_b__username')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('liker', 'liked_user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('liker__username', 'liked_user__username')
    readonly_fields = ('created_at',)

@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('blocker__username', 'blocked__username')
    readonly_fields = ('created_at',)

@admin.register(PrivateAccessRequest)
class PrivateAccessRequestAdmin(admin.ModelAdmin):
    list_display = ('requester', 'target_user', 'status', 'created_at', 'reviewed_at')
    list_filter = ('status', 'created_at', 'reviewed_at')
    search_fields = ('requester__username', 'target_user__username')
    readonly_fields = ('created_at', 'reviewed_at')
    actions = ['approve_requests', 'deny_requests']

    def approve_requests(self, request, queryset):
        queryset.update(status='approved', reviewed_by=request.user, reviewed_at=timezone.now())
    approve_requests.short_description = "Approve selected requests"

    def deny_requests(self, request, queryset):
        queryset.update(status='denied', reviewed_by=request.user, reviewed_at=timezone.now())
    deny_requests.short_description = "Deny selected requests"

@admin.register(HotDate)
class HotDateAdmin(admin.ModelAdmin):
    list_display = ('host', 'activity', 'date_time', 'area', 'is_active', 'is_cancelled', 'created_at')
    list_filter = ('is_active', 'is_cancelled', 'date_time', 'created_at')
    search_fields = ('host__username', 'activity', 'area', 'vibe')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['activate_hotdates', 'deactivate_hotdates', 'cancel_hotdates']

    def activate_hotdates(self, request, queryset):
        queryset.update(is_active=True)
    activate_hotdates.short_description = "Activate selected Hot Dates"

    def deactivate_hotdates(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_hotdates.short_description = "Deactivate selected Hot Dates"

    def cancel_hotdates(self, request, queryset):
        queryset.update(is_cancelled=True)
    cancel_hotdates.short_description = "Cancel selected Hot Dates"

@admin.register(HotDateView)
class HotDateViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'hot_date', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('user__username', 'hot_date__activity')
    readonly_fields = ('viewed_at',)

@admin.register(HotDateNotification)
class HotDateNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'hot_date', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'hot_date__activity', 'message')
    readonly_fields = ('created_at', 'read_at')
    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, read_at=timezone.now())
    mark_as_read.short_description = "Mark selected notifications as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
    mark_as_unread.short_description = "Mark selected notifications as unread"

# ENHANCED BlogAdmin with DRAG & DROP ordering - FIXED
@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ['title', 'position', 'status', 'published_at', 'is_published', 'created_at']
    list_editable = ['position', 'status']
    list_display_links = ['title']
    list_filter = ['status', 'published_at', 'created_at']
    search_fields = ['title', 'content', 'summary', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    ordering = ['-position', '-published_at']
    fieldsets = (
        ('Basic Information', {'fields': ('title', 'slug', 'summary', 'excerpt')}),
        ('Content', {'fields': ('content', 'hero_image')}),
        ('Publication & Ordering', {'fields': ('status', 'published_at', 'position')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)})
    )
    readonly_fields = ('created_at', 'updated_at')
    actions = ['publish_posts', 'unpublish_posts', 'mark_as_draft', 'set_published_date_to_now']

    def publish_posts(self, request, queryset):
        updated = queryset.update(status=Blog.Status.PUBLISHED, published_at=timezone.now())
        self.message_user(request, f'{updated} blog posts were successfully published.')
    publish_posts.short_description = "📝 Publish selected blog posts"

    def unpublish_posts(self, request, queryset):
        updated = queryset.update(status=Blog.Status.DRAFT)
        self.message_user(request, f'{updated} blog posts were unpublished and marked as draft.')
    unpublish_posts.short_description = "📝 Unpublish selected blog posts"

    def mark_as_draft(self, request, queryset):
        updated = queryset.update(status=Blog.Status.DRAFT)
        self.message_user(request, f'{updated} blog posts were marked as draft.')
    mark_as_draft.short_description = "📝 Mark selected as draft"

    def set_published_date_to_now(self, request, queryset):
        updated = queryset.update(published_at=timezone.now())
        self.message_user(request, f'Published date updated to now for {updated} blog posts.')
    set_published_date_to_now.short_description = "🕒 Set published date to now"

# FIXED UserActivityAdmin
@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'action')
    readonly_fields = ('timestamp',)

# ✅ FIXED: Only register CustomUserAdmin if User isn't already registered
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, CustomUserAdmin)
