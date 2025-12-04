# admin.py - COMPLETE ADMIN INTERFACE WITH LEGAL COMPLIANCE
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse
from django.core import serializers
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
import json

from allauth.account.models import EmailAddress

from .models import (
    BlogPost, UserProfile, TrustIndicator, LegalConsent, ProfileEditRequest,
    UserLike, UserFavorite, UserBlock, DateEvent, DateView, Conversation, 
    Message, UserActivityLog, UserProfileImage, PrivateAccessRequest, PrivateImage
)

# ==================== ADMIN CONFIGURATION ====================

admin.site.site_header = "Synergy Dating Admin - LEGAL COMPLIANCE MODE"
admin.site.site_title = "Synergy Admin Portal"
admin.site.index_title = "Administration Dashboard - All Data Monitored"

# ==================== INLINE ADMIN CLASSES ====================

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ('profile_name', 'profile_photo', 'location', 
              'relationship_status', 'is_complete', 'is_approved', 'trust_level')
    readonly_fields = ('display_age',)
    
    def display_age(self, obj):
        return obj.display_age() if hasattr(obj, 'display_age') and callable(obj.display_age) else 'N/A'
    display_age.short_description = 'Age'

class UserActivityLogInline(admin.TabularInline):
    model = UserActivityLog
    extra = 0
    can_delete = False
    readonly_fields = ['activity_type', 'target_user', 'ip_address', 'user_agent', 'created_at']
    fields = ['activity_type', 'target_user', 'ip_address', 'created_at']
    max_num = 10
    fk_name = 'user'

class UserLikeInline(admin.TabularInline):
    model = UserLike
    extra = 0
    can_delete = False
    verbose_name_plural = 'Likes Given'
    fk_name = 'user'
    fields = ['liked_user_id', 'created_at']
    readonly_fields = ['liked_user_id', 'created_at']

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False
    verbose_name_plural = 'Recent Messages'
    fields = ['conversation', 'content_preview', 'created_at', 'is_read']
    readonly_fields = ['conversation', 'content_preview', 'created_at', 'is_read']
    fk_name = 'sender'
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Message'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(sender=request.user if request.user.is_authenticated else None)[:5]

# ==================== CUSTOM USER ADMIN ====================

