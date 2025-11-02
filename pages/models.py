# pages/models.py

from __future__ import annotations

from datetime import date
from datetime import timedelta  # ADDED

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType


# ---------------------------------------------------------------------
# Blog
# ---------------------------------------------------------------------
class Blog(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    summary = models.TextField(blank=True)
    excerpt = models.TextField(blank=True)
    hero_image = models.ImageField(upload_to="blog/", blank=True, null=True)
    
    # ADD THIS FIELD:
    position = models.IntegerField(default=0, help_text="Higher numbers appear first")
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-position", "-published_at"]  # This needs the position field

    def __str__(self):
        return self.title

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED and self.published_at is not None

# ---------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------

User = settings.AUTH_USER_MODEL


def _today() -> date:
    return timezone.localdate()


class Profile(models.Model):
    """User's dating profile. One-to-one with the auth user."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # Completion / approval gates
    is_complete = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    needs_review = models.BooleanField(default=False)
    pending_changes = models.JSONField(null=True, blank=True)
    last_submitted_for_approval = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ✅ FIXED: Email Verification Fields (consistent naming)
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True)  # RENAMED
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)  # RENAMED

    # ✅ ADDED: Approval Status Field
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('pending_review', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        default='pending_review'
    )
    
    # ✅ ADDED: Admin Approval Tracking
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_profiles'
    )

    # Basics
    date_of_birth = models.DateField(blank=True, null=True)
    headline = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, blank=True)
    about = models.TextField(blank=True)

    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        NON_BINARY = "nonbinary", "Non-binary"
        UNSPECIFIED = "unspecified", "Prefer not to say"

    my_gender = models.CharField(
        max_length=20, choices=Gender.choices, default=Gender.UNSPECIFIED
    )

    class LookingFor(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        BISEXUAL = "bisexual", "Bi-sexual"
        UNSPECIFIED = "unspecified", "Prefer not to say"

    looking_for = models.CharField(
        max_length=20, choices=LookingFor.choices, default=LookingFor.UNSPECIFIED
    )

    class Children(models.TextChoices):
        PREFER_NOT = "prefer_not", "Prefer not to say"
        YES = "yes", "Yes"
        NONE = "none", "None"

    children = models.CharField(
        max_length=20, choices=Children.choices, default=Children.PREFER_NOT
    )

    # Lifestyle fields with default values
    smoking = models.CharField(max_length=20, default='prefer_not', blank=True)
    drinking = models.CharField(max_length=20, default='prefer_not', blank=True)
    exercise = models.CharField(max_length=20, default='prefer_not', blank=True)
    pets = models.CharField(max_length=20, default='prefer_not', blank=True)
    diet = models.CharField(max_length=20, default='prefer_not', blank=True)

    # Lifestyle / tags (CSV strings)
    my_interests = models.CharField(max_length=600, blank=True)
    must_have_tags = models.CharField(max_length=600, blank=True)

    # Preferences
    preferred_age_min = models.PositiveSmallIntegerField(default=18)
    preferred_age_max = models.PositiveSmallIntegerField(default=60)

    class Distance(models.TextChoices):
        ANY = "any", "Any"
        KM_5 = "5", "5 km"
        KM_10 = "10", "10 km"
        KM_25 = "25", "25 km"
        KM_50 = "50", "50 km"
        KM_100 = "100", "100 km"
        COUNTRY = "country", "Countrywide"

    preferred_distance = models.CharField(
        max_length=20, choices=Distance.choices, default=Distance.ANY
    )

    class Intent(models.TextChoices):
        ANY = "any", "Any"
        FRIENDS = "friends", "New friends"
        CASUAL = "casual", "Casual dating"
        LONGTERM = "longterm", "Long-term"
        MARRIAGE = "marriage", "Marriage"

    preferred_intent = models.CharField(
        max_length=20, choices=Intent.choices, default=Intent.ANY
    )

    def __str__(self) -> str:
        uname = getattr(self.user, "username", None) or (self.user.get_username() if self.user else "user")
        return f"Profile #{self.pk} (@{uname})"

    def allow_full_access(self) -> bool:
        """Full dashboard access only when complete + approved."""
        return bool(self.is_complete and self.is_approved)

    @property
    def age(self) -> int | None:
        """Age in years from DOB, or None if unknown."""
        if not self.date_of_birth:
            return None
        today = _today()
        years = today.year - self.date_of_birth.year
        before_bday = (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        return years - 1 if before_bday else years

    @property
    def primary_image(self) -> "ProfileImage | None":
        return self.images.filter(is_primary=True).first()

    @property
    def primary_image_url(self) -> str | None:
        img = self.primary_image
        try:
            return img.image.url if img else None
        except Exception:
            return None

    # Backwards-compat properties
    @property
    def display_name(self) -> str:
        u = getattr(self, "user", None)
        return getattr(u, "username", "") or (u.get_username() if u else "")

    @property
    def tagline(self) -> str:
        return self.headline or ""

    @property
    def city(self) -> str:
        return self.location or ""

    @property
    def bio(self) -> str:
        return self.about or ""

    @property
    def gender(self) -> str:
        return self.my_gender

    @property
    def pref_age_min(self) -> int:
        return self.preferred_age_min

    @property
    def pref_age_max(self) -> int:
        return self.preferred_age_max

    @property
    def distance(self) -> str:
        return self.preferred_distance

    @property
    def intent(self) -> str:
        return self.preferred_intent

    def get_pending_or_current(self, field_name, default=None):
        """Get pending change value or current field value"""
        if self.pending_changes and field_name in self.pending_changes:
            return self.pending_changes[field_name]
        return getattr(self, field_name, default)


# ---------------------------------------------------------------------
# Profile Images
# ---------------------------------------------------------------------

class ProfileImage(models.Model):
    profile = models.ForeignKey(
        Profile,
        related_name="images",
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to="profiles/")
    is_private = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile"],
                condition=models.Q(is_primary=True),
                name="one_primary_image_per_profile",
            ),
        ]

    def __str__(self) -> str:
        return f"Image #{self.pk} for Profile #{self.profile_id}"


# ---------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------

class Thread(models.Model):
    user_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads_as_a")
    user_b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads_as_b")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = (("user_a", "user_b"),)
        indexes = [models.Index(fields=["user_a", "user_b"])]
        ordering = ['-updated_at']  # ADD THIS LINE TOO
    
    def __str__(self) -> str:
        return f"Thread({self.user_a_id}, {self.user_b_id})"
    
    def get_other_user(self, current_user):  # ADD THIS METHOD
        """Return the other user in the conversation"""
        if self.user_a == current_user:
            return self.user_b
        return self.user_a
    
    @property
    def last_message(self):  # ADD THIS METHOD
        """Return the last message in the thread"""
        return self.messages.order_by('-created_at').first()
    
    @staticmethod
    def canonical_pair(u1_id: int, u2_id: int) -> tuple[int, int]:
        return (u1_id, u2_id) if u1_id < u2_id else (u2_id, u1_id)
    
    @classmethod
    def get_or_create_for(cls, u1, u2):
        a_id, b_id = cls.canonical_pair(u1.id, u2.id)
        obj, _ = cls.objects.get_or_create(user_a_id=a_id, user_b_id=b_id)
        return obj
    
    @classmethod
    def for_user(cls, user):
        from django.db.models import Q
        return cls.objects.filter(Q(user_a=user) | Q(user_b=user))

class Message(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_messages")
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    is_deleted_by_sender = models.BooleanField(default=False)
    is_deleted_by_recipient = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["thread", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Msg(t={self.thread_id} from={self.sender_id} to={self.recipient_id})"

    def is_visible_to_user(self, user):
        if user.is_superuser:
            return True
        if user == self.sender and not self.is_deleted_by_sender:
            return True
        if user == self.recipient and not self.is_deleted_by_recipient:
            return True
        return False

    @property
    def short_text(self):
        return (self.text or "")[:80]


def is_blocked(a, b) -> bool:
    from .models import Block
    return Block.objects.filter(Q(blocker=a, blocked=b) | Q(blocker=b, blocked=a)).exists()


class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="blocks_made", on_delete=models.CASCADE)
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="blocks_received", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ("blocker", "blocked")
    def __str__(self):
        return f"{self.blocker_id} ⟂ {self.blocked_id}"


class Like(models.Model):
    liker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='likes_given')
    liked_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='likes_received')
    active = models.BooleanField(default=True)  # Added this field
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['liker', 'liked_user']
    
    def __str__(self):
        return f"{self.liker.username} likes {self.liked_user.username}"


# ---------------------------------------------------------------------
# Private Access Requests
# ---------------------------------------------------------------------

class PrivateAccessRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"
    
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_requests_made")
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_requests_received")
    message = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_access_requests")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['requester', 'target_user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Access request from {self.requester} to {self.target_user} ({self.status})"

    def is_active(self):
        return self.status == self.Status.APPROVED


# ---------------------------------------------------------------------
# NEW: Admin Messages Model
# ---------------------------------------------------------------------

class AdminMessage(models.Model):
    """Messages from admins to users about profile changes needed"""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="admin_messages")
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_admin_messages")
    message = models.TextField(help_text="What needs to be changed in the profile")
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Admin message to {self.profile.user.username}"


# ---------------------------------------------------------------------
# User Activity Tracking
# ---------------------------------------------------------------------

class UserActivity(models.Model):
    class ActionType(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        VIEW_PROFILE = 'view_profile', 'View Profile'
        UPDATE_PROFILE = 'update_profile', 'Update Profile'
        SEND_MESSAGE = 'send_message', 'Send Message'
        VIEW_BLOG = 'view_blog', 'View Blog'
        SEARCH = 'search', 'Search'
        LIKE = 'like', 'Like'
        BLOCK = 'block', 'Block'
        ADMIN_MESSAGE_SENT = 'admin_message_sent', 'Admin Message Sent'
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=50, choices=ActionType.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    target_content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    extra_data = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "User Activities"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"


# Utility function to log activities
def log_user_activity(user, action, request=None, target_object=None, **extra_data):
    """Log user activity for admin tracking"""
    activity = UserActivity(
        user=user,
        action=action,
        ip_address=request.META.get('REMOTE_ADDR') if request else None,
        user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
        extra_data=extra_data
    )
    
    if target_object:
        activity.target_object_id = target_object.id
        activity.target_content_type = ContentType.objects.get_for_model(target_object)
    
    activity.save()
    return activity


# ---------------------------------------------------------------------
# Hot Dates (ADDED FROM OLDER VERSION)
# ---------------------------------------------------------------------

class HotDate(models.Model):
    """Hot Date - pre-arranged dates that users can join"""
    
    class AudienceType(models.TextChoices):
        ANYONE = "anyone", "Anyone"
        WOMEN_ONLY = "women_only", "Women only"
        MEN_ONLY = "men_only", "Men only"
    
    class GroupSize(models.TextChoices):
        ONE_ON_ONE = "1_on_1", "1 on 1"
        SMALL_GROUP = "small_group", "Small group (3–4)"
        GROUP = "group", "Group (5+)"
    
    # Host and basic info
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_hotdates")
    title = models.CharField(max_length=100, blank=True)  # Auto-generated from activity + vibe
    
    # Date details
    activity = models.CharField(max_length=50)
    vibe = models.CharField(max_length=50)
    budget = models.CharField(max_length=50)
    duration = models.CharField(max_length=20)
    date_time = models.DateTimeField()
    area = models.CharField(max_length=100)
    
    # Group settings
    group_size = models.CharField(max_length=20, choices=GroupSize.choices, default=GroupSize.ONE_ON_ONE)
    audience = models.CharField(max_length=20, choices=AudienceType.choices, default=AudienceType.ANYONE)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_cancelled = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date_time']
    
    def __str__(self):
        return f"Hot Date: {self.activity} by {self.host.username} at {self.date_time}"
    
    def save(self, *args, **kwargs):
        # Auto-generate title from activity + vibe
        if not self.title:
            self.title = f"{self.activity} • {self.vibe}"
        super().save(*args, **kwargs)
    
    @property
    def is_upcoming(self):
        return self.date_time > timezone.now() and not self.is_cancelled


class HotDateParticipant(models.Model):
    """Track participants for Hot Dates"""
    hot_date = models.ForeignKey(HotDate, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="joined_hotdates")
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['hot_date', 'user']
    
    def __str__(self):
        return f"{self.user.username} joined {self.hot_date}"


class HotDateView(models.Model):
    """Track when users view Hot Dates (for notification counting)"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="viewed_hotdates")
    hot_date = models.ForeignKey(HotDate, on_delete=models.CASCADE, related_name="views")
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'hot_date']
    
    def __str__(self):
        return f"{self.user.username} viewed {self.hot_date}"

class HotDateNotification(models.Model):
    """Notifications for Hot Date cancellations and updates"""
    NOTIFICATION_TYPES = [
        ('cancelled', 'Cancelled'),
        ('updated', 'Updated'),
        ('reminder', 'Reminder'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hotdate_notifications')
    hot_date = models.ForeignKey(HotDate, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.hot_date.title}"
