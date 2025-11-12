# pages/admin.py
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.db import models
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.utils.html import format_html
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.db.models import Count, Q
from django.core.mail import send_mail
from django.conf import settings

from . import views
from .models import (
    Profile, Message, Thread, Like, Block, PrivateAccessRequest,
    HotDate, HotDateView, HotDateNotification, Blog, UserActivity, 
    ProfileImage, AdminMessage, EmailReminderLog
)

# ✅ ENHANCED ADMIN WITH SECURITY FEATURES

# ✅ CUSTOM FILTERS FOR BETTER WORKFLOW
class ApprovalStatusFilter(admin.SimpleListFilter):
    title = 'Approval Status'
    parameter_name = 'approval_status'
    
    def lookups(self, request, model_admin):
        return (
            ('needs_review', '🟡 Needs Review'),
            ('approved', '✅ Approved'),
            ('rejected', '❌ Rejected'),
            ('changes_requested', '✏️ Needs Changes'),
            ('unverified', '⚠️ Unverified Email'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'needs_review':
            return queryset.filter(approval_status='pending_review')
        elif self.value() == 'approved':
            return queryset.filter(approval_status='approved', is_approved=True)
        elif self.value() == 'rejected':
            return queryset.filter(approval_status='rejected')
        elif self.value() == 'changes_requested':
            return queryset.filter(approval_status='changes_requested')
        elif self.value() == 'unverified':
            return queryset.filter(email_verified=False)
        return queryset

class ProfileCompletenessFilter(admin.SimpleListFilter):
    title = 'Profile Photos'
    parameter_name = 'photos'
    
    def lookups(self, request, model_admin):
        return (
            ('no_photos', '📷 No Photos'),
            ('has_photos', '📸 Has Photos'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'no_photos':
            from .models import ProfileImage
            profiles_with_photos = ProfileImage.objects.values_list('profile_id', flat=True).distinct()
            return queryset.exclude(id__in=profiles_with_photos)
        elif self.value() == 'has_photos':
            from .models import ProfileImage
            profiles_with_photos = ProfileImage.objects.values_list('profile_id', flat=True).distinct()
            return queryset.filter(id__in=profiles_with_photos)
        return queryset

class ReminderStatusFilter(admin.SimpleListFilter):
    title = 'Reminder Status'
    parameter_name = 'reminder_status'
    
    def lookups(self, request, model_admin):
        return (
            ('needs_verification_reminder', '📧 Needs Email Verification Reminder'),
            ('needs_completion_reminder', '📝 Needs Profile Completion Reminder'),
            ('marked_for_deletion', '🚨 Marked for Deletion'),
            ('no_reminders', '✅ No Reminders Needed'),
        )
    
    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'needs_verification_reminder':
            return queryset.filter(
                email_verified=False,
                email_verification_reminder_count__lt=3,
                email_verification_last_reminder_sent__lt=now - timezone.timedelta(days=7)
            )
        elif self.value() == 'needs_completion_reminder':
            return queryset.filter(
                is_complete=False,
                profile_completion_reminder_count__lt=5,
                profile_completion_last_reminder_sent__lt=now - timezone.timedelta(days=5)
            )
        elif self.value() == 'marked_for_deletion':
            return queryset.filter(marked_for_deletion=True)
        elif self.value() == 'no_reminders':
            return queryset.filter(
                email_verified=True,
                is_complete=True,
                marked_for_deletion=False
            )
        return queryset

# ✅ QUICK ACTION VIEWS WITH SECURITY ENHANCEMENTS
def approve_profile(request, profile_id):
    try:
        profile = Profile.objects.get(id=profile_id)
        
        # SAFETY CHECK: Don't approve unverified emails
        if not profile.email_verified:
            messages.error(request, f"Cannot approve {profile.user.username}: Email not verified!")
            return HttpResponseRedirect(reverse('admin:pages_profile_changelist'))
        
        profile.is_approved = True
        profile.approval_status = 'approved'
        profile.approved_at = timezone.now()
        profile.approved_by = request.user
        
        # SECURITY FIX: Capture approved content state
        profile.capture_approved_state()
        
        profile.save()
        
        # ✅ ADDED: Send approval email for single profile approval
        from .utils.emails import send_profile_approved_email
        email_sent = send_profile_approved_email(
            user_email=profile.user.email,
            username=profile.user.username,
            login_url=request.build_absolute_uri(reverse('login'))
        )
        
        if email_sent:
            messages.success(request, f"Profile approved and notification sent to: {profile.user.username}")
        else:
            messages.warning(request, f"Profile approved but failed to send email to: {profile.user.username}")
            
    except Profile.DoesNotExist:
        messages.error(request, "Profile not found")
    
    return HttpResponseRedirect(reverse('admin:pages_profile_changelist'))

def reject_profile(request, profile_id):
    try:
        profile = Profile.objects.get(id=profile_id)
        profile.is_approved = False
        profile.approval_status = 'rejected'
        profile.save()
        messages.success(request, f"Profile rejected: {profile.user.username}")
    except Profile.DoesNotExist:
        messages.error(request, "Profile not found")
    
    return HttpResponseRedirect(reverse('admin:pages_profile_changelist'))

def request_changes(request, profile_id):
    try:
        profile = Profile.objects.get(id=profile_id)
        profile.approval_status = 'changes_requested'
        profile.save()
        messages.success(request, f"Changes requested for: {profile.user.username}")
    except Profile.DoesNotExist:
        messages.error(request, "Profile not found")
    
    return HttpResponseRedirect(reverse('admin:pages_profile_changelist'))

def resend_verification(request, profile_id):
    """Resend verification email to user"""
    try:
        profile = Profile.objects.get(id=profile_id)
        
        if profile.email_verified:
            messages.info(request, f"Email already verified for {profile.user.username}")
            return HttpResponseRedirect(reverse('admin:pages_profile_changelist'))
        
        # Update token and send time
        import secrets
        profile.email_verification_token = secrets.token_urlsafe(32)
        profile.email_verification_sent_at = timezone.now()
        profile.save()
        
        # Send verification email
        verification_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'token': profile.email_verification_token})
        )
        
        from .utils.emails import send_email_verification_email
        # ✅ FIXED: Correct function signature
        success = send_email_verification_email(
            user_email=profile.user.email,
            username=profile.user.username,
            verification_url=verification_url
        )
        
        if success:
            messages.success(request, f"Verification email sent to {profile.user.email}")
        else:
            messages.error(request, f"Failed to send verification email to {profile.user.email}")
            
    except Profile.DoesNotExist:
        messages.error(request, "Profile not found")
    
    return HttpResponseRedirect(reverse('admin:pages_profile_changelist'))

def view_live_profile(request, profile_id):
    """View profile as it appears to users"""
    try:
        profile = Profile.objects.get(id=profile_id)
        # Use the correct URL name from urls.py
        return redirect(reverse('profile_detail', kwargs={'user_id': profile.user_id}))
    except Profile.DoesNotExist:
        messages.error(request, "Profile not found")
        return HttpResponseRedirect(reverse('admin:pages_profile_changelist'))

# ✅ PROFILE IMAGE INLINE FOR PROFILE ADMIN WITH SECURITY FIELDS
class ProfileImageInline(admin.TabularInline):
    model = ProfileImage
    extra = 0
    readonly_fields = ('image_preview', 'created_at', 'needs_approval', 'is_approved')
    fields = ('image_preview', 'image', 'image_type', 'is_primary', 'needs_approval', 'is_approved', 'created_at')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 8px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = 'Preview'

# ✅ EMAIL REMINDER LOG INLINE
class EmailReminderLogInline(admin.TabularInline):
    model = EmailReminderLog
    extra = 0
    readonly_fields = ['reminder_type', 'sent_at', 'was_successful', 'error_message']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

# ✅ MOBILE-FRIENDLY PROFILE ADMIN WITH SECURITY FEATURES
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # MOBILE-FRIENDLY COLUMNS - Only essential info
    list_display = (
        'mobile_user_info',
        'mobile_status',
        'mobile_photos',
        'mobile_reminders',
        'mobile_created',
        'mobile_actions'
    )
    
    list_filter = (
        ApprovalStatusFilter,
        ProfileCompletenessFilter,
        ReminderStatusFilter,
        'email_verified',
        'my_gender',
        'looking_for',
        'created_at',
        'marked_for_deletion',
    )
    
    search_fields = ('user__username', 'user__email', 'headline', 'location', 'about')
    readonly_fields = (
        'created_at', 'updated_at', 'email_verification_token', 
        'email_verification_sent_at', 'approved_at', 'approved_by',
        'profile_images_display', 'view_live_profile_button',
        'email_verification_reminder_count', 'profile_completion_reminder_count',
        'profile_approval_reminder_count', 'inactivity_reminder_count',
        'last_activity_date', 'marked_for_deletion_at',
        'approved_content_snapshot_display', 'last_approved_at'  # SECURITY FIELDS
    )
    
    list_per_page = 25  # Fewer rows for mobile
    
    # ✅ ENHANCED BULK ACTIONS - Added reminder actions
    actions = [
        'approve_selected_verified',  # Only verified emails
        'approve_selected_all',       # All including unverified (with auto-verify)
        'verify_emails_selected',     # Just verify emails without approving
        'reject_selected', 
        'request_changes', 
        'resend_verification',
        'send_email_verification_reminder',
        'send_profile_completion_reminder',
        'mark_for_deletion',
        'unmark_for_deletion',
        'capture_approved_state',  # SECURITY ACTION
    ]
    
    # ✅ ADD PROFILE IMAGES AND REMINDER LOG INLINES
    inlines = [ProfileImageInline, EmailReminderLogInline]
    
    # ENHANCED FIELDSETS WITH SECURITY INFORMATION
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'headline', 'about', 'view_live_profile_button')
        }),
        ('Details', {
            'fields': ('location', 'date_of_birth', 'my_gender', 'looking_for'),
            'classes': ('collapse',)  # Collapsible on mobile
        }),
        ('Profile Images', {
            'fields': ('profile_images_display',),
            'classes': ('collapse',)
        }),
        ('Approval', {
            'fields': ('is_approved', 'approval_status', 'email_verified')
        }),
        ('Security - Approved Content State', {
            'fields': ('approved_content_snapshot_display', 'last_approved_at'),
            'classes': ('collapse',),
            'description': 'Content state when profile was approved - prevents degradation'
        }),
        ('Reminder Tracking', {
            'fields': (
                ('email_verification_reminder_count', 'email_verification_last_reminder_sent'),
                ('profile_completion_reminder_count', 'profile_completion_last_reminder_sent'),
                ('profile_approval_reminder_count', 'profile_approval_last_reminder_sent'),
                ('inactivity_reminder_count', 'inactivity_last_reminder_sent'),
                'last_activity_date',
                ('marked_for_deletion', 'marked_for_deletion_at')
            ),
            'classes': ('collapse',)
        }),
        ('System Info', {
            'fields': ('created_at', 'updated_at', 'approved_at', 'approved_by'),
            'classes': ('collapse',)
        }),
    )
    
    # ✅ ADDED: Display approved content snapshot
    def approved_content_snapshot_display(self, obj):
        """Display approved content state in admin"""
        if not obj.approved_content_snapshot:
            return "No approved state captured yet"
        
        snapshot = obj.approved_content_snapshot
        items = []
        
        for key, value in snapshot.items():
            if key in ['approved_photo_count', 'approved_private_photo_count']:
                display_key = key.replace('_', ' ').title()
                items.append(f"<strong>{display_key}:</strong> {value}")
            elif value:  # Only show non-empty values
                display_key = key.replace('_', ' ').title()
                display_value = value[:100] + "..." if len(str(value)) > 100 else value
                items.append(f"<strong>{display_key}:</strong> {display_value}")
        
        return format_html('<br>'.join(items))
    approved_content_snapshot_display.short_description = 'Approved Content State'
    
    # ✅ ADDED: Send approval email when approving from individual profile edit page
    def save_model(self, request, obj, form, change):
        """Override save to send approval email when approving from edit page"""
        # Check if this is an approval action (status changing to approved)
        was_approved_before = False
        if obj.pk:  # Existing object
            try:
                old_obj = Profile.objects.get(pk=obj.pk)
                was_approved_before = old_obj.is_approved and old_obj.approval_status == 'approved'
            except Profile.DoesNotExist:
                pass
        
        # Save the profile first
        super().save_model(request, obj, form, change)
        
        # Check if it was just approved (and wasn't approved before)
        is_approved_now = obj.is_approved and obj.approval_status == 'approved'
        
        if is_approved_now and not was_approved_before:
            # SECURITY FIX: Capture approved content state
            obj.capture_approved_state()
            
            # ✅ Send approval email for individual profile edit approval
            from .utils.emails import send_profile_approved_email
            email_sent = send_profile_approved_email(
                user_email=obj.user.email,
                username=obj.user.username,
                login_url=request.build_absolute_uri(reverse('login'))
            )
            
            if email_sent:
                messages.success(request, f"Profile approved and notification sent to: {obj.user.username}")
            else:
                messages.warning(request, f"Profile approved but failed to send email to: {obj.user.username}")
    
    # ✅ PROFILE IMAGES DISPLAY IN ADMIN - Shows ALL images in a gallery
    def profile_images_display(self, obj):
        """Display all profile images in the admin"""
        images = ProfileImage.objects.filter(profile=obj)
        if not images:
            return "No images uploaded"
        
        image_html = []
        for image in images:
            status = "🟢 PRIMARY" if image.is_primary else "🔵 Additional"
            privacy = "🔒 Private" if image.image_type == 'private' else "👁 Public"
            approval_status = "⏳ Pending" if image.needs_approval and not image.is_approved else "✅ Approved"
            border_color = "#28a745" if image.is_primary else "#6c757d"
            if image.needs_approval and not image.is_approved:
                border_color = "#ffc107"  # Yellow for pending approval
            
            image_html.append(
                f'<div style="display: inline-block; margin: 10px; text-align: center;">'
                f'<img src="{image.image.url}" style="max-height: 150px; max-width: 150px; border-radius: 8px; border: 2px solid {border_color};" />'
                f'<div style="margin-top: 5px; font-size: 12px;">'
                f'<div>{status}</div>'
                f'<div>{privacy}</div>'
                f'<div>Approval: {approval_status}</div>'
                f'<div>Uploaded: {image.created_at.strftime("%Y-%m-%d")}</div>'
                f'</div>'
                f'</div>'
            )
        
        return format_html('<div style="display: flex; flex-wrap: wrap;">{}</div>', ''.join(image_html))
    profile_images_display.short_description = 'All Profile Images'
    
    # ✅ VIEW LIVE PROFILE BUTTON - Fixed with correct URL name
    def view_live_profile_button(self, obj):
        """Button to view profile as users see it"""
        profile_url = reverse('profile_detail', kwargs={'user_id': obj.user_id})
        return format_html(
            '<a href="{}" target="_blank" style="background: #17a2b8; color: white; padding: 10px 15px; border-radius: 5px; text-decoration: none; font-weight: bold; display: inline-block;">'
            '👁 View Live Profile'
            '</a>',
            profile_url
        )
    view_live_profile_button.short_description = 'Live Preview'
    
    # ✅ MOBILE-OPTIMIZED COLUMNS
    def mobile_user_info(self, obj):
        """Compact user info for mobile"""
        return format_html(
            '<div style="min-width: 120px;">'
            '<strong>{}</strong><br/>'
            '<small style="color: #666;">{}</small><br/>'
            '<small style="color: #888;">{}</small>'
            '</div>',
            obj.user.username,
            obj.user.email,
            obj.headline[:30] + "..." if obj.headline and len(obj.headline) > 30 else obj.headline or "No headline"
        )
    mobile_user_info.short_description = 'User Info'
    
    def mobile_status(self, obj):
        """Compact status badges"""
        # Email status
        email_badge = '✅' if obj.email_verified else '⚠️'
        email_color = '#28a745' if obj.email_verified else '#dc3545'
        
        # Approval status
        status_map = {
            'approved': ('✅', '#28a745'),
            'rejected': ('❌', '#dc3545'), 
            'pending_review': ('🟡', '#ffc107'),
            'changes_requested': ('✏️', '#17a2b8'),
        }
        approval_icon, approval_color = status_map.get(obj.approval_status, ('❓', '#6c757d'))
        
        return format_html(
            '<div style="min-width: 80px; text-align: center;">'
            '<div title="Email: {}" style="color: {}; font-size: 16px; margin-bottom: 4px;">{}</div>'
            '<div title="Status: {}" style="color: {}; font-size: 16px;">{}</div>'
            '</div>',
            "Verified" if obj.email_verified else "Unverified",
            email_color, email_badge,
            obj.approval_status.replace('_', ' ').title(),
            approval_color, approval_icon
        )
    mobile_status.short_description = 'Status'
    
    def mobile_photos(self, obj):
        """Photo count with icon"""
        try:
            from .models import ProfileImage
            count = ProfileImage.objects.filter(profile=obj).count()
            approved_count = ProfileImage.objects.filter(profile=obj, is_approved=True).count()
            pending_count = count - approved_count
            
            color = "#28a745" if count >= 1 else "#dc3545"
            icon = "📸" if count >= 1 else "📷"
            
            if pending_count > 0:
                return format_html(
                    '<div style="text-align: center; min-width: 60px;" title="{} photos ({} pending approval)">'
                    '<span style="color: {}; font-size: 16px;">{}</span><br/>'
                    '<small style="color: {};">{}<span style="color: #ffc107;"> (+{})</span></small>'
                    '</div>',
                    count, pending_count, color, icon, color, approved_count, pending_count
                )
            else:
                return format_html(
                    '<div style="text-align: center; min-width: 60px;" title="{} photos">'
                    '<span style="color: {}; font-size: 16px;">{}</span><br/>'
                    '<small style="color: {};">{}</small>'
                    '</div>',
                    count, color, icon, color, count
                )
        except Exception:
            return format_html('<div style="text-align: center;">📷 0</div>')
    mobile_photos.short_description = 'Photos'
    
    def mobile_reminders(self, obj):
        """Reminder status summary"""
        total_reminders = (
            obj.email_verification_reminder_count +
            obj.profile_completion_reminder_count + 
            obj.profile_approval_reminder_count +
            obj.inactivity_reminder_count
        )
        
        if obj.marked_for_deletion:
            return format_html(
                '<div style="text-align: center; min-width: 60px;" title="Marked for deletion">'
                '<span style="color: #dc3545; font-size: 16px;">🚨</span><br/>'
                '<small style="color: #dc3545;">Delete</small>'
                '</div>'
            )
        elif total_reminders > 0:
            return format_html(
                '<div style="text-align: center; min-width: 60px;" title="{} total reminders">'
                '<span style="color: #ffc107; font-size: 16px;">🔔</span><br/>'
                '<small style="color: #ffc107;">{}</small>'
                '</div>',
                total_reminders, total_reminders
            )
        else:
            return format_html(
                '<div style="text-align: center; min-width: 60px;" title="No reminders">'
                '<span style="color: #28a745; font-size: 16px;">✅</span><br/>'
                '<small style="color: #28a745;">Clean</small>'
                '</div>'
            )
    mobile_reminders.short_description = 'Reminders'
    
    def mobile_created(self, obj):
        """Compact date display"""
        delta = timezone.now() - obj.created_at
        if delta.days == 0:
            return "Today"
        elif delta.days == 1:
            return "1d"
        elif delta.days < 7:
            return f"{delta.days}d"
        elif delta.days < 30:
            return f"{delta.days//7}w"
        else:
            return f"{delta.days//30}m"
    mobile_created.short_description = 'Created'
    mobile_created.admin_order_field = 'created_at'
    
    def mobile_actions(self, obj):
        """Compact action buttons for mobile"""
        buttons = []
        
        # Main action button based on status
        if obj.approval_status != 'approved' and obj.email_verified:
            buttons.append(
                f'<a href="/admin/approve-profile/{obj.id}/" title="Approve" style="background: #28a745; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; margin: 1px; display: inline-block;">✓</a>'
            )
        elif not obj.email_verified:
            buttons.append(
                f'<a href="/admin/resend-verification/{obj.id}/" title="Resend Verification" style="background: #ffc107; color: black; padding: 4px 8px; border-radius: 4px; text-decoration: none; margin: 1px; display: inline-block;">✉️</a>'
            )
        
        # Reject button
        if obj.approval_status != 'rejected':
            buttons.append(
                f'<a href="/admin/reject-profile/{obj.id}/" title="Reject" style="background: #dc3545; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; margin: 1px; display: inline-block;">✗</a>'
            )
        
        # View details button
        buttons.append(
            f'<a href="/admin/pages/profile/{obj.id}/change/" title="View Details" style="background: #6c757d; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; margin: 1px; display: inline-block;">👁</a>'
        )
        
        # View live profile button
        buttons.append(
            f'<a href="/admin/view-live-profile/{obj.id}/" title="View Live Profile" style="background: #17a2b8; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; margin: 1px; display: inline-block;">🌐</a>'
        )
        
        return format_html(' '.join(buttons))
    mobile_actions.short_description = 'Actions'
    
    # ✅ ENHANCED BULK ACTIONS WITH SECURITY FEATURES
    
    def approve_selected_verified(self, request, queryset):
        """Approve only profiles with verified emails"""
        verified_profiles = queryset.filter(email_verified=True)
        unverified_profiles = queryset.filter(email_verified=False)
        
        approved_count = verified_profiles.count()
        unverified_count = unverified_profiles.count()
        
        # Only approve verified profiles with content snapshot
        for profile in verified_profiles:
            profile.is_approved = True
            profile.approval_status = 'approved'
            profile.approved_at = timezone.now()
            profile.approved_by = request.user
            profile.capture_approved_state()  # SECURITY FIX
            profile.save()
        
        # ✅ ADDED: Send approval emails for bulk approval
        from .utils.emails import send_profile_approved_email
        emailed_count = 0
        for profile in verified_profiles:
            email_sent = send_profile_approved_email(
                user_email=profile.user.email,
                username=profile.user.username,
                login_url=request.build_absolute_uri(reverse('login'))
            )
            if email_sent:
                emailed_count += 1
        
        if unverified_count > 0:
            self.message_user(
                request, 
                f'✅ Approved {approved_count} verified profiles. 📧 Sent {emailed_count} approval emails. ⚠️ Skipped {unverified_count} unverified profiles.', 
                messages.WARNING
            )
        else:
            self.message_user(
                request, 
                f'✅ Approved {approved_count} profiles. 📧 Sent {emailed_count} approval emails.', 
                messages.SUCCESS
            )
    
    approve_selected_verified.short_description = "✅ Approve SELECTED (verified emails only)"
    
    def approve_selected_all(self, request, queryset):
        """Approve all selected profiles and auto-verify their emails"""
        total_count = queryset.count()
        unverified_profiles = queryset.filter(email_verified=False)
        
        # Auto-verify emails for unverified profiles
        unverified_count = unverified_profiles.count()
        if unverified_count > 0:
            unverified_profiles.update(email_verified=True)
            self.message_user(
                request, 
                f'📧 Auto-verified {unverified_count} emails.', 
                messages.INFO
            )
        
        # Approve all profiles with content snapshot
        for profile in queryset:
            profile.is_approved = True
            profile.approval_status = 'approved'
            profile.approved_at = timezone.now()
            profile.approved_by = request.user
            profile.capture_approved_state()  # SECURITY FIX
            profile.save()
        
        # ✅ ADDED: Send approval emails for bulk approval (all)
        from .utils.emails import send_profile_approved_email
        emailed_count = 0
        for profile in queryset:
            email_sent = send_profile_approved_email(
                user_email=profile.user.email,
                username=profile.user.username,
                login_url=request.build_absolute_uri(reverse('login'))
            )
            if email_sent:
                emailed_count += 1
    
        self.message_user(
            request, 
            f'✅ Approved {total_count} profiles. 📧 Auto-verified {unverified_count} emails. 📨 Sent {emailed_count} approval emails.', 
            messages.SUCCESS
        )
    
    approve_selected_all.short_description = "🚀 APPROVE ALL + Auto-verify emails"
    
    def capture_approved_state(self, request, queryset):
        """Capture approved content state for selected profiles"""
        count = 0
        for profile in queryset:
            if profile.is_approved:
                profile.capture_approved_state()
                count += 1
        
        if count > 0:
            self.message_user(
                request,
                f'✅ Captured approved content state for {count} profiles.',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                '⚠️ No approved profiles selected to capture state.',
                messages.WARNING
            )
    
    capture_approved_state.short_description = "📸 Capture approved content state"
    
    def verify_emails_selected(self, request, queryset):
        """Verify emails for selected profiles without approving"""
        unverified_profiles = queryset.filter(email_verified=False)
        already_verified_count = queryset.filter(email_verified=True).count()
        
        verified_count = unverified_profiles.count()
        
        if verified_count > 0:
            unverified_profiles.update(email_verified=True)
            
            if already_verified_count > 0:
                self.message_user(
                    request, 
                    f'📧 Verified {verified_count} emails. ✅ {already_verified_count} were already verified.', 
                    messages.SUCCESS
                )
            else:
                self.message_user(
                    request, 
                    f'📧 Verified {verified_count} emails.', 
                    messages.SUCCESS
                )
        else:
            self.message_user(
                request, 
                f'✅ All {already_verified_count} selected profiles already have verified emails.', 
                messages.INFO
            )
    
    verify_emails_selected.short_description = "📧 VERIFY EMAILS only (no approval)"
    
    def reject_selected(self, request, queryset):
        count = queryset.count()
        queryset.update(is_approved=False, approval_status='rejected')
        self.message_user(request, f'❌ Rejected {count} profiles.', messages.SUCCESS)
    
    reject_selected.short_description = "❌ Reject selected"
    
    def request_changes(self, request, queryset):
        count = queryset.count()
        queryset.update(approval_status='changes_requested')
        self.message_user(request, f'✏️ Requested changes for {count} profiles.', messages.SUCCESS)
    
    request_changes.short_description = "✏️ Request changes"
    
    def resend_verification(self, request, queryset):
        """Resend verification email to selected users"""
        unverified = queryset.filter(email_verified=False)
        sent_count = 0
        
        for profile in unverified:
            try:
                # Update token and send time
                import secrets
                profile.email_verification_token = secrets.token_urlsafe(32)
                profile.email_verification_sent_at = timezone.now()
                profile.save()
                
                # Send verification email
                verification_url = request.build_absolute_uri(
                    reverse('verify_email', kwargs={'token': profile.email_verification_token})
                )
                
                from .utils.emails import send_email_verification_email
                # ✅ FIXED: Correct function signature
                success = send_email_verification_email(
                    user_email=profile.user.email,
                    username=profile.user.username,
                    verification_url=verification_url
                )
                
                if success:
                    sent_count += 1
                    
            except Exception as e:
                self.message_user(
                    request, 
                    f'Error sending to {profile.user.email}: {str(e)}', 
                    messages.ERROR
                )
        
        if sent_count > 0:
            self.message_user(
                request, 
                f'📧 Sent verification emails to {sent_count} users.', 
                messages.SUCCESS
            )
        else:
            self.message_user(
                request, 
                'No verification emails sent - all selected profiles are already verified or there was an error.', 
                messages.WARNING
            )
    
    resend_verification.short_description = "📧 Resend verification email"
    
    def send_email_verification_reminder(self, request, queryset):
        """Send email verification reminder to selected users"""
        from django.utils import timezone
        from .utils.emails import send_verification_reminder
        
        unverified = queryset.filter(email_verified=False)
        sent_count = 0
        
        for profile in unverified:
            if send_verification_reminder(profile.user, request):
                profile.email_verification_reminder_count += 1
                profile.email_verification_last_reminder_sent = timezone.now()
                profile.save()
                sent_count += 1
        
        if sent_count > 0:
            self.message_user(
                request, 
                f'📧 Sent email verification reminders to {sent_count} users.', 
                messages.SUCCESS
            )
        else:
            self.message_user(
                request, 
                'No email verification reminders sent - all selected profiles are already verified.', 
                messages.WARNING
            )
    
    send_email_verification_reminder.short_description = "📧 Send email verification reminders"
    
    def send_profile_completion_reminder(self, request, queryset):
        """Send profile completion reminder to selected users"""
        from django.utils import timezone
        from .utils.emails import send_profile_completion_reminder
        
        incomplete = queryset.filter(is_complete=False)
        sent_count = 0
        
        for profile in incomplete:
            if send_profile_completion_reminder(profile.user, request):
                profile.profile_completion_reminder_count += 1
                profile.profile_completion_last_reminder_sent = timezone.now()
                profile.save()
                sent_count += 1
        
        if sent_count > 0:
            self.message_user(
                request, 
                f'📝 Sent profile completion reminders to {sent_count} users.', 
                messages.SUCCESS
            )
        else:
            self.message_user(
                request, 
                'No profile completion reminders sent - all selected profiles are already complete.', 
                messages.WARNING
            )
    
    send_profile_completion_reminder.short_description = "📝 Send profile completion reminders"
    
    def mark_for_deletion(self, request, queryset):
        """Mark selected profiles for deletion"""
        from django.utils import timezone
        updated = queryset.update(
            marked_for_deletion=True,
            marked_for_deletion_at=timezone.now()
        )
        self.message_user(
            request, 
            f'🚨 Marked {updated} profiles for deletion.', 
            messages.WARNING
        )
    
    mark_for_deletion.short_description = "🚨 Mark selected for deletion"
    
    def unmark_for_deletion(self, request, queryset):
        """Unmark selected profiles from deletion"""
        updated = queryset.update(
            marked_for_deletion=False,
            marked_for_deletion_at=None
        )
        self.message_user(
            request, 
            f'✅ Unmarked {updated} profiles from deletion.', 
            messages.SUCCESS
        )
    
    unmark_for_deletion.short_description = "✅ Unmark from deletion"

    # ✅ MOBILE-FRIENDLY CHANGE LIST
    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        
        # Mobile-optimized stats
        stats = {
            'total': Profile.objects.count(),
            'pending': Profile.objects.filter(approval_status='pending_review').count(),
            'unverified': Profile.objects.filter(email_verified=False).count(),
            'marked_for_deletion': Profile.objects.filter(marked_for_deletion=True).count(),
            'approved_with_state': Profile.objects.filter(
                is_approved=True, 
                approved_content_snapshot__isnull=False
            ).count(),
        }
        
        extra_context['stats'] = stats
        return super().changelist_view(request, extra_context=extra_context)

    # ✅ MOBILE CSS
    class Media:
        css = {
            'all': (
                '@media (max-width: 768px) { '
                '.profile-admin-mobile { font-size: 12px; } '
                '}',
            )
        }

