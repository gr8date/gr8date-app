# pages/management/commands/send_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from pages.models import Profile
from pages.utils.emails import send_verification_reminder, send_profile_completion_reminder


class Command(BaseCommand):
    help = 'Send automated reminders for email verification and profile completion'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reminder-type',
            type=str,
            choices=['email_verification', 'profile_completion', 'all'],
            default='all',
            help='Type of reminders to send'
        )
    
    def handle(self, *args, **options):
        reminder_type = options['reminder_type']
        now = timezone.now()
        
        if reminder_type in ['email_verification', 'all']:
            self.send_email_verification_reminders(now)
        
        if reminder_type in ['profile_completion', 'all']:
            self.send_profile_completion_reminders(now)
    
    def send_email_verification_reminders(self, now):
        """Send email verification reminders"""
        # Users with unverified emails, no reminder sent in last 7 days, less than 3 reminders total
        profiles = Profile.objects.filter(
            email_verified=False,
            email_verification_reminder_count__lt=3,
        ).exclude(
            email_verification_last_reminder_sent__gte=now - timedelta(days=7)
        )
        
        count = 0
        for profile in profiles:
            if send_verification_reminder(profile.user):
                profile.email_verification_reminder_count += 1
                profile.email_verification_last_reminder_sent = now
                profile.save()
                count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f"Sent {count} email verification reminders")
        )
    
    def send_profile_completion_reminders(self, now):
        """Send profile completion reminders"""
        # Incomplete profiles, no reminder in last 5 days, less than 5 reminders total
        profiles = Profile.objects.filter(
            is_complete=False,
            profile_completion_reminder_count__lt=5,
        ).exclude(
            profile_completion_last_reminder_sent__gte=now - timedelta(days=5)
        )
        
        count = 0
        for profile in profiles:
            if send_profile_completion_reminder(profile.user):
                profile.profile_completion_reminder_count += 1
                profile.profile_completion_last_reminder_sent = now
                profile.save()
                count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f"Sent {count} profile completion reminders")
        )