class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline, UserActivityLogInline, UserLikeInline, MessageInline]
    list_display = ['username', 'email', 'get_profile_name', 'date_joined', 
                    'last_login', 'is_active', 'is_staff', 'activity_count', 'message_count']
    list_filter = ['is_staff', 'is_active', 'date_joined', 'profile__is_approved']
    search_fields = ['username', 'email', 'profile__profile_name', 'first_name', 'last_name']
    
    # CRITICAL FIX: actions must be a list, not a method
    actions = ['deactivate_users', 'activate_users', 'export_user_data', 'view_full_activity_logs',
               'verify_selected_emails', 'unverify_selected_emails']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 
                                   'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    def get_profile_name(self, obj):
        try:
            return obj.profile.profile_name
        except UserProfile.DoesNotExist:
            return "-"
        except AttributeError:
            return "-"
    get_profile_name.short_description = 'Profile Name'
    
    def activity_count(self, obj):
        count = UserActivityLog.objects.filter(user=obj).count()
        url = reverse('admin:website_useractivitylog_changelist') + f'?user__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    activity_count.short_description = 'Activities'
    
    def message_count(self, obj):
        sent = Message.objects.filter(sender=obj).count()
        received = Message.objects.filter(conversation__participants=obj).exclude(sender=obj).count()
        url = reverse('admin:website_message_changelist') + f'?conversation__participants__id__exact={obj.id}'
        return format_html('<a href="{}">S:{} | R:{}</a>', url, sent, received)
    message_count.short_description = 'Messages'
    
    # Admin actions - must use @admin.action decorator
    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated.", messages.SUCCESS)
    
    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated.", messages.SUCCESS)
    
    @admin.action(description="Export user data (JSON)")
    def export_user_data(self, request, queryset):
        data = serializers.serialize('json', queryset, 
                                    fields=('username', 'email', 'first_name', 'last_name', 'date_joined'))
        response = HttpResponse(data, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="user_data.json"'
        return response
    
    @admin.action(description="View full activity logs")
    def view_full_activity_logs(self, request, queryset):
        user_ids = queryset.values_list('id', flat=True)
        logs = UserActivityLog.objects.filter(user_id__in=user_ids).order_by('-created_at')[:100]
        
        return render(request, 'admin/website/user_activity_report.html', {
            'logs': logs,
            'users': queryset,
            'title': 'User Activity Report'
        })
    
    @admin.action(description="Verify email for selected users")
    def verify_selected_emails(self, request, queryset):
        verified_count = 0
        for user in queryset:
            try:
                email_address = EmailAddress.objects.get(email=user.email, user=user)
                if not email_address.verified:
                    email_address.verified = True
                    email_address.save()
                    verified_count += 1
            except EmailAddress.DoesNotExist:
                # Create verified email address
                EmailAddress.objects.create(
                    user=user,
                    email=user.email,
                    verified=True,
                    primary=True
                )
                verified_count += 1
        
        if verified_count > 0:
            self.message_user(request, f"Verified email for {verified_count} user(s)", messages.SUCCESS)
        else:
            self.message_user(request, "No emails needed verification", level=messages.WARNING)
    
    @admin.action(description="Unverify email for selected users")
    def unverify_selected_emails(self, request, queryset):
        unverified_count = 0
        for user in queryset:
            try:
                email_address = EmailAddress.objects.get(email=user.email, user=user)
                if email_address.verified:
                    email_address.verified = False
                    email_address.save()
                    unverified_count += 1
            except EmailAddress.DoesNotExist:
                # Create unverified email address
                EmailAddress.objects.create(
                    user=user,
                    email=user.email,
                    verified=False,
                    primary=True
                )
                unverified_count += 1
        
        if unverified_count > 0:
            self.message_user(request, f"Unverified email for {unverified_count} user(s)", messages.SUCCESS)
        else:
            self.message_user(request, "No emails needed unverification", level=messages.WARNING)

# ==================== UNREGISTER AND REGISTER ====================

# Unregister the default User admin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

# Register with custom User admin
admin.site.register(User, UserAdmin)

# ==================== MODEL ADMIN CLASSES WITH EXPLICIT actions ATTRIBUTES ====================

class BaseModelAdmin(admin.ModelAdmin):
    """Base class to ensure all ModelAdmin classes have actions attribute"""
    actions = []

# ==================== MESSAGE ADMIN (CRITICAL FOR LEGAL COMPLIANCE) ====================

@admin.register(Message)
class MessageAdmin(BaseModelAdmin):
    list_display = ['id', 'conversation_link', 'sender_link', 'receiver_link', 
                    'content_preview', 'is_read', 'deleted_status', 'created_at']
    list_filter = ['is_read', 'is_deleted_for_sender', 'is_deleted_for_receiver', 
                   'created_at', 'conversation']
    search_fields = ['content', 'sender__username', 'sender__profile__profile_name']
    readonly_fields = ['conversation', 'sender', 'content', 'is_deleted_for_sender', 
                      'is_deleted_for_receiver', 'deleted_at', 'deleted_by', 'created_at']
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    fieldsets = (
        ('Message Content (LEGALLY RETAINED)', {
            'fields': ('content', 'sender', 'conversation')
        }),
        ('Delivery Status', {
            'fields': ('is_read', 'created_at')
        }),
        ('Deletion Status (Soft Delete Only)', {
            'fields': ('is_deleted_for_sender', 'is_deleted_for_receiver', 
                      'deleted_at', 'deleted_by'),
            'description': 'Messages are NEVER permanently deleted for legal compliance.'
        }),
    )
    
    def conversation_link(self, obj):
        url = reverse('admin:website_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">Conv #{}</a>', url, obj.conversation.id)
    conversation_link.short_description = 'Conversation'
    
    def sender_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.sender.id])
        return format_html('<a href="{}">{}</a>', url, obj.sender.username)
    sender_link.short_description = 'Sender'
    
    def receiver_link(self, obj):
        receiver = obj.conversation.participants.exclude(id=obj.sender.id).first()
        if receiver:
            url = reverse('admin:auth_user_change', args=[receiver.id])
            return format_html('<a href="{}">{}</a>', url, receiver.username)
        return '-'
    receiver_link.short_description = 'Receiver'
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Message'
    
    def deleted_status(self, obj):
        if obj.is_deleted_for_sender and obj.is_deleted_for_receiver:
            return format_html('<span style="color: #e74c3c;">Deleted for Both</span>')
        elif obj.is_deleted_for_sender:
            return format_html('<span style="color: #f39c12;">Deleted for Sender</span>')
        elif obj.is_deleted_for_receiver:
            return format_html('<span style="color: #f39c12;">Deleted for Receiver</span>')
        return format_html('<span style="color: #27ae60;">Active</span>')
    deleted_status.short_description = 'Deletion Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'conversation')
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_add_permission(self, request):
        return False

# ==================== CONVERSATION ADMIN ====================