# ✅ ENHANCED PROFILE IMAGE ADMIN WITH SECURITY FIELDS
@admin.register(ProfileImage)
class ProfileImageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'image_preview', 'image_type', 'is_primary', 'needs_approval', 'is_approved', 'created_at')
    list_filter = ('image_type', 'is_primary', 'needs_approval', 'is_approved', 'created_at')
    search_fields = ('profile__user__username', 'profile__user__email')
    list_per_page = 20
    readonly_fields = ('image_preview_large', 'created_at')
    
    fieldsets = (
        ('Image Info', {
            'fields': ('profile', 'image_preview_large', 'image')
        }),
        ('Settings', {
            'fields': ('image_type', 'is_primary')
        }),
        ('Approval Workflow', {
            'fields': ('needs_approval', 'is_approved', 'replaced_image'),
            'description': 'Security: New photos for approved profiles need admin approval'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            border_color = "#28a745" if obj.is_approved else "#ffc107"
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px; border-radius: 4px; border: 2px solid {};" />',
                obj.image.url, border_color
            )
        return "No image"
    image_preview.short_description = 'Preview'
    
    def image_preview_large(self, obj):
        if obj.image:
            border_color = "#28a745" if obj.is_approved else "#ffc107"
            border_style = "solid" if obj.is_approved else "dashed"
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 300px; border-radius: 8px; border: 3px {} {};" />',
                obj.image.url, border_style, border_color
            )
        return "No image"
    image_preview_large.short_description = 'Large Preview'

# ✅ EMAIL REMINDER LOG ADMIN
@admin.register(EmailReminderLog)
class EmailReminderLogAdmin(admin.ModelAdmin):
    list_display = ['profile', 'reminder_type', 'sent_at', 'was_successful']
    list_filter = ['reminder_type', 'was_successful', 'sent_at']
    search_fields = ['profile__user__username', 'profile__user__email']
    readonly_fields = ['profile', 'reminder_type', 'sent_at', 'was_successful', 'error_message']
    list_per_page = 20
    
    def has_add_permission(self, request):
        return False

# ✅ FIXED: Message Admin - uses 'message' field instead of 'content'
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'message_preview', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'recipient__username', 'text')
    list_per_page = 20
    
    def message_preview(self, obj):
        # Use 'text' field instead of 'content'
        if hasattr(obj, 'text'):
            return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
        elif hasattr(obj, 'content'):
            return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
        else:
            return "No message content"
    message_preview.short_description = 'Message'

