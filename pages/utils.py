# pages/utils.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import EmailReminderLog

def send_verification_reminder(user):
    """Send email verification reminder"""
    try:
        subject = "Please verify your email address"
        html_message = render_to_string('emails/verification_reminder.html', {
            'user': user,
            'verification_url': f"{settings.SITE_URL}/verify-email/{user.profile.email_verification_token}/"
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Log the reminder
        EmailReminderLog.objects.create(
            user=user,
            reminder_type=EmailReminderLog.ReminderType.EMAIL_VERIFICATION,
            was_successful=True
        )
        return True
        
    except Exception as e:
        EmailReminderLog.objects.create(
            user=user,
            reminder_type=EmailReminderLog.ReminderType.EMAIL_VERIFICATION,
            was_successful=False,
            error_message=str(e)
        )
        return False

def send_profile_completion_reminder(user):
    """Send profile completion reminder"""
    try:
        subject = "Complete your dating profile"
        html_message = render_to_string('emails/profile_completion_reminder.html', {
            'user': user,
            'profile_url': f"{settings.SITE_URL}/profile/edit/"
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        EmailReminderLog.objects.create(
            user=user,
            reminder_type=EmailReminderLog.ReminderType.PROFILE_COMPLETION,
            was_successful=True
        )
        return True
        
    except Exception as e:
        EmailReminderLog.objects.create(
            user=user,
            reminder_type=EmailReminderLog.ReminderType.PROFILE_COMPLETION,
            was_successful=False,
            error_message=str(e)
        )
        return False
