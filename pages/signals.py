# pages/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from .models import Profile, User
from .utils.emails import (
    send_welcome_email,
    send_email_verification_email, 
    send_profile_submitted_email,
    send_profile_approved_email,
    send_admin_notification_email,
    send_reminder_email
)

@receiver(post_save, sender=User)
def handle_new_user_signup(sender, instance, created, **kwargs):
    """Create profile but DON'T send emails until profile is completed"""
    if created:
        try:
            # Create profile with verification token ready
            profile, profile_created = Profile.objects.get_or_create(user=instance)
            import secrets
            profile.email_verification_token = secrets.token_urlsafe(32)
            profile.email_verification_sent_at = timezone.now()
            profile.save()
            
            # ⚠️ NO EMAILS SENT HERE - wait for profile completion
            
        except Exception as e:
            print(f"DEBUG: Error in new user signal: {e}")

@receiver(post_save, sender=Profile)
def handle_profile_completion(sender, instance, **kwargs):
    """Send verification + welcome when profile reaches 50%+ completeness"""
    try:
        # Calculate profile completeness
        completeness = 0
        if instance.headline: completeness += 20
        if instance.about and len(instance.about) > 50: completeness += 30  
        if instance.location: completeness += 15
        if instance.date_of_birth: completeness += 10
        if hasattr(instance, 'images') and instance.images.filter(is_primary=True).exists(): completeness += 25
        
        # Only send verification email when profile is somewhat complete
        if (completeness >= 50 and 
            not instance.email_verified and 
            not getattr(instance, '_verification_sent', False)):
            
            # Mark that we've sent verification to prevent duplicates
            instance._verification_sent = True
            
            # Send verification email FIRST
            verification_url = reverse('verify_email', kwargs={'token': instance.email_verification_token})
            send_email_verification_email(instance.user.email, instance.user.username, verification_url)
            
            # Send welcome email (but note it requires verification)
            welcome_url = reverse('create_profile')
            send_welcome_email(instance.user.email, instance.user.username, welcome_url)
            
            # Notify admins about new complete profile
            if completeness >= 80:
                admin_emails = User.objects.filter(
                    is_staff=True, 
                    is_active=True
                ).values_list('email', flat=True)
                
                profile_url = reverse('admin:pages_profile_changelist')
                
                for admin_email in admin_emails:
                    if admin_email:
                        send_admin_notification_email(
                            admin_email, 
                            instance.user.username, 
                            profile_url
                        )
                    
    except Exception as e:
        print(f"DEBUG: Error in profile completion signal: {e}")

@receiver(post_save, sender=Profile)
def handle_profile_approval(sender, instance, **kwargs):
    """Send approval email only to verified emails"""
    try:
        # Check if profile was just approved AND email is verified
        if (instance.is_approved and 
            instance.approval_status == 'approved' and 
            instance.email_verified):
            
            # Send approval email to user
            dashboard_url = reverse('dashboard')
            send_profile_approved_email(
                instance.user.email,
                instance.user.username,
                dashboard_url
            )
            
    except Exception as e:
        print(f"DEBUG: Error in profile approval signal: {e}")