# ✅ FIXED: UserActivityAdmin with proper error handling
@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = [
        'user', 
        'action', 
        'timestamp', 
        'is_bot_display',
        'bot_category_display',
        'ip_address',
    ]
    
    list_filter = [
        'action',
        'timestamp',
    ]
    
    search_fields = [
        'user__username',
        'user__email', 
        'ip_address',
        'user_agent',
    ]
    
    readonly_fields = [
        'user', 'action', 'timestamp', 'ip_address', 'user_agent',
        'target_object_id', 'target_content_type', 'extra_data',
        'is_bot_display', 'bot_category_display', 'bot_type_display', 
        'all_extra_data_display'
    ]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'action', 'timestamp')
        }),
        ('Request Details', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Bot Detection', {
            'fields': ('is_bot_display', 'bot_category_display', 'bot_type_display')
        }),
        ('Target Object', {
            'fields': ('target_content_type', 'target_object_id'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('all_extra_data_display', 'extra_data'),
            'classes': ('collapse',)
        }),
    )
    
    def is_bot_display(self, obj):
        """Display bot status from extra_data"""
        is_bot = obj.extra_data.get('is_bot', False) if obj.extra_data else False
        color = '#dc3545' if is_bot else '#28a745'
        icon = '🤖' if is_bot else '👤'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, 'Bot' if is_bot else 'Human'
        )
    is_bot_display.short_description = 'Bot Status'
    
    def bot_category_display(self, obj):
        """Display bot category from extra_data"""
        if not obj.extra_data:
            return format_html('<span style="color: #6c757d;">—</span>')
        
        category = obj.extra_data.get('bot_category', 'human')
        category_map = {
            'human': ('👤', 'Human', '#28a745'),
            'social_media': ('📱', 'Social Media', '#17a2b8'),
            'search_engine': ('🔍', 'Search Engine', '#6f42c1'),
            'ai_assistant': ('🤖', 'AI Assistant', '#e83e8c'),
            'monitoring': ('📊', 'Monitoring', '#fd7e14'),
            'seo_tool': ('⚡', 'SEO Tool', '#20c997'),
            'unknown': ('❓', 'Unknown Bot', '#6c757d')
        }
        
        # ✅ FIXED: Proper error handling for unknown categories
        if category in category_map:
            icon, text, color = category_map[category]
        else:
            # Handle unknown categories safely
            icon, text, color = '❓', str(category).title() if category else 'Unknown', '#6c757d'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, text
        )
    bot_category_display.short_description = 'Bot Category'
    
    def bot_type_display(self, obj):
        """Display bot type from extra_data"""
        if not obj.extra_data:
            return format_html('<span style="color: #28a745;">👤 Human</span>')
        
        bot_type = obj.extra_data.get('bot_type', 'human')
        if bot_type == 'human':
            return format_html('<span style="color: #28a745;">👤 Human</span>')
        else:
            # ✅ FIXED: Handle None or unexpected bot_type values
            display_type = str(bot_type) if bot_type else 'Unknown'
            return format_html('<span style="color: #dc3545;">🤖 {}</span>', display_type)
    bot_type_display.short_description = 'Bot Type'
    
    def all_extra_data_display(self, obj):
        """Display all extra_data in a readable format"""
        if not obj.extra_data:
            return "No additional data"
        
        items = []
        for key, value in obj.extra_data.items():
            if isinstance(value, bool):
                display_value = '✅ Yes' if value else '❌ No'
            elif value is None:
                display_value = '—'
            else:
                display_value = str(value)
            
            items.append(
                f'<tr><td style="padding: 4px 8px; border-bottom: 1px solid #eee;"><strong>{key}:</strong></td>'
                f'<td style="padding: 4px 8px; border-bottom: 1px solid #eee;">{display_value}</td></tr>'
            )
        
        return format_html(
            '<table style="width: 100%; border-collapse: collapse;">{}</table>',
            ''.join(items)
        )
    all_extra_data_display.short_description = 'All Extra Data'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