@admin.register(Conversation)
class ConversationAdmin(BaseModelAdmin):
    list_display = ['id', 'participants_list', 'message_count', 'last_message_time', 
                    'created_at', 'view_messages_link']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['participants__username', 'participants__profile__profile_name']
    filter_horizontal = ['participants']
    readonly_fields = ['created_at', 'updated_at', 'participants_list_display']
    
    def participants_list(self, obj):
        users = []
        for p in obj.participants.all()[:3]:
            url = reverse('admin:auth_user_change', args=[p.id])
            users.append(format_html('<a href="{}">{}</a>', url, p.username))
        
        if obj.participants.count() > 3:
            users.append(f"...(+{obj.participants.count() - 3})")
            
        return format_html(', '.join(users))
    participants_list.short_description = 'Participants'
    
    def participants_list_display(self, obj):
        return self.participants_list(obj)
    participants_list_display.short_description = 'Participants'
    
    def message_count(self, obj):
        count = obj.messages.count()
        url = reverse('admin:website_message_changelist') + f'?conversation__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    message_count.short_description = 'Messages'
    
    def last_message_time(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        return last_msg.created_at if last_msg else '-'
    last_message_time.short_description = 'Last Message'
    
    def view_messages_link(self, obj):
        url = reverse('admin:website_message_changelist') + f'?conversation__id__exact={obj.id}'
        return format_html('<a href="{}" class="button">View Messages</a>', url)
    view_messages_link.short_description = 'Actions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('participants')

# ==================== USER ACTIVITY LOG ADMIN (CRITICAL FOR LEGAL COMPLIANCE) ====================

@admin.register(UserActivityLog)
class UserActivityLogAdmin(BaseModelAdmin):
    list_display = ['id', 'user_link', 'activity_type', 'target_user_link', 
                    'ip_address', 'created_at', 'additional_data_preview']
    list_filter = ['activity_type', 'created_at', 'ip_address']
    search_fields = ['user__username', 'user__email', 'ip_address', 
                    'additional_data', 'user_agent']
    readonly_fields = ['user', 'activity_type', 'target_user', 'ip_address', 
                      'user_agent', 'additional_data_prettified', 'created_at']
    date_hierarchy = 'created_at'
    list_per_page = 100
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('user', 'activity_type', 'target_user', 'created_at')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('additional_data_prettified',),
            'classes': ('collapse',)
        }),
    )
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    
    def target_user_link(self, obj):
        if obj.target_user:
            url = reverse('admin:auth_user_change', args=[obj.target_user.id])
            return format_html('<a href="{}">{}</a>', url, obj.target_user.username)
        return '-'
    target_user_link.short_description = 'Target User'
    
    def additional_data_preview(self, obj):
        if obj.additional_data:
            try:
                data_str = json.dumps(obj.additional_data)[:100]
                return data_str + '...' if len(data_str) > 100 else data_str
            except:
                return str(obj.additional_data)[:100]
        return '-'
    additional_data_preview.short_description = 'Data'
    
    def additional_data_prettified(self, obj):
        if obj.additional_data:
            try:
                return format_html('<pre style="background: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>', 
                                 json.dumps(obj.additional_data, indent=2, default=str))
            except:
                return format_html('<pre style="background: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>', 
                                 str(obj.additional_data))
        return '-'
    additional_data_prettified.short_description = 'Additional Data (Pretty)'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'target_user')

# ==================== PRIVATE ACCESS REQUEST ADMIN ====================

