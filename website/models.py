# models.py - COMPLETE WITH MESSAGING MODELS AND LEGAL COMPLIANCE
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import date
import json

class Conversation(models.Model):
    """Conversation between two users"""
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        usernames = [user.username for user in self.participants.all()]
        return f"Conversation: {' & '.join(usernames)}"

class Message(models.Model):
    """Individual message in a conversation - WITH LEGAL COMPLIANCE"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    
    # === LEGAL COMPLIANCE FIELDS ===
    is_deleted_for_sender = models.BooleanField(default=False)
    is_deleted_for_receiver = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, 
                                   on_delete=models.SET_NULL, related_name='deleted_messages')
    # ================================
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
    
    def is_visible_to(self, user):
        """Check if message is visible to a specific user (for legal compliance)"""
        if user == self.sender:
            return not self.is_deleted_for_sender
        elif user in self.conversation.participants.all():
            return not self.is_deleted_for_receiver
        return True  # Admin can always see
    
    @property
    def receiver(self):
        """Get the other participant in the conversation"""
        other_participants = self.conversation.participants.exclude(id=self.sender.id)
        return other_participants.first() if other_participants.exists() else None

# === NEW MODEL FOR LEGAL COMPLIANCE ===
class UserActivityLog(models.Model):
    """Log all user activities for legal compliance and admin monitoring"""
    ACTIVITY_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('message_sent', 'Message Sent'),
        ('message_received', 'Message Received'),
        ('message_deleted', 'Message Deleted'),
        ('profile_view', 'Profile Viewed'),
        ('like_given', 'Like Given'),
        ('like_received', 'Like Received'),
        ('favorite', 'Favorite Toggled'),
        ('block', 'Block Toggled'),
        ('date_created', 'Date Created'),
        ('date_joined', 'Date Joined'),
        ('date_cancelled', 'Date Cancelled'),
        ('profile_edit', 'Profile Edited'),
        ('profile_edit_request', 'Profile Edit Requested'),
        ('profile_approved', 'Profile Approved'),
        ('profile_rejected', 'Profile Rejected'),
        ('private_access_requested', 'Private Access Requested'),
        ('private_access_granted', 'Private Access Granted'),
        ('private_access_revoked', 'Private Access Revoked'),
        ('private_access_denied', 'Private Access Denied'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_logs')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, 
                                   on_delete=models.SET_NULL, related_name='targeted_activities')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    additional_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['activity_type', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]
        verbose_name = 'User Activity Log'
        verbose_name_plural = 'User Activity Logs'
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.created_at}"

# === NEW MODEL FOR FIXING PRIVATE IMAGES BUG ===
class UserIdMapping(models.Model):
    """
    Maps external system profile/user IDs to Django user IDs.
    Critical for fixing private images showing on wrong profiles.
    """
    external_profile_id = models.IntegerField(unique=True, help_text="ID from external profile system")
    external_user_id = models.IntegerField(help_text="user_id from external profile system")
    django_user_id = models.IntegerField(help_text="Actual Django user.id")
    username = models.CharField(max_length=150, help_text="Username for verification")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_id_mapping'
        verbose_name = 'User ID Mapping'
        verbose_name_plural = 'User ID Mappings'
        indexes = [
            models.Index(fields=['external_profile_id']),
            models.Index(fields=['username']),
            models.Index(fields=['django_user_id']),
        ]
    
    def __str__(self):
        return f"{self.external_profile_id} → {self.django_user_id} ({self.username})"
    
    @classmethod
    def get_django_user_id(cls, external_profile_id, external_user_id=None):
        """Get Django user_id for external profile_id"""
        try:
            if external_user_id:
                mapping = cls.objects.get(
                    external_profile_id=external_profile_id,
                    external_user_id=external_user_id
                )
            else:
                mapping = cls.objects.get(external_profile_id=external_profile_id)
            return mapping.django_user_id
        except cls.DoesNotExist:
            return None

# ======================================

class PrivateAccessRequest(models.Model):
    """
    Model for tracking private photo access requests between users
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('granted', 'Granted'),
        ('denied', 'Denied'),
        ('revoked', 'Revoked'),
    ]
    
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='private_access_requests_sent'
    )
    
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='private_access_requests_received'
    )
    
    message = models.TextField(
        blank=True,
        help_text='Optional message explaining why access is requested'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    denied_at = models.DateTimeField(null=True, blank=True)
    
    # Reason for denial/revocation
    reason = models.TextField(blank=True, help_text='Reason for denying or revoking access')
    
    class Meta:
        unique_together = ['requester', 'target_user']
        ordering = ['-created_at']
        verbose_name = 'Private Access Request'
        verbose_name_plural = 'Private Access Requests'
    
    def __str__(self):
        return f"{self.requester.username} -> {self.target_user.username} ({self.status})"
    
    def grant(self):
        """Grant access to private photos"""
        self.status = 'granted'
        self.granted_at = timezone.now()
        self.revoked_at = None
        self.denied_at = None
        self.save()
    
    def deny(self, reason=''):
        """Deny access request"""
        self.status = 'denied'
        self.denied_at = timezone.now()
        self.reason = reason
        self.save()
    
    def revoke(self, reason=''):
        """Revoke previously granted access"""
        self.status = 'revoked'
        self.revoked_at = timezone.now()
        self.reason = reason
        self.save()
    
    def is_active(self):
        """Check if access is currently active"""
        return self.status == 'granted'
    
    def get_duration(self):
        """Get how long access has been granted"""
        if self.status == 'granted' and self.granted_at:
            return timezone.now() - self.granted_at
        return None

# === ADDED PRIVATE IMAGE MODEL ===
class PrivateImage(models.Model):
    """
    Model for storing private images that require access approval
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='private_images'
    )
    image = models.ImageField(upload_to='private_images/%Y/%m/%d/')
    caption = models.CharField(max_length=200, blank=True)
    position = models.IntegerField(default=1, help_text="Position for ordering (1-5)")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['position', 'uploaded_at']
        verbose_name = 'Private Image'
        verbose_name_plural = 'Private Images'
    
    def __str__(self):
        return f"Private image {self.position} for {self.user.username}"

class UserProfile(models.Model):
    # Step 1: Basic Information
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    
    RELATIONSHIP_STATUS = [
        ('single', 'Single'),
        ('divorced', 'Divorced'),
        ('separated', 'Separated'),
        ('widowed', 'Widowed'),
    ]
    relationship_status = models.CharField(max_length=20, choices=RELATIONSHIP_STATUS, default='single')
    
    BODY_TYPES = [
        ('slim', 'Slim'),
        ('athletic', 'Athletic'),
        ('average', 'Average'),
        ('curvy', 'Curvy'),
        ('full_figured', 'Full Figured'),
    ]
    body_type = models.CharField(max_length=20, choices=BODY_TYPES, default='average')
    
    has_children = models.BooleanField(default=False)
    children_details = models.TextField(blank=True)
    is_smoker = models.BooleanField(default=False)
    location = models.CharField(max_length=100, default='Unknown')
    
    @property
    def profile_heading(self):
        """For templates expecting profile_heading - maps to profile_name"""
        return self.profile_name or ""
    
    @property
    def about_you(self):
        """For templates expecting about_you - maps to story"""
        return self.story or ""
    
    @property
    def display_age(self):
        """Calculate age from date_of_birth"""
        if self.date_of_birth:
            today = date.today()
            age = today.year - self.date_of_birth.year
            if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
                age -= 1
            return age
        return 25
    
    @property
    def username(self):
        """For templates expecting username on profile object"""
        return self.user.username if self.user else ""

    # NEW FIELDS FOR CSV COMPATIBILITY
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    height = models.CharField(max_length=20, blank=True, default='')
    gender = models.CharField(max_length=20, choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], blank=True, default='')
    looking_for = models.TextField(blank=True, default='')
    
    # IMAGE URL FIELDS FOR CSV MIGRATION
    profile_image_url = models.URLField(max_length=500, blank=True, null=True, help_text="Original CSV profile image URL")
    
    # Step 2: About Me & Personality
    story = models.TextField(default='No story provided yet.')
    personality_traits = models.JSONField(default=list)
    communication_style = models.CharField(max_length=100, default='Friendly')
    life_priorities = models.JSONField(default=list)
    core_values = models.JSONField(default=list)
    
    # Step 3: Preferences & Interests
    arrangement_preferences = models.JSONField(default=dict)
    lifestyle_interests = models.JSONField(default=list)
    preferred_age_min = models.IntegerField(
        validators=[MinValueValidator(18), MaxValueValidator(100)],
        default=25
    )
    preferred_age_max = models.IntegerField(
        validators=[MinValueValidator(18), MaxValueValidator(100)],
        default=45
    )
    preferred_distance = models.IntegerField(default=50)
    
    # Step 4: Trust & Privacy (NOT VERIFICATION)
    TRUST_LEVELS = [
        ('unverified', 'Unverified'),
        ('basic', 'Basic Trust'),
        ('enhanced', 'Enhanced Trust'),
        ('premium', 'Premium Trust'),
    ]
    trust_level = models.CharField(
        max_length=20,
        choices=TRUST_LEVELS,
        default='unverified'
    )
    privacy_settings = models.JSONField(default=dict)
    notification_preferences = models.JSONField(default=dict)
    
    # Step 5: Email Verification - ADDED FIELD
    email_verified = models.BooleanField(default=False)
    
    # System fields
    is_complete = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.profile_name} - {self.user.username}"

    def get_profile_image_url(self):
        """Get the best available profile image URL"""
        if self.profile_photo:
            return self.profile_photo.url
        elif self.profile_image_url:
            return self.profile_image_url
        return None

    def get_additional_images(self):
        """Get all additional images for this profile"""
        return self.images.filter(image_type='additional').order_by('position')

    def get_private_images(self):
        """Get all private images for this profile"""
        return PrivateImage.objects.filter(user=self.user, is_active=True).order_by('position')

    def has_private_images(self):
        """Check if user has any private images uploaded"""
        return PrivateImage.objects.filter(user=self.user, is_active=True).exists()
    
    def has_private_access_for(self, requesting_user):
        """Check if requesting user has access to private images"""
        if requesting_user == self.user:
            return True
        
        return PrivateAccessRequest.objects.filter(
            requester=requesting_user,
            target_user=self.user,
            status='granted'
        ).exists()

class UserProfileImage(models.Model):
    IMAGE_TYPES = [
        ('additional', 'Additional Image'),
        ('private', 'Private Image'),
    ]
    
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField(max_length=500)
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES)
    position = models.IntegerField(default=0, help_text="Position for ordering: 1-4 for additional, 1-5 for private")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['image_type', 'position']
        unique_together = ['user_profile', 'image_type', 'position']
        verbose_name = 'User Profile Image'
        verbose_name_plural = 'User Profile Images'

    def __str__(self):
        return f"{self.user_profile.profile_name} - {self.image_type} {self.position}"

    # ADD THESE HELPER PROPERTIES
    @property
    def is_private(self):
        """Helper property to check if image is private"""
        return self.image_type == 'private'
    
    @property
    def is_additional(self):
        """Helper property to check if image is additional"""
        return self.image_type == 'additional'

class ProfileEditRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='edit_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # All editable fields (mirroring UserProfile)
    profile_name = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    relationship_status = models.CharField(max_length=20, blank=True, null=True)
    body_type = models.CharField(max_length=20, blank=True, null=True)
    has_children = models.BooleanField(default=False, null=True)
    children_details = models.TextField(blank=True, null=True)
    is_smoker = models.BooleanField(default=False, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    
    # CSV Compatibility Fields
    profile_photo = models.ImageField(upload_to='pending_profile_photos/', null=True, blank=True)
    height = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    looking_for = models.TextField(blank=True, null=True)
    
    # About Me & Personality
    story = models.TextField(blank=True, null=True)
    personality_traits = models.JSONField(default=list, blank=True, null=True)
    communication_style = models.CharField(max_length=100, blank=True, null=True)
    life_priorities = models.JSONField(default=list, blank=True, null=True)
    core_values = models.JSONField(default=list, blank=True, null=True)
    
    # Preferences & Interests
    arrangement_preferences = models.JSONField(default=dict, blank=True, null=True)
    lifestyle_interests = models.JSONField(default=list, blank=True, null=True)
    preferred_age_min = models.IntegerField(null=True, blank=True)
    preferred_age_max = models.IntegerField(null=True, blank=True)
    preferred_distance = models.IntegerField(null=True, blank=True)
    
    # Trust & Privacy
    trust_level = models.CharField(max_length=20, blank=True, null=True)
    privacy_settings = models.JSONField(default=dict, blank=True, null=True)
    notification_preferences = models.JSONField(default=dict, blank=True, null=True)
    
    # Admin fields
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_changed_fields(self):
        """Compare with current profile and return list of changed field names"""
        try:
            current_profile = self.user.profile
            changed_fields = []
            
            profile_fields = [
                'profile_name', 'date_of_birth', 'relationship_status', 'body_type',
                'has_children', 'children_details', 'is_smoker', 'location', 'story',
                'personality_traits', 'communication_style', 'life_priorities', 'core_values',
                'arrangement_preferences', 'lifestyle_interests', 'preferred_age_min',
                'preferred_age_max', 'preferred_distance', 'trust_level', 'privacy_settings',
                'notification_preferences', 'height', 'gender', 'looking_for'
            ]
            
            for field in profile_fields:
                current_value = getattr(current_profile, field)
                new_value = getattr(self, field)
                
                if current_value != new_value:
                    changed_fields.append(field)
            
            if self.profile_photo:
                changed_fields.append('profile_photo')
                
            return changed_fields
        except UserProfile.DoesNotExist:
            return []
    
    def approve(self, admin_user, notes=''):
        """Approve the changes and update the user's profile"""
        try:
            profile = self.user.profile
            changed_fields = self.get_changed_fields()
            
            for field in changed_fields:
                if field != 'profile_photo':
                    setattr(profile, field, getattr(self, field))
            
            if self.profile_photo:
                profile.profile_photo = self.profile_photo
            
            profile.save()
            
            # Update request status
            self.status = 'approved'
            self.reviewed_by = admin_user
            self.reviewed_at = timezone.now()
            self.admin_notes = notes
            self.save()
            
            # Log the activity
            from .signals import log_user_activity
            log_user_activity(
                user=admin_user,
                activity_type='profile_approved',
                target_user=self.user,
                additional_data={
                    'request_id': self.id,
                    'changed_fields': changed_fields,
                }
            )
            
            # Send approval email
            self._send_approval_email()
            
            return True
        except Exception as e:
            print(f"Error approving profile edit request: {e}")
            return False
    
    def reject(self, admin_user, notes=''):
        """Reject the changes"""
        self.status = 'rejected'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.admin_notes = notes
        self.save()
        
        # Log the activity
        from .signals import log_user_activity
        log_user_activity(
            user=admin_user,
            activity_type='profile_rejected',
            target_user=self.user,
            additional_data={
                'request_id': self.id,
                'admin_notes': notes,
            }
        )
        
        # Send rejection email
        self._send_rejection_email()
    
    def _send_approval_email(self):
        """Send email notification to user about approval"""
        subject = 'Profile Update Approved'
        html_message = render_to_string('emails/profile_update_approved.html', {
            'user': self.user,
            'edit_request': self,
            'changed_fields': self.get_changed_fields(),
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [self.user.email],
            html_message=html_message,
        )
    
    def _send_rejection_email(self):
        """Send email notification to user about rejection"""
        subject = 'Profile Update Rejected'
        html_message = render_to_string('emails/profile_update_rejected.html', {
            'user': self.user,
            'edit_request': self,
            'admin_notes': self.admin_notes,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [self.user.email],
            html_message=html_message,
        )
    
    def __str__(self):
        return f"Edit Request - {self.user.username} ({self.status})"

class TrustIndicator(models.Model):
    """Tracks trust-building activities - NOT VERIFICATION"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    indicator_type = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Trust Indicator"
        verbose_name_plural = "Trust Indicators"
        permissions = [
            ("can_view_trust_indicators", "Can view trust indicators"),
        ]

class LegalConsent(models.Model):
    """Tracks user consent to legal terms"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    terms_version = models.CharField(max_length=50)
    privacy_version = models.CharField(max_length=50)
    safety_acknowledged = models.BooleanField(default=False)
    consent_date = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Legal Consent"
        verbose_name_plural = "Legal Consents"

    def __str__(self):
        return f"{self.user.email} - {self.consent_date}"

class BlogPost(models.Model):
    POSITION_CHOICES = [
        (1, 'Featured - Top Position'),
        (2, 'Standard - High Priority'),
        (3, 'Regular - Normal Priority'),
        (4, 'Archive - Lower Priority'),
    ]
    
    CATEGORY_CHOICES = [
        ('dating-advice', 'Dating Advice'),
        ('online-safety', 'Online Dating Safety'),
        ('elite-dating', 'Elite Dating Insights'),
        ('success-stories', 'Success Stories'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    content = models.TextField()
    excerpt = models.TextField(max_length=300, help_text="Brief summary for blog listing")
    featured_image = models.ImageField(
        upload_to='blog/%Y/%m/%d/',
        help_text="Optimal size: 1200x630px for social sharing"
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    published_date = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=False)
    position = models.IntegerField(choices=POSITION_CHOICES, default=3)
    category = models.CharField(
        max_length=50, 
        choices=CATEGORY_CHOICES, 
        default='dating-advice',
        help_text="Select blog post category"
    )
    meta_title = models.CharField(max_length=200, blank=True, help_text="Optional custom title for SEO")
    meta_description = models.TextField(max_length=300, blank=True, help_text="Optional custom description for SEO")

    class Meta:
        ordering = ['position', '-published_date']
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog_post', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if self.is_published and not self.published_date:
            self.published_date = timezone.now()
        super().save(*args, **kwargs)

class UserLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes_given')
    liked_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'liked_user_id']

class UserFavorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    favorite_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'favorite_user_id']

class UserBlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks')
    blocked_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'blocked_user_id']

class DateEvent(models.Model):
    ACTIVITY_CHOICES = [
        ('Coffee', 'Coffee'),
        ('Drinks / Wine Bar', 'Drinks / Wine Bar'),
        ('Dinner', 'Dinner'),
        ('Walk / Park', 'Walk / Park'),
        ('Gallery / Museum', 'Gallery / Museum'),
        ('Movie', 'Movie'),
        ('Live Music / Comedy', 'Live Music / Comedy'),
        ('Surprise Me', 'Surprise Me'),
    ]
    
    VIBE_CHOICES = [
        ('Chill', 'Chill'),
        ('Classy', 'Classy'),
        ('Adventurous', 'Adventurous'),
        ('Playful', 'Playful'),
        ('Quiet', 'Quiet'),
    ]
    
    BUDGET_CHOICES = [
        ('Free', 'Free'),
        ('$', '$'),
        ('$$', '$$'),
        ('$$$', '$$$'),
        ('Each pays their way', 'Each pays their way'),
    ]
    
    DURATION_CHOICES = [
        ('45 min', '45 min'),
        ('60 min', '60 min'),
        ('90 min', '90 min'),
        ('2 hours', '2 hours'),
        ('3 hours', '3 hours'),
    ]
    
    GROUP_SIZE_CHOICES = [
        ('1_on_1', '1 on 1'),
        ('small_group', 'Small group (3-4)'),
        ('group', 'Group (5+)'),
    ]
    
    AUDIENCE_CHOICES = [
        ('anyone', 'Anyone'),
        ('women_only', 'Women only'),
        ('men_only', 'Men only'),
    ]

    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_dates')
    title = models.CharField(max_length=200)
    activity = models.CharField(max_length=100, choices=ACTIVITY_CHOICES)
    vibe = models.CharField(max_length=100, choices=VIBE_CHOICES)
    budget = models.CharField(max_length=50, choices=BUDGET_CHOICES)
    duration = models.CharField(max_length=50, choices=DURATION_CHOICES)
    date_time = models.DateTimeField()
    area = models.CharField(max_length=100)
    group_size = models.CharField(max_length=50, choices=GROUP_SIZE_CHOICES)
    audience = models.CharField(max_length=50, choices=AUDIENCE_CHOICES)
    is_cancelled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date_time']
        verbose_name = 'Date Event'
        verbose_name_plural = 'Date Events'

    def __str__(self):
        return f"{self.title} by {self.host.username}"

    def get_audience_display(self):
        return dict(self.AUDIENCE_CHOICES).get(self.audience, self.audience)

    def get_group_size_display(self):
        return dict(self.GROUP_SIZE_CHOICES).get(self.group_size, self.group_size)

    def is_upcoming(self):
        return self.date_time > timezone.now() and not self.is_cancelled

    def is_past(self):
        return self.date_time <= timezone.now()

class DateView(models.Model):
    """Track which users have seen which dates"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_event = models.ForeignKey(DateEvent, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'date_event']
        verbose_name = 'Date View'
        verbose_name_plural = 'Date Views'

    def __str__(self):
        return f"{self.user.username} viewed {self.date_event.title}"