# ✅ CUSTOM ADMIN URLS FOR QUICK ACTIONS
def get_admin_urls():
    urls = [
        path('approve-profile/<int:profile_id>/', admin.site.admin_view(approve_profile), name='approve_profile'),
        path('reject-profile/<int:profile_id>/', admin.site.admin_view(reject_profile), name='reject_profile'),
        path('request-changes/<int:profile_id>/', admin.site.admin_view(request_changes), name='request_changes'),
        path('resend-verification/<int:profile_id>/', admin.site.admin_view(resend_verification), name='resend_verification'),
        path('view-live-profile/<int:profile_id>/', admin.site.admin_view(view_live_profile), name='view_live_profile'),
    ]
    return urls

# ✅ SAFE: Add custom URLs to existing admin site
original_get_urls = admin.site.get_urls

def custom_get_urls():
    return get_admin_urls() + original_get_urls()

admin.site.get_urls = custom_get_urls

# ✅ ENHANCED ADMIN SITE WITH BETTER DASHBOARD
class CustomAdminSite(admin.AdminSite):
    def get_app_list(self, request):
        """Add custom links to the admin index"""
        app_list = super().get_app_list(request)
        
        if request.user.is_staff:
            # Get quick stats for the admin dashboard
            pending_count = Profile.objects.filter(approval_status='pending_review').count()
            unverified_count = Profile.objects.filter(email_verified=False).count()
            deletion_count = Profile.objects.filter(marked_for_deletion=True).count()
            approved_with_state = Profile.objects.filter(
                is_approved=True, 
                approved_content_snapshot__isnull=False
            ).count()
            
            custom_app = {
                'name': '🚀 Quick Actions',
                'app_label': 'quick_actions',
                'app_url': '/admin/',
                'has_module_perms': True,
                'models': [
                    {
                        'name': f'📊 Pending Review ({pending_count})',
                        'object_name': 'pending_profiles',
                        'admin_url': '/admin/pages/profile/?approval_status=needs_review',
                        'view_only': True,
                    },
                    {
                        'name': f'⚠️ Unverified ({unverified_count})', 
                        'object_name': 'unverified_emails',
                        'admin_url': '/admin/pages/profile/?email_verified__exact=0',
                        'view_only': True,
                    },
                    {
                        'name': f'🚨 Marked for Deletion ({deletion_count})', 
                        'object_name': 'marked_for_deletion',
                        'admin_url': '/admin/pages/profile/?marked_for_deletion__exact=1',
                        'view_only': True,
                    },
                    {
                        'name': f'📸 Protected Profiles ({approved_with_state})', 
                        'object_name': 'protected_profiles',
                        'admin_url': '/admin/pages/profile/?is_approved__exact=1&approved_content_snapshot__isnull=False',
                        'view_only': True,
                    },
                ],
            }
            app_list.append(custom_app)
        
        return app_list