@admin.register(PrivateAccessRequest)
class PrivateAccessRequestAdmin(BaseModelAdmin):
    # FIXED: Added 'status' to list_display since it's in list_editable
    list_display = ['id', 'requester_link', 'target_user_link', 'status', 'status_badge', 
                    'created_at', 'granted_at', 'action_links']
    list_filter = ['status', 'created_at', 'granted_at']
    search_fields = ['requester__username', 'target_user__username', 'message']
    
    # FIXED: Check what fields actually exist in the model
    # Most likely only 'created_at' exists, not 'updated_at'
    readonly_fields = ['created_at']
    
    list_editable = ['status']
    
    # Override actions from BaseModelAdmin
    actions = ['grant_selected_requests', 'deny_selected_requests', 'revoke_selected_requests']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('requester', 'target_user', 'message', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'granted_at', 'denied_at', 'revoked_at')
        }),
        ('Admin Notes', {
            'fields': ('reason',),
            'classes': ('collapse',)
        }),
    )
    
    def requester_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.requester.id])
        return format_html('<a href="{}">{}</a>', url, obj.requester.username)
    requester_link.short_description = 'Requester'
    
    def target_user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.target_user.id])
        return format_html('<a href="{}">{}</a>', url, obj.target_user.username)
    target_user_link.short_description = 'Target User'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#f39c12',
            'granted': '#27ae60',
            'denied': '#e74c3c',
            'revoked': '#95a5a6'
        }
        return format_html(
            '<span style="padding: 4px 8px; border-radius: 4px; background: {}; color: white; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#95a5a6'),
            obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def action_links(self, obj):
        links = []
        if obj.status == 'pending':
            grant_url = reverse('admin:website_privateaccessrequest_grant', args=[obj.id])
            deny_url = reverse('admin:website_privateaccessrequest_deny', args=[obj.id])
            links.append(f'<a href="{grant_url}" class="button">Grant</a>')
            links.append(f'<a href="{deny_url}" class="button">Deny</a>')
        elif obj.status == 'granted':
            revoke_url = reverse('admin:website_privateaccessrequest_revoke', args=[obj.id])
            links.append(f'<a href="{revoke_url}" class="button">Revoke</a>')
        return format_html(' '.join(links))
    action_links.short_description = 'Actions'
    
    @admin.action(description="Grant selected access requests")
    def grant_selected_requests(self, request, queryset):
        granted_count = 0
        for access_request in queryset.filter(status='pending'):
            access_request.grant()
            granted_count += 1
        
        if granted_count > 0:
            self.message_user(request, f"Successfully granted {granted_count} access request(s)", messages.SUCCESS)
        else:
            self.message_user(request, "No requests were granted", level=messages.WARNING)
    
    @admin.action(description="Deny selected access requests")
    def deny_selected_requests(self, request, queryset):
        denied_count = 0
        for access_request in queryset.filter(status='pending'):
            access_request.deny("Denied via admin action")
            denied_count += 1
        
        if denied_count > 0:
            self.message_user(request, f"Successfully denied {denied_count} access request(s)", messages.SUCCESS)
        else:
            self.message_user(request, "No requests were denied", level=messages.WARNING)
    
    @admin.action(description="Revoke selected granted requests")
    def revoke_selected_requests(self, request, queryset):
        revoked_count = 0
        for access_request in queryset.filter(status='granted'):
            access_request.revoke("Revoked via admin action")
            revoked_count += 1
        
        if revoked_count > 0:
            self.message_user(request, f"Successfully revoked {revoked_count} access request(s)", messages.SUCCESS)
        else:
            self.message_user(request, "No granted requests were revoked", level=messages.WARNING)

# ==================== PRIVATE IMAGE ADMIN ====================

