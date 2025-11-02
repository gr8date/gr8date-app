# pages/utils/emails.py

import os
import requests
from django.conf import settings
from django.utils import timezone

def send_brevo_email(to_email, subject, html_content):
    """
    Send email via Brevo API
    Returns True if successful, False otherwise
    """
    try:
        # Brevo API configuration
        BREVO_API_KEY = getattr(settings, 'BREVO_API_KEY', os.environ.get('BREVO_API_KEY'))
        BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
        
        if not BREVO_API_KEY:
            print("❌ DEBUG: Brevo API key not configured")
            return False

        # Prepare email data
        email_data = {
            "sender": {
                "name": "GR8DATE",
                "email": "hello@gr8date.com.au"
            },
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_content,
            "tags": ["gr8date"]
        }

        # Make API request
        response = requests.post(
            BREVO_API_URL,
            json=email_data,
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=30  # 30 second timeout
        )

        if response.status_code == 201:
            print(f"✅ DEBUG: Email sent successfully to {to_email}")
            return True
        else:
            print(f"❌ DEBUG: Brevo API error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ DEBUG: Exception sending email: {str(e)}")
        return False

def send_welcome_email(user_email, username, complete_profile_url):
    """Send welcome email when user signs up"""
    subject = "🎉 Welcome to GR8DATE!"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to GR8DATE</title>
        <style>
            @media only screen and (max-width: 600px) {{
                .container {{
                    width: 100% !important;
                    padding: 10px !important;
                }}
                .button {{
                    display: block !important;
                    width: 100% !important;
                    text-align: center !important;
                }}
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f8f9fa;">
        <div class="container" style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header with Logo -->
            <div style="text-align: center; margin-bottom: 30px; padding: 20px 0;">
                <img src="https://gr8date.com.au/static/images/gr8date-logo.png" alt="GR8DATE" style="max-width: 200px; height: auto;">
            </div>
            
            <!-- Main Content -->
            <div style="background: white; padding: 40px 30px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #333; margin-top: 0; text-align: center;">Welcome to GR8DATE, {username}! 🎉</h2>
                
                <p style="color: #555; line-height: 1.6; font-size: 16px;">
                    We're thrilled to have you join our community of amazing singles looking for meaningful connections.
                </p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 25px 0;">
                    <h3 style="color: #333; margin-top: 0;">Next Steps:</h3>
                    <ul style="color: #555; line-height: 1.8;">
                        <li><strong>Complete your profile</strong> - Tell us about yourself</li>
                        <li><strong>Add your best photos</strong> - Show your personality</li>
                        <li><strong>Start browsing</strong> - Discover amazing people</li>
                    </ul>
                </div>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{complete_profile_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-size: 16px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                        Complete Your Profile
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px; text-align: center;">
                    You're currently in preview mode. Complete your profile to get full access!
                </p>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 30px; color: #999; font-size: 12px; line-height: 1.6;">
                <p>This email was sent to {user_email} because you signed up for GR8DATE</p>
                <p>If you didn't create an account, please ignore this email.</p>
                <p>© 2024 GR8DATE. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_brevo_email(user_email, subject, html_content)

def send_profile_submitted_email(user_email, username):
    """Send confirmation when user submits profile for approval"""
    subject = "📋 Your GR8DATE Profile is Under Review!"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Profile Under Review</title>
        <style>
            @media only screen and (max-width: 600px) {{
                .container {{
                    width: 100% !important;
                    padding: 10px !important;
                }}
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f8f9fa;">
        <div class="container" style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header with Logo -->
            <div style="text-align: center; margin-bottom: 30px; padding: 20px 0;">
                <img src="https://gr8date.com.au/static/images/gr8date-logo.png" alt="GR8DATE" style="max-width: 200px; height: auto;">
            </div>
            
            <!-- Main Content -->
            <div style="background: white; padding: 40px 30px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 25px;">
                    <div style="background: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; display: inline-block;">
                        <strong>⏳ Profile Under Review</strong>
                    </div>
                </div>
                
                <h2 style="color: #333; margin-top: 0; text-align: center;">Thanks for completing your profile, {username}! </h2>
                
                <p style="color: #555; line-height: 1.6; font-size: 16px;">
                    Our team is currently reviewing your profile to ensure it meets our community guidelines. 
                    This usually takes less than 24 hours.
                </p>
                
                <div style="background: #e7f3ff; padding: 20px; border-radius: 10px; margin: 25px 0;">
                    <h3 style="color: #004085; margin-top: 0;">What happens next?</h3>
                    <ul style="color: #004085; line-height: 1.8;">
                        <li><strong>Profile review</strong> - We'll check your profile details and photos</li>
                        <li><strong>Quick approval</strong> - Most profiles are approved within hours</li>
                        <li><strong>Full access</strong> - You'll get complete access to all features</li>
                        <li><strong>Email notification</strong> - We'll email you once approved</li>
                    </ul>
                </div>
                
                <p style="color: #666; font-size: 14px; text-align: center;">
                    In the meantime, you can still browse profiles in preview mode!
                </p>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 30px; color: #999; font-size: 12px; line-height: 1.6;">
                <p>This email was sent to {user_email} because you submitted your GR8DATE profile for approval</p>
                <p>© 2024 GR8DATE. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_brevo_email(user_email, subject, html_content)

def send_profile_approved_email(user_email, username, login_url):
    """Send notification when profile is approved by admin"""
    subject = "✅ Your GR8DATE Profile is Approved!"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Profile Approved</title>
        <style>
            @media only screen and (max-width: 600px) {{
                .container {{
                    width: 100% !important;
                    padding: 10px !important;
                }}
                .button {{
                    display: block !important;
                    width: 100% !important;
                    text-align: center !important;
                }}
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f8f9fa;">
        <div class="container" style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header with Logo -->
            <div style="text-align: center; margin-bottom: 30px; padding: 20px 0;">
                <img src="https://gr8date.com.au/static/images/gr8date-logo.png" alt="GR8DATE" style="max-width: 200px; height: auto;">
            </div>
            
            <!-- Main Content -->
            <div style="background: white; padding: 40px 30px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 25px;">
                    <div style="background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; display: inline-block;">
                        <strong>✅ Profile Approved!</strong>
                    </div>
                </div>
                
                <h2 style="color: #333; margin-top: 0; text-align: center;">Congratulations, {username}! 🎉</h2>
                
                <p style="color: #555; line-height: 1.6; font-size: 16px;">
                    Great news! Your GR8DATE profile has been approved and you now have full access to all features.
                </p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 25px 0;">
                    <h3 style="color: #333; margin-top: 0;">You can now:</h3>
                    <ul style="color: #555; line-height: 1.8;">
                        <li><strong>Browse all profiles</strong> - Discover your perfect match</li>
                        <li><strong>Send and receive messages</strong> - Start conversations</li>
                        <li><strong>Like profiles</strong> - Show interest in other members</li>
                        <li><strong>Join Hot Dates</strong> - Attend exciting group events</li>
                        <li><strong>Use advanced search</strong> - Find exactly what you're looking for</li>
                    </ul>
                </div>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{login_url}" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-size: 16px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);">
                        Start Exploring Now
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px; text-align: center;">
                    The adventure begins now! We can't wait to see you find amazing connections.
                </p>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 30px; color: #999; font-size: 12px; line-height: 1.6;">
                <p>This email was sent to {user_email} because your GR8DATE profile was approved</p>
                <p>© 2024 GR8DATE. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_brevo_email(user_email, subject, html_content)

def send_admin_notification_email(admin_email, username, profile_url):
    """Notify admins when a user submits profile for approval"""
    subject = f"🆕 New Profile Submission: {username}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>New Profile Submission</title>
        <style>
            @media only screen and (max-width: 600px) {{
                .container {{
                    width: 100% !important;
                    padding: 10px !important;
                }}
                .button {{
                    display: block !important;
                    width: 100% !important;
                    text-align: center !important;
                }}
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f8f9fa;">
        <div class="container" style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header with Logo -->
            <div style="text-align: center; margin-bottom: 30px; padding: 20px 0;">
                <img src="https://gr8date.com.au/static/images/gr8date-logo.png" alt="GR8DATE" style="max-width: 200px; height: auto;">
            </div>
            
            <!-- Main Content -->
            <div style="background: white; padding: 40px 30px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 25px;">
                    <div style="background: #cce7ff; color: #004085; padding: 15px; border-radius: 8px; display: inline-block;">
                        <strong>🆕 New Profile Awaiting Review</strong>
                    </div>
                </div>
                
                <h2 style="color: #333; margin-top: 0; text-align: center;">New User Profile Submitted</h2>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 25px 0;">
                    <p style="margin: 0; color: #555; font-size: 16px;">
                        <strong>User:</strong> {username}<br>
                        <strong>Submitted:</strong> {timezone.now().strftime('%Y-%m-%d at %H:%M')}<br>
                        <strong>Status:</strong> Awaiting Approval
                    </p>
                </div>
                
                <p style="color: #555; line-height: 1.6;">
                    Please review this profile to ensure it meets GR8DATE community guidelines and quality standards.
                </p>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{profile_url}" style="background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-size: 16px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(0, 123, 255, 0.3);">
                        Review Profile Now
                    </a>
                </div>
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="color: #856404; margin: 0; font-size: 14px;">
                        <strong>⏰ Quick Approval Recommended:</strong><br>
                        Users receive better experience when profiles are approved within 24 hours.
                    </p>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 30px; color: #999; font-size: 12px; line-height: 1.6;">
                <p>This is an automated notification from GR8DATE Admin System</p>
                <p>© 2024 GR8DATE. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_brevo_email(admin_email, subject, html_content)

def send_email_verification_email(user_email, username, verification_url):
    """Send email verification link to user"""
    subject = "✅ Verify Your GR8DATE Email Address"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verify Your Email</title>
        <style>
            @media only screen and (max-width: 600px) {{
                .container {{
                    width: 100% !important;
                    padding: 10px !important;
                }}
                .button {{
                    display: block !important;
                    width: 100% !important;
                    text-align: center !important;
                }}
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f8f9fa;">
        <div class="container" style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header with Logo -->
            <div style="text-align: center; margin-bottom: 30px; padding: 20px 0;">
                <img src="https://gr8date.com.au/static/images/gr8date-logo.png" alt="GR8DATE" style="max-width: 200px; height: auto;">
            </div>
            
            <!-- Main Content -->
            <div style="background: white; padding: 40px 30px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 25px;">
                    <div style="background: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 8px; display: inline-block;">
                        <strong>📧 Email Verification Required</strong>
                    </div>
                </div>
                
                <h2 style="color: #333; margin-top: 0; text-align: center;">Hi {username}, Verify Your Email</h2>
                
                <p style="color: #555; line-height: 1.6; font-size: 16px;">
                    Thank you for completing your GR8DATE profile! Please verify your email address to ensure you receive important notifications and updates.
                </p>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{verification_url}" style="background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-size: 16px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(23, 162, 184, 0.3);">
                        Verify Email Address
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px; text-align: center;">
                    This link will expire in 24 hours. If you didn't create a GR8DATE account, please ignore this email.
                </p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="color: #666; margin: 0; font-size: 14px;">
                        <strong>Why verify your email?</strong><br>
                        • Secure your account<br>
                        • Receive match notifications<br>
                        • Get important updates<br>
                        • Reset password if needed
                    </p>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 30px; color: #999; font-size: 12px; line-height: 1.6;">
                <p>This email was sent to {user_email} as part of your GR8DATE account setup</p>
                <p>© 2024 GR8DATE. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_brevo_email(user_email, subject, html_content)

def send_admin_message_notification(user_email, username, admin_message, reply_url):
    """Notify user when admin sends them a message about profile changes"""
    subject = "📝 Message from GR8DATE Admin About Your Profile"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Message</title>
        <style>
            @media only screen and (max-width: 600px) {{
                .container {{
                    width: 100% !important;
                    padding: 10px !important;
                }}
                .button {{
                    display: block !important;
                    width: 100% !important;
                    text-align: center !important;
                }}
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f8f9fa;">
        <div class="container" style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header with Logo -->
            <div style="text-align: center; margin-bottom: 30px; padding: 20px 0;">
                <img src="https://gr8date.com.au/static/images/gr8date-logo.png" alt="GR8DATE" style="max-width: 200px; height: auto;">
            </div>
            
            <!-- Main Content -->
            <div style="background: white; padding: 40px 30px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 25px;">
                    <div style="background: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; display: inline-block;">
                        <strong>📝 Message from GR8DATE Admin</strong>
                    </div>
                </div>
                
                <h2 style="color: #333; margin-top: 0; text-align: center;">Hi {username}</h2>
                
                <p style="color: #555; line-height: 1.6; font-size: 16px;">
                    Our admin team has reviewed your profile and has an important message for you:
                </p>
                
                <!-- Admin Message -->
                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 25px 0; border-left: 4px solid #007bff;">
                    <p style="color: #333; font-style: italic; margin: 0; line-height: 1.6;">
                        "{admin_message}"
                    </p>
                </div>
                
                <p style="color: #555; line-height: 1.6;">
                    Please address the above feedback to complete your profile approval process.
                </p>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{reply_url}" style="background: linear-gradient(135deg, #fd7e14 0%, #e55a0e 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-size: 16px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(253, 126, 20, 0.3);">
                        Update Your Profile
                    </a>
                </div>
                
                <div style="background: #e7f3ff; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="color: #004085; margin: 0; font-size: 14px;">
                        <strong>💡 Need help?</strong><br>
                        If you have questions about the requested changes, you can reply to this email or contact our support team.
                    </p>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 30px; color: #999; font-size: 12px; line-height: 1.6;">
                <p>This email was sent to {user_email} from GR8DATE Admin Team</p>
                <p>© 2024 GR8DATE. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_brevo_email(user_email, subject, html_content)

def send_password_reset_email(user_email, username, reset_url):
    """Send password reset email to user"""
    subject = "🔒 Reset Your GR8DATE Password"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reset Your Password</title>
        <style>
            @media only screen and (max-width: 600px) {{
                .container {{
                    width: 100% !important;
                    padding: 10px !important;
                }}
                .button {{
                    display: block !important;
                    width: 100% !important;
                    text-align: center !important;
                }}
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f8f9fa;">
        <div class="container" style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header with Logo -->
            <div style="text-align: center; margin-bottom: 30px; padding: 20px 0;">
                <img src="https://gr8date.com.au/static/images/gr8date-logo.png" alt="GR8DATE" style="max-width: 200px; height: auto;">
            </div>
            
            <!-- Main Content -->
            <div style="background: white; padding: 40px 30px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 25px;">
                    <div style="background: #f8d7da; color: #721c24; padding: 15px; border-radius: 8px; display: inline-block;">
                        <strong>🔒 Password Reset Request</strong>
                    </div>
                </div>
                
                <h2 style="color: #333; margin-top: 0; text-align: center;">Hi {username},</h2>
                
                <p style="color: #555; line-height: 1.6; font-size: 16px;">
                    We received a request to reset your GR8DATE password. Click the button below to create a new password.
                </p>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{reset_url}" style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-size: 16px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(220, 53, 69, 0.3);">
                        Reset Your Password
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px; text-align: center;">
                    This link will expire in 1 hour for security reasons.
                </p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="color: #666; margin: 0; font-size: 14px;">
                        <strong>🔒 Security Tips:</strong><br>
                        • Never share your password<br>
                        • Use a strong, unique password<br>
                        • Change your password regularly<br>
                        • Log out from shared devices
                    </p>
                </div>
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    If you didn't request a password reset, please ignore this email or contact support if you're concerned about your account security.
                </p>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 30px; color: #999; font-size: 12px; line-height: 1.6;">
                <p>This email was sent to {user_email} in response to a password reset request</p>
                <p>© 2024 GR8DATE. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_brevo_email(user_email, subject, html_content)