# ✅ SAFE: Apply custom admin site without replacing
admin.site.__class__ = CustomAdminSite

# ✅ PROFILE INLINE FOR USER ADMIN
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ('headline', 'location', 'is_approved', 'email_verified', 'approval_status')
    readonly_fields = ('is_approved', 'email_verified', 'approval_status')
    
    def has_add_permission(self, request, obj=None):
        return False

# ✅ ENHANCED USER ADMIN
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'date_joined', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')

# ✅ OTHER MODEL ADMINS (SIMPLIFIED FOR MOBILE)
@admin.register(AdminMessage)
class AdminMessageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'admin_user', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('profile__user__username', 'message')
    list_per_page = 20

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('user_a', 'user_b', 'created_at', 'updated_at')
    list_per_page = 20

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('liker', 'liked_user', 'created_at')
    list_per_page = 20

@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    list_per_page = 20

@admin.register(PrivateAccessRequest)
class PrivateAccessRequestAdmin(admin.ModelAdmin):
    list_display = ('requester', 'target_user', 'status', 'created_at')
    list_filter = ('status',)
    list_per_page = 20

@admin.register(HotDate)
class HotDateAdmin(admin.ModelAdmin):
    list_display = ('host', 'activity', 'date_time', 'area', 'is_active')
    list_filter = ('is_active', 'area')
    list_per_page = 20

@admin.register(HotDateView)
class HotDateViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'hot_date', 'viewed_at')
    list_per_page = 20

@admin.register(HotDateNotification)
class HotDateNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'hot_date', 'notification_type', 'is_read')
    list_filter = ('is_read', 'notification_type')
    list_per_page = 20

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ['title', 'position', 'status', 'published_at', 'is_published']
    list_editable = ['position', 'status']
    prepopulated_fields = {'slug': ('title',)}
    list_per_page = 20

# ✅ REGISTER CUSTOM USER ADMIN
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, CustomUserAdmin)

# ✅ MOBILE RESPONSIVE CSS
class MobileAdminSite(admin.AdminSite):
    def each_context(self, request):
        context = super().each_context(request)
        context['is_mobile'] = request.user_agent.is_mobile if hasattr(request, 'user_agent') else False
        return context

# Apply mobile enhancements
admin.site.__class__ = MobileAdminSite
# Deployment trigger