@admin.register(PrivateImage)
class PrivateImageAdmin(BaseModelAdmin):
    list_display = ['id', 'user_link', 'image_preview', 'caption', 'position', 
                    'is_active', 'uploaded_at']
    list_filter = ['is_active', 'uploaded_at']
    search_fields = ['user__username', 'caption']
    readonly_fields = ['uploaded_at', 'image_preview_large']
    list_editable = ['position', 'is_active']
    
    # Add actions
    actions = ['activate_selected_images', 'deactivate_selected_images']
    
    fieldsets = (
        ('Image Information', {
            'fields': ('user', 'image', 'caption', 'position', 'is_active')
        }),
        ('Preview', {
            'fields': ('image_preview_large',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at',)
        }),
    )
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    
    def image_preview(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html(
                '<img src="{}" style="max-height:50px;max-width:50px;border-radius:6px;" />',
                obj.image.url,
            )
        return "No Image"
    image_preview.short_description = 'Preview'
    
    def image_preview_large(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html(
                '<img src="{}" style="max-height:200px;max-width:200px;border-radius:6px;" />',
                obj.image.url,
            )
        return "No Image"
    image_preview_large.short_description = 'Large Preview'
    
    @admin.action(description="Activate selected images")
    def activate_selected_images(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} image(s) activated.", messages.SUCCESS)
    
    @admin.action(description="Deactivate selected images")
    def deactivate_selected_images(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} image(s) deactivated.", messages.SUCCESS)

# ==================== PROFILE EDIT REQUEST ADMIN ====================

@admin.register(ProfileEditRequest)
class ProfileEditRequestAdmin(BaseModelAdmin):
    list_display = [
        "user_display",
        "status_badge",
        "changed_fields_count",
        "created_at",
        "reviewed_by_display",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["user__username", "user__email", "user__first_name", "user__last_name"]
    readonly_fields = ["created_at", "updated_at", "changed_fields_list", "profile_comparison", "status_badge"]
    
    # Override actions from BaseModelAdmin
    actions = ['approve_selected_requests', 'reject_selected_requests', 'mark_as_pending']
    
    fieldsets = (
        (
            "Request Information",
            {
                "fields": (
                    "user",
                    "status_badge",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Changes Summary",
            {
                "fields": (
                    "changed_fields_list",
                    "profile_comparison",
                )
            },
        ),
        (
            "Profile Data (Pending Changes)",
            {
                "fields": (
                    "profile_name",
                    "date_of_birth",
                    "relationship_status",
                    "body_type",
                    "has_children",
                    "children_details",
                    "is_smoker",
                    "location",
                    "story",
                    "communication_style",
                    "preferred_age_min",
                    "preferred_age_max",
                    "preferred_distance",
                    "profile_photo",
                )
            },
        ),
        (
            "JSON Data Fields",
            {
                "fields": (
                    "personality_traits",
                    "life_priorities",
                    "core_values",
                    "arrangement_preferences",
                    "lifestyle_interests",
                    "privacy_settings",
                    "notification_preferences",
                ),
                "classes": ("collapse",)
            },
        ),
        (
            "Review Information",
            {
                "fields": (
                    "admin_notes",
                    "reviewed_by",
                    "reviewed_at",
                )
            },
        ),
    )

    def user_display(self, obj):
        return f"{obj.user.username} ({obj.user.email})"
    user_display.short_description = "User"

    def status_badge(self, obj):
        colors = {
            'pending': '#f39c12',
            'approved': '#27ae60', 
            'rejected': '#e74c3c'
        }
        return format_html(
            '<span style="padding: 4px 8px; border-radius: 4px; background: {}; color: white; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#95a5a6'),
            obj.status.upper()
        )
    status_badge.short_description = "Status"

    def changed_fields_count(self, obj):
        changed_fields = obj.get_changed_fields()
        count = len(changed_fields) if changed_fields else 0
        color = '#e74c3c' if count > 0 else '#95a5a6'
        return format_html(
            '<span style="padding: 4px 8px; border-radius: 50%; background: {}; color: white; font-weight: bold;">{}</span>',
            color,
            count
        )
    changed_fields_count.short_description = "Changes"

    def reviewed_by_display(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.username
        return "—"
    reviewed_by_display.short_description = "Reviewed By"

    def changed_fields_list(self, obj):
        changed_fields = obj.get_changed_fields()
        if not changed_fields:
            return "No changes detected"
        
        field_list = "".join([f"<li>{field}</li>" for field in changed_fields])
        return format_html(f"<ul>{field_list}</ul>")
    changed_fields_list.short_description = "Changed Fields"

    def profile_comparison(self, obj):
        """Show comparison between current profile and requested changes"""
        try:
            current_profile = obj.user.profile
            changed_fields = obj.get_changed_fields()
            
            if not changed_fields:
                return "No changes to display"
            
            comparison_html = """
            <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                <tr>
                    <th style="text-align: left; padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">Field</th>
                    <th style="text-align: left; padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">Current</th>
                    <th style="text-align: left; padding: 8px; border: 1px solid #ddd; background: #f8f9fa;">Requested</th>
                </tr>
            """
            
            for field in changed_fields:
                try:
                    current_value = getattr(current_profile, field, 'N/A')
                    new_value = getattr(obj, field, 'N/A')
                    
                    current_display = str(current_value) if current_value not in [None, ''] else 'Empty'
                    new_display = str(new_value) if new_value not in [None, ''] else 'Empty'
                    
                    comparison_html += f"""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>{field}</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{current_display}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; background: #d4edda;">{new_display}</td>
                    </tr>
                    """
                except AttributeError:
                    continue
            
            comparison_html += "</table>"
            return format_html(comparison_html)
        except UserProfile.DoesNotExist:
            return "User profile not found"
        except Exception as e:
            return f"Error generating comparison: {str(e)}"
    
    profile_comparison.short_description = "Profile Comparison"

    @admin.action(description="Approve selected requests")
    def approve_selected_requests(self, request, queryset):
        approved_count = 0
        for edit_request in queryset.filter(status='pending'):
            if edit_request.approve(request.user, "Approved via admin action"):
                approved_count += 1
        
        if approved_count > 0:
            self.message_user(request, f"Successfully approved {approved_count} profile edit request(s)", messages.SUCCESS)
        else:
            self.message_user(request, "No requests were approved", level=messages.WARNING)
    
    @admin.action(description="Reject selected requests")
    def reject_selected_requests(self, request, queryset):
        rejected_count = 0
        for edit_request in queryset.filter(status='pending'):
            edit_request.reject(request.user, "Rejected via admin action")
            rejected_count += 1
        
        if rejected_count > 0:
            self.message_user(request, f"Successfully rejected {rejected_count} profile edit request(s)", messages.SUCCESS)
        else:
            self.message_user(request, "No requests were rejected", level=messages.WARNING)
    
    @admin.action(description="Mark selected as pending")
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status='pending', reviewed_by=None, reviewed_at=None)
        self.message_user(request, f"{updated} request(s) marked as pending.", messages.SUCCESS)

# ==================== USERPROFILE ADMIN ====================

@admin.register(UserProfile)
class UserProfileAdmin(BaseModelAdmin):
    list_display = (
        "profile_name",
        "user_email",
        "display_age",
        "email_verified",
        "is_approved",
        "is_complete",
        "trust_level",
        "created_at",
    )
    list_filter = ("is_approved", "is_complete", "trust_level", "relationship_status", "gender")
    search_fields = ("profile_name", "user__email", "user__username", "location")
    readonly_fields = ("created_at", "updated_at", "display_age", "email_verified_display")
    ordering = ("-created_at",)
    
    # ADDED: Admin actions for profiles
    actions = ['approve_profiles', 'unapprove_profiles', 'mark_complete', 'mark_incomplete']
    
    fieldsets = (
        (
            "Member Information",
            {
                "fields": (
                    "user",
                    "profile_name",
                    "date_of_birth",
                    "gender",
                    "relationship_status",
                )
            },
        ),
        (
            "Location & Lifestyle",
            {
                "fields": (
                    "location",
                    "body_type",
                    "looking_for",
                    "has_children",
                    "children_details",
                    "is_smoker",
                )
            },
        ),
        (
            "About & Personality",
            {
                "fields": (
                    "story",
                    "communication_style",
                    "personality_traits",
                    "life_priorities",
                    "core_values",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Dating Preferences",
            {
                "fields": (
                    "preferred_age_min",
                    "preferred_age_max",
                    "preferred_distance",
                    "arrangement_preferences",
                    "lifestyle_interests",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Trust & Privacy",
            {
                "fields": (
                    "trust_level",
                    "privacy_settings",
                    "notification_preferences",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Verification & Status",
            {
                "fields": (
                    "email_verified_display",
                    "is_complete",
                    "is_approved",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def user_email(self, obj):
        return obj.user.email if obj.user else "No user"
    user_email.short_description = "Email"

    def email_verified(self, obj):
        return EmailAddress.objects.filter(user=obj.user, verified=True).exists()
    email_verified.boolean = True
    email_verified.short_description = "Email Verified?"
    
    def email_verified_display(self, obj):
        verified = EmailAddress.objects.filter(user=obj.user, verified=True).exists()
        if verified:
            return format_html('<span style="color: green;">✓ Verified</span>')
        else:
            return format_html('<span style="color: red;">✗ Not Verified</span>')
    email_verified_display.short_description = 'Email Verification'
    
    def display_age(self, obj):
        return obj.display_age() if hasattr(obj, 'display_age') and callable(obj.display_age) else 'N/A'
    display_age.short_description = 'Age'
    
    @admin.action(description="Approve selected profiles")
    def approve_profiles(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} profile(s) approved.", messages.SUCCESS)
    
    @admin.action(description="Unapprove selected profiles")
    def unapprove_profiles(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} profile(s) unapproved.", messages.SUCCESS)
    
    @admin.action(description="Mark selected profiles as complete")
    def mark_complete(self, request, queryset):
        updated = queryset.update(is_complete=True)
        self.message_user(request, f"{updated} profile(s) marked as complete.", messages.SUCCESS)
    
    @admin.action(description="Mark selected profiles as incomplete")
    def mark_incomplete(self, request, queryset):
        updated = queryset.update(is_complete=False)
        self.message_user(request, f"{updated} profile(s) marked as incomplete.", messages.SUCCESS)

# ==================== BLOGPOST ADMIN ====================

@admin.register(BlogPost)
class BlogPostAdmin(BaseModelAdmin):
    list_display = [
        "title",
        "author_display",
        "category",
        "position",
        "is_published",
        "status_badge",
        "published_date",
        "featured_image_preview",
    ]
    list_filter = ["is_published", "category", "position"]
    search_fields = ["title", "content", "author__username", "author__email"]
    list_editable = ["position", "is_published"]
    readonly_fields = ["published_date", "featured_image_preview", "status_badge"]
    ordering = ["position", "-published_date"]
    prepopulated_fields = {"slug": ("title",)}
    
    # Override actions from BaseModelAdmin
    actions = ['publish_selected', 'unpublish_selected', 'set_featured']

    fieldsets = (
        (
            "Content",
            {
                "fields": (
                    "title",
                    "slug",
                    "content",
                    "excerpt",
                    "featured_image",
                    "category",
                )
            },
        ),
        (
            "Publishing",
            {
                "fields": (
                    "author",
                    "is_published",
                    "position",
                    "published_date",
                    "status_badge",
                )
            },
        ),
        (
            "SEO",
            {
                "fields": (
                    "meta_title",
                    "meta_description",
                )
            },
        ),
    )

    def author_display(self, obj):
        if obj.author:
            if obj.author.first_name or obj.author.last_name:
                return f"{obj.author.first_name} {obj.author.last_name}".strip()
            return obj.author.username
        return "No author"
    author_display.short_description = "Author"

    def status_badge(self, obj):
        if obj.is_published:
            color = "#2ecc71"
            label = "Published"
        else:
            color = "#e67e22"
            label = "Draft"
        return format_html(
            '<span style="padding:3px 10px;border-radius:999px;'
            'font-size:0.8rem;background:{}20;color:{};">{}</span>',
            color,
            color,
            label,
        )
    status_badge.short_description = "Status"

    def featured_image_preview(self, obj):
        if obj.featured_image and hasattr(obj.featured_image, 'url'):
            return format_html(
                '<img src="{}" style="max-height:50px;max-width:50px;border-radius:6px;" />',
                obj.featured_image.url,
            )
        return "No Image"
    featured_image_preview.short_description = "Image"

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        if obj.is_published and not obj.published_date:
            obj.published_date = timezone.now()
        super().save_model(request, obj, form, change)

    @admin.action(description="Publish selected posts")
    def publish_selected(self, request, queryset):
        updated = queryset.update(is_published=True, published_date=timezone.now())
        self.message_user(request, f"{updated} blog post(s) published successfully.", messages.SUCCESS)
    
    @admin.action(description="Unpublish selected posts")
    def unpublish_selected(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} blog post(s) unpublished.", messages.SUCCESS)
    
    @admin.action(description="Mark selected as featured (position 0)")
    def set_featured(self, request, queryset):
        updated = queryset.update(position=0)
        self.message_user(request, f"{updated} post(s) marked as featured.", messages.SUCCESS)

# ==================== DATE EVENT ADMIN ====================

@admin.register(DateEvent)
class DateEventAdmin(BaseModelAdmin):
    list_display = ['title', 'host_link', 'activity', 'date_time', 'area', 
                    'is_cancelled', 'created_at', 'view_count']
    list_filter = ['activity', 'is_cancelled', 'date_time', 'created_at']
    search_fields = ['title', 'host__username', 'area', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    # Add actions
    actions = ['cancel_selected_dates', 'uncancel_selected_dates']
    
    def host_link(self, obj):
        if obj.host:
            url = reverse('admin:auth_user_change', args=[obj.host.id])
            return format_html('<a href="{}">{}</a>', url, obj.host.username)
        return "No host"
    host_link.short_description = 'Host'
    
    def view_count(self, obj):
        return obj.dateview_set.count()
    view_count.short_description = 'Views'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('host')
    
    @admin.action(description="Cancel selected dates")
    def cancel_selected_dates(self, request, queryset):
        updated = queryset.update(is_cancelled=True)
        self.message_user(request, f"{updated} date(s) cancelled.", messages.SUCCESS)
    
    @admin.action(description="Uncancel selected dates")
    def uncancel_selected_dates(self, request, queryset):
        updated = queryset.update(is_cancelled=False)
        self.message_user(request, f"{updated} date(s) uncancelled.", messages.SUCCESS)

# ==================== OTHER MODELS ====================

@admin.register(UserLike)
class UserLikeAdmin(BaseModelAdmin):
    list_display = ['user_link', 'liked_user_link', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'liked_user_id']
    readonly_fields = ['created_at']
    
    # Add actions
    actions = ['export_likes_csv']
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "No user"
    user_link.short_description = 'User'
    
    def liked_user_link(self, obj):
        try:
            liked_user = User.objects.get(id=obj.liked_user_id)
            url = reverse('admin:auth_user_change', args=[liked_user.id])
            return format_html('<a href="{}">{}</a>', url, liked_user.username)
        except User.DoesNotExist:
            return f"User ID: {obj.liked_user_id}"
    liked_user_link.short_description = 'Liked User'
    
    @admin.action(description="Export likes to CSV")
    def export_likes_csv(self, request, queryset):
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="likes_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User', 'Liked User', 'Created At'])
        
        for like in queryset:
            writer.writerow([
                like.user.username if like.user else f"User ID: {like.user_id}",
                like.liked_user_id,
                like.created_at
            ])
        
        return response

@admin.register(UserFavorite)
class UserFavoriteAdmin(BaseModelAdmin):
    list_display = ['user_link', 'favorite_user_link', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']
    
    # Add actions
    actions = ['export_favorites_csv']
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "No user"
    user_link.short_description = 'User'
    
    def favorite_user_link(self, obj):
        try:
            favorite_user = User.objects.get(id=obj.favorite_user_id)
            url = reverse('admin:auth_user_change', args=[favorite_user.id])
            return format_html('<a href="{}">{}</a>', url, favorite_user.username)
        except User.DoesNotExist:
            return f"User ID: {obj.favorite_user_id}"
    favorite_user_link.short_description = 'Favorite User'
    
    @admin.action(description="Export favorites to CSV")
    def export_favorites_csv(self, request, queryset):
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="favorites_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User', 'Favorite User', 'Created At'])
        
        for favorite in queryset:
            writer.writerow([
                favorite.user.username if favorite.user else f"User ID: {favorite.user_id}",
                favorite.favorite_user_id,
                favorite.created_at
            ])
        
        return response

@admin.register(UserBlock)
class UserBlockAdmin(BaseModelAdmin):
    list_display = ['user_link', 'blocked_user_link', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']
    
    # Add actions
    actions = ['export_blocks_csv']
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "No user"
    user_link.short_description = 'User'
    
    def blocked_user_link(self, obj):
        try:
            blocked_user = User.objects.get(id=obj.blocked_user_id)
            url = reverse('admin:auth_user_change', args=[blocked_user.id])
            return format_html('<a href="{}">{}</a>', url, blocked_user.username)
        except User.DoesNotExist:
            return f"User ID: {obj.blocked_user_id}"
    blocked_user_link.short_description = 'Blocked User'
    
    @admin.action(description="Export blocks to CSV")
    def export_blocks_csv(self, request, queryset):
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="blocks_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User', 'Blocked User', 'Created At'])
        
        for block in queryset:
            writer.writerow([
                block.user.username if block.user else f"User ID: {block.user_id}",
                block.blocked_user_id,
                block.created_at
            ])
        
        return response

@admin.register(DateView)
class DateViewAdmin(BaseModelAdmin):
    list_display = ['user_link', 'date_event_link', 'viewed_at']
    list_filter = ['viewed_at']
    
    # Add actions
    actions = ['export_views_csv']
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "No user"
    user_link.short_description = 'User'
    
    def date_event_link(self, obj):
        if obj.date_event:
            url = reverse('admin:website_dateevent_change', args=[obj.date_event.id])
            return format_html('<a href="{}">{}</a>', url, obj.date_event.title)
        return "No event"
    
    @admin.action(description="Export date views to CSV")
    def export_views_csv(self, request, queryset):
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="date_views_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User', 'Date Event', 'Viewed At'])
        
        for view in queryset:
            writer.writerow([
                view.user.username if view.user else f"User ID: {view.user_id}",
                view.date_event.title if view.date_event else f"Event ID: {view.date_event_id}",
                view.viewed_at
            ])
        
        return response

@admin.register(TrustIndicator)
class TrustIndicatorAdmin(BaseModelAdmin):
    list_display = ("user", "indicator_type", "is_active", "created_at")
    list_filter = ("indicator_type", "is_active")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("created_at",)
    
    # Add actions
    actions = ['activate_indicators', 'deactivate_indicators']
    
    @admin.action(description="Activate selected indicators")
    def activate_indicators(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} indicator(s) activated.", messages.SUCCESS)
    
    @admin.action(description="Deactivate selected indicators")
    def deactivate_indicators(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} indicator(s) deactivated.", messages.SUCCESS)

@admin.register(LegalConsent)
class LegalConsentAdmin(BaseModelAdmin):
    list_display = (
        "user",
        "terms_version",
        "privacy_version",
        "safety_acknowledged",
        "consent_date",
        "ip_address",
    )
    list_filter = ("safety_acknowledged", "terms_version", "privacy_version")
    search_fields = ("user__email", "user__username", "ip_address")
    readonly_fields = ("consent_date",)
    
    # Add actions
    actions = ['export_consents_csv']

@admin.register(UserProfileImage)
class UserProfileImageAdmin(BaseModelAdmin):
    list_display = ['user_profile_link', 'image_type', 'position', 'image_preview', 'created_at']
    list_filter = ['image_type', 'created_at']
    search_fields = ['user_profile__profile_name']
    readonly_fields = ['image_preview', 'created_at']
    
    # Add actions
    actions = ['reorder_to_top']
    
    def user_profile_link(self, obj):
        if obj.user_profile:
            url = reverse('admin:website_userprofile_change', args=[obj.user_profile.id])
            return format_html('<a href="{}">{}</a>', url, obj.user_profile.profile_name)
        return "No profile"
    user_profile_link.short_description = 'Profile'
    
    def image_preview(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return format_html(
                '<img src="{}" style="max-height:100px;max-width:100px;border-radius:6px;" />',
                obj.image.url,
            )
        return "No Image"
    image_preview.short_description = 'Preview'
    
    @admin.action(description="Reorder selected to position 0")
    def reorder_to_top(self, request, queryset):
        updated = queryset.update(position=0)
        self.message_user(request, f"{updated} image(s) moved to top position.", messages.SUCCESS)
