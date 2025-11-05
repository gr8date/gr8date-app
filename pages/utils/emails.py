import os
import requests
from django.conf import settings
from django.utils import timezone

def send_brevo_email(to_email, subject, html_content):
    """
    Send email via Brevo API
    """
    try:
        BREVO_API_KEY = getattr(settings, 'BREVO_API_KEY', os.environ.get('BREVO_API_KEY'))
        DEFAULT_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'GR8DATE <hello@gr8date.com.au>')
        
        if not BREVO_API_KEY:
            print("❌ BREVO_API_KEY not found")
            return False
            
        BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'
        
        payload = {
            'sender': {
                'name': 'GR8DATE',
                'email': 'hello@gr8date.com.au'
            },
            'to': [{'email': to_email}],
            'subject': subject,
            'htmlContent': html_content
        }
        
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'api-key': BREVO_API_KEY
        }
        
        response = requests.post(BREVO_API_URL, json=payload, headers=headers)
        
        if response.status_code == 201:
            print(f"✅ Email sent successfully to {to_email}")
            return True
        else:
            print(f"❌ Brevo API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception sending email: {str(e)}")
        return False

def send_welcome_email(user_email, username, complete_profile_url):
    """
    Send welcome email to new users
    """
    try:
        subject = 'Welcome to GR8DATE! Complete Your Profile'
        html_message = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ff2b6a, #ff5478); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .button {{ background: #ff2b6a; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: bold; }}
                .footer {{ background: #333; color: white; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to GR8DATE!</h1>
                </div>
                <div class="content">
                    <h2>Hello {username},</h2>
                    <p>Welcome to Australia's exciting new dating community! We're thrilled to have you on board.</p>
                    <p>To start connecting with other singles, please complete your profile:</p>
                    <p style="text-align: center;">
                        <a href="{complete_profile_url}" class="button">Complete Your Profile</a>
                    </p>
                    <p>Once your profile is approved by our admin team, you'll be able to browse and connect with other members.</p>
                    <p><strong>Need help?</strong> Reply to this email or visit our FAQ section.</p>
                </div>
                <div class="footer">
                    <p>© 2024 GR8DATE. All rights reserved.</p>
                    <p>Making dating great again in Australia! 🇦🇺</p>
                </div>
            </div>
        </body>
        </html>
        '''
        return send_brevo_email(user_email, subject, html_message)
    except Exception as e:
        print(f"❌ Welcome email error: {str(e)}")
        return False

def send_profile_submitted_email(user_email, username):
    """
    Send email when profile is submitted for approval
    """
    try:
        subject = 'Profile Submitted for Review - GR8DATE'
        html_message = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .footer {{ background: #333; color: white; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Profile Submitted!</h1>
                </div>
                <div class="content">
                    <h2>Hello {username},</h2>
                    <p>Your profile has been successfully submitted for admin approval!</p>
                    <p><strong>What happens next?</strong></p>
                    <ul>
                        <li>Our team will review your profile within 24-48 hours</li>
                        <li>You'll receive an email once your profile is approved</li>
                        <li>Once approved, you can start browsing and connecting with other members</li>
                    </ul>
                    <p>In the meantime, you can browse profiles in preview mode.</p>
                    <p><strong>Please check your spam/junk folder</strong> if you don't see our approval email.</p>
                </div>
                <div class="footer">
                    <p>© 2024 GR8DATE. Making meaningful connections in Australia.</p>
                </div>
            </div>
        </body>
        </html>
        '''
        return send_brevo_email(user_email, subject, html_message)
    except Exception as e:
        print(f"❌ Profile submitted email error: {str(e)}")
        return False

def send_profile_approved_email(user_email, username, login_url):
    """
    Send email when profile is approved
    """
    try:
        subject = '🎉 Your GR8DATE Profile is Approved!'
        html_message = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4CAF50, #45a049); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .button {{ background: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: bold; }}
                .footer {{ background: #333; color: white; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Profile Approved!</h1>
                </div>
                <div class="content">
                    <h2>Congratulations {username}!</h2>
                    <p>Great news! Your GR8DATE profile has been approved by our admin team.</p>
                    <p>You can now start browsing and connecting with other singles in the community.</p>
                    <p style="text-align: center;">
                        <a href="{login_url}" class="button">Start Exploring</a>
                    </p>
                    <p><strong>Ready to make great connections?</strong></p>
                    <ul>
                        <li>Browse profiles of other singles</li>
                        <li>Send likes and messages</li>
                        <li>Join Hot Dates events</li>
                        <li>Find your perfect match!</li>
                    </ul>
                    <p>We're excited to help you make meaningful connections!</p>
                </div>
                <div class="footer">
                    <p>© 2024 GR8DATE. Your journey to great dates starts here!</p>
                </div>
            </div>
        </body>
        </html>
        '''
        return send_brevo_email(user_email, subject, html_message)
    except Exception as e:
        print(f"❌ Profile approved email error: {str(e)}")
        return False

def send_admin_notification_email(admin_email, username, profile_url):
    """
    Send notification to admin about new profile submission
    """
    try:
        subject = f'🆕 New Profile Submission: {username}'
        html_message = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #FF9800, #FF5722); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .button {{ background: #FF9800; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: bold; }}
                .footer {{ background: #333; color: white; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>New Profile Awaiting Review</h1>
                </div>
                <div class="content">
                    <h2>Profile Submission Alert</h2>
                    <p><strong>Username:</strong> {username}</p>
                    <p>A new user has submitted their profile for approval.</p>
                    <p style="text-align: center;">
                        <a href="{profile_url}" class="button">Review Profile</a>
                    </p>
                    <p>Please review the profile within 24 hours.</p>
                </div>
                <div class="footer">
                    <p>GR8DATE Admin System</p>
                </div>
            </div>
        </body>
        </html>
        '''
        return send_brevo_email(admin_email, subject, html_message)
    except Exception as e:
        print(f"❌ Admin notification email error: {str(e)}")
        return False

def send_email_verification_email(user_email, username, verification_url):
    """
    Send email verification link
    """
    try:
        subject = 'Verify Your Email Address - GR8DATE'
        html_message = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #2196F3, #21CBF3); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .button {{ background: #2196F3; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: bold; }}
                .footer {{ background: #333; color: white; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Verify Your Email</h1>
                </div>
                <div class="content">
                    <h2>Hello {username},</h2>
                    <p>Please verify your email address to complete your GR8DATE registration.</p>
                    <p style="text-align: center;">
                        <a href="{verification_url}" class="button">Verify Email Address</a>
                    </p>
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; background: #f0f0f0; padding: 10px; border-radius: 5px;">
                        {verification_url}
                    </p>
                    <p><strong>This link will expire in 24 hours.</strong></p>
                </div>
                <div class="footer">
                    <p>© 2024 GR8DATE. Secure dating platform.</p>
                </div>
            </div>
        </body>
        </html>
        '''
        return send_brevo_email(user_email, subject, html_message)
    except Exception as e:
        print(f"❌ Email verification error: {str(e)}")
        return False

def send_admin_message_notification(user_email, username, message, profile_edit_url):
    """
    Send notification when admin sends a message
    """
    try:
        subject = 'Message from GR8DATE Admin'
        html_message = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #9C27B0, #673AB7); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .button {{ background: #9C27B0; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: bold; }}
                .message-box {{ background: #fff; border-left: 4px solid #9C27B0; padding: 15px; margin: 20px 0; }}
                .footer {{ background: #333; color: white; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Admin Message</h1>
                </div>
                <div class="content">
                    <h2>Hello {username},</h2>
                    <p>You have a new message from the GR8DATE admin team regarding your profile.</p>
                    <div class="message-box">
                        <p><strong>Admin Message:</strong></p>
                        <p>{message}</p>
                    </div>
                    <p style="text-align: center;">
                        <a href="{profile_edit_url}" class="button">Update Your Profile</a>
                    </p>
                </div>
                <div class="footer">
                    <p>© 2024 GR8DATE Admin Team</p>
                </div>
            </div>
        </body>
        </html>
        '''
        return send_brevo_email(user_email, subject, html_message)
    except Exception as e:
        print(f"❌ Admin message notification error: {str(e)}")
        return False

def send_password_reset_email(user_email, username, reset_url):
    """
    Send password reset email
    """
    try:
        subject = 'Reset Your GR8DATE Password'
        html_message = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ff2b6a, #ff5478); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .button {{ background: #ff2b6a; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; display: inline-block; font-weight: bold; }}
                .footer {{ background: #333; color: white; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset</h1>
                </div>
                <div class="content">
                    <h2>Hello {username},</h2>
                    <p>We received a request to reset your GR8DATE password.</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </p>
                    <p>Or copy this link:</p>
                    <p style="word-break: break-all; background: #f0f0f0; padding: 10px; border-radius: 5px;">
                        {reset_url}
                    </p>
                    <p><strong>This link will expire in 1 hour.</strong></p>
                    <p>If you didn't request this, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>© 2024 GR8DATE. Secure dating platform.</p>
                </div>
            </div>
        </body>
        </html>
        '''
        return send_brevo_email(user_email, subject, html_message)
    except Exception as e:
        print(f"❌ Password reset email error: {str(e)}")
        return False

# Legacy functions for compatibility
def send_verification_reminder(user, request=None):
    """Legacy function - use send_email_verification_email instead"""
    return send_email_verification_email(user.email, user.username, "#")

def send_profile_completion_reminder(user, request=None):
    """Legacy function"""
    try:
        subject = 'Complete Your GR8DATE Profile'
        html_message = f'<html><body><h2>Complete Your Profile</h2><p>Hello {user.username}, please complete your profile to start connecting with other singles!</p></body></html>'
        return send_brevo_email(user.email, subject, html_message)
    except Exception as e:
        print(f"❌ Profile completion reminder error: {str(e)}")
        return False

def send_reminder_email(user_email, username, reminder_type, message):
    """
    Send reminder email - for signals compatibility
    """
    try:
        subject = f'Reminder: {reminder_type}'
        html_message = f'''
        <html>
        <body>
            <h2>Reminder</h2>
            <p>Hello {username}, {message}</p>
        </body>
        </html>
        '''
        return send_brevo_email(user_email, subject, html_message)
    except Exception as e:
        print(f"Reminder email error: {str(e)}")
        return False

def send_welcome_email_legacy(user):
    """Legacy function - use send_welcome_email instead"""
    return send_welcome_email(user.email, user.username, "#")
