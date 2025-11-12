# pages/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date, datetime
import json
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib import messages
import re
from .models import ProfileImage
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import secrets
from pages.utils.emails import send_password_reset_email

# ✅ PASSWORD VALIDATION IMPORTS
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

# ✅ ENHANCED EMAIL IMPORTS
from django.urls import reverse
from .utils.emails import (
    send_welcome_email, 
    send_profile_submitted_email, 
    send_profile_approved_email,
    send_admin_notification_email,
    send_email_verification_email,
    send_admin_message_notification
)

# ✅ PASSWORD RESET IMPORTS
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings

# Import your models
from .models import (
    Profile, Message, Thread, Like, Block, PrivateAccessRequest, 
    HotDate, HotDateView, HotDateNotification, Blog, UserActivity,
    AdminMessage
)

# ======================
# ✅ FIXED: ENHANCED ACTIVITY TRACKING FUNCTION WITH BOT DETECTION
# ======================

def track_user_activity(user, action, request=None, extra_data=None):
    """Enhanced tracking function with bot detection and CORRECT field names"""
    try:
        ip_address = None
        user_agent = None
        is_bot = False
        bot_type = None
        bot_category = None
        
        if request:
            # Get client IP safely
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            # Get user agent safely
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length
            
            # ✅ COMPREHENSIVE BOT DETECTION
            bot_indicators = {
                # Search Engine Bots
                'googlebot': ('Google Bot', 'search_engine'),
                'bingbot': ('Bing Bot', 'search_engine'),
                'duckduckbot': ('DuckDuckGo Bot', 'search_engine'),
                'baiduspider': ('Baidu Bot', 'search_engine'),
                'yandexbot': ('Yandex Bot', 'search_engine'),
                'sogou': ('Sogou Bot', 'search_engine'),
                
                # Social Media Bots
                'facebookexternalhit': ('Facebook Bot', 'social_media'),
                'twitterbot': ('Twitter Bot', 'social_media'),
                'linkedinbot': ('LinkedIn Bot', 'social_media'),
                'pinterest': ('Pinterest Bot', 'social_media'),
                'tiktok': ('TikTok Bot', 'social_media'),  # ✅ TIKTOK ADDED
                'tiktokbot': ('TikTok Bot', 'social_media'),  # ✅ TIKTOK VARIATION
                'instagram': ('Instagram Bot', 'social_media'),
                'redditbot': ('Reddit Bot', 'social_media'),
                'discordbot': ('Discord Bot', 'social_media'),
                'slackbot': ('Slack Bot', 'social_media'),
                'telegrambot': ('Telegram Bot', 'social_media'),
                'whatsapp': ('WhatsApp Bot', 'social_media'),
                'snapchat': ('Snapchat Bot', 'social_media'),
                'threads': ('Threads Bot', 'social_media'),
                
                # Messaging/App Bots
                'discord': ('Discord', 'messaging'),
                'telegram': ('Telegram', 'messaging'),
                'whatsapp': ('WhatsApp', 'messaging'),
                'signal': ('Signal', 'messaging'),
                'wechat': ('WeChat', 'messaging'),
                'line': ('Line', 'messaging'),
                
                # SEO & Analytics Bots
                'ahrefsbot': ('Ahrefs Bot', 'seo'),
                'semrushbot': ('Semrush Bot', 'seo'),
                'mj12bot': ('Majestic SEO Bot', 'seo'),
                'dotbot': ('DotBot', 'seo'),
                'rogerbot': ('RogerBot', 'seo'),
                'exabot': ('ExaBot', 'seo'),
                'ccbot': ('Common Crawl Bot', 'seo'),
                'petalbot': ('PetalBot', 'seo'),
                'screaming frog': ('Screaming Frog SEO Spider', 'seo'),
                'moz.com': ('Moz Bot', 'seo'),
                'seznam': ('Seznam Bot', 'seo'),
                
                # AI & Tech Bots
                'chatgpt': ('OpenAI ChatGPT', 'ai'),
                'openai': ('OpenAI', 'ai'),
                'anthropic': ('Anthropic Claude', 'ai'),
                'claude': ('Claude AI', 'ai'),
                'google-assistant': ('Google Assistant', 'ai'),
                'alexa': ('Amazon Alexa', 'ai'),
                'siri': ('Apple Siri', 'ai'),
                
                # Monitoring & Scraping Tools
                'uptimerobot': ('UptimeRobot', 'monitoring'),
                'pingdom': ('Pingdom', 'monitoring'),
                'newrelic': ('New Relic', 'monitoring'),
                'datadog': ('Datadog', 'monitoring'),
                'python-requests': ('Python Requests', 'scraping'),
                'curl': ('cURL', 'scraping'),
                'wget': ('Wget', 'scraping'),
                'scrapy': ('Scrapy', 'scraping'),
                'beautifulsoup': ('BeautifulSoup', 'scraping'),
                
                # Generic Bot Indicators (keep these last)
                'bot': ('Generic Bot', 'unknown'),
                'crawler': ('Generic Crawler', 'unknown'),
                'spider': ('Generic Spider', 'unknown'),
                'fetcher': ('Generic Fetcher', 'unknown'),
                'checker': ('Generic Checker', 'unknown')
            }
            
            if user_agent:
                user_agent_lower = user_agent.lower()
                for indicator, (bot_name, category) in bot_indicators.items():
                    if indicator in user_agent_lower:
                        is_bot = True
                        bot_type = bot_name
                        bot_category = category
                        break
        
        # Prepare enhanced extra_data
        enhanced_extra_data = extra_data or {}
        enhanced_extra_data.update({
            'is_bot': is_bot,
            'bot_type': bot_type,
            'bot_category': bot_category,
            'user_agent_preview': user_agent[:100] if user_agent else None,
            'detection_method': 'user_agent_analysis'
        })
        
        # ✅ FIXED: Create activity record with CORRECT field names
        activity = UserActivity.objects.create(
            user=user,
            action=action,  # ✅ Using 'action' field that matches your model
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=enhanced_extra_data,  # ✅ CORRECT FIELD NAME (not additional_data)
            timestamp=timezone.now()  # ✅ ADD TIMESTAMP (required field)
        )
        
        # Log bot detection with categories
        if is_bot:
            print(f"🤖 {bot_category.upper()} BOT: {bot_type} - Action: {action} - IP: {ip_address}")
        else:
            user_display = user.username if user else 'Anonymous'
            print(f"✅ Human Activity: {user_display} - {action}")
        
        return True
        
    except Exception as e:
        # ✅ SAFE: Fail silently without breaking the main functionality
        print(f"⚠️ Activity tracking failed (non-critical): {e}")
        return False

# ======================
# SECURITY FIX 1: HOT DATE CREATION GUARD
# ======================

@login_required
def hotdate_create(request):
    """Display and handle Hot Date creation form WITH SECURITY CHECK"""
    # SECURITY FIX: Check profile approval before allowing Hot Date creation
    try:
        user_profile = Profile.objects.get(user=request.user)
        if not user_profile.is_approved and not request.user.is_staff:
            messages.error(request, "Your profile must be approved before you can create Hot Dates.")
            return redirect('dashboard')
    except Profile.DoesNotExist:
        messages.error(request, "Please complete your profile before creating Hot Dates.")
        return redirect('create_profile')
    
    if request.method == 'POST':
        try:
            # Get form data
            activity = request.POST.get('activity', '').strip()
            vibe = request.POST.get('vibe', '').strip()
            budget = request.POST.get('budget', '').strip()
            duration = request.POST.get('duration', '').strip()
            date_str = request.POST.get('date', '').strip()
            time_str = request.POST.get('time', '').strip()
            area = request.POST.get('area', '').strip()
            group_size = request.POST.get('group_size', '').strip()
            
            # Validate required fields
            if not all([activity, vibe, budget, duration, date_str, time_str, area, group_size]):
                messages.error(request, "All fields are required")
                return render(request, 'pages/hotdate_create.html')
            
            # Parse date and time
            try:
                date_time = timezone.make_aware(
                    datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                )
            except ValueError:
                messages.error(request, "Invalid date or time format")
                return render(request, 'pages/hotdate_create.html')
            
            # Create Hot Date
            hot_date = HotDate.objects.create(
                host=request.user,
                activity=activity,
                vibe=vibe,
                budget=budget,
                duration=duration,
                date_time=date_time,
                area=area,
                group_size=group_size
            )
            
            # ✅ ADDED: Track hotdate creation (SAFE: Won't break hotdate creation)
            track_user_activity(
                request.user, 
                'hotdate_created', 
                request,
                {'hotdate_id': hot_date.id, 'activity': activity}
            )
            
            messages.success(request, "Hot Date created successfully!")
            return redirect('hotdate_list')
            
        except Exception as e:
            messages.error(request, f"Error creating Hot Date: {str(e)}")
            return render(request, 'pages/hotdate_create.html')
    
    return render(request, 'pages/hotdate_create.html')

# ======================
# SECURITY FIX 2: PROFILE CONTENT PROTECTION
# ======================

@login_required
def profile_edit(request):
    """Edit current user's profile - WITH CONTENT PROTECTION"""
    profile = get_object_or_404(Profile, user=request.user)
     
    if request.method == 'POST':
        try:
            # SECURITY FIX: Auto-restore blank fields to approved content for approved profiles
            if profile.is_approved:
                profile.restore_approved_content()
            
            # ✅ SYNCED: Update profile fields that exist in forms
            profile.headline = request.POST.get('headline', '')
            profile.about = request.POST.get('about', '')
            profile.location = request.POST.get('location', '')
            profile.my_gender = request.POST.get('my_gender', '')
            profile.looking_for = request.POST.get('looking_for', '')
            profile.my_interests = request.POST.get('my_interests', '')
            profile.children = request.POST.get('children', '')
            
            # ✅ SYNCED: ADD missing fields from forms
            profile.body_type = request.POST.get('body_type', '')
            profile.ethnicity = request.POST.get('ethnicity', '')
            profile.relationship_status = request.POST.get('relationship_status', '')
            profile.want_children = request.POST.get('want_children', '')
            profile.smoking = request.POST.get('smoking', '')
            profile.drinking = request.POST.get('drinking', '')
            profile.preferred_intent = request.POST.get('preferred_intent', '')
            
            profile.save()
            
            # ✅ ADDED: Track profile edit (SAFE: Won't break profile editing)
            track_user_activity(request.user, 'profile_edited', request)
            
            messages.success(request, "Profile updated successfully!")
            return redirect('profile_view')
            
        except Exception as e:
            messages.error(request, f"Error updating profile: {str(e)}")
    
    context = {
        'me': profile,  # Keep 'me' for template compatibility
    }
    return render(request, 'pages/profile_edit.html', context)

# ======================
# SECURITY FIX 3: PHOTO DELETION PROTECTION
# ======================

@login_required
@csrf_exempt
def delete_image_api(request, image_id):
    """API endpoint for deleting images WITH PHOTO PROTECTION"""
    try:
        image = ProfileImage.objects.get(id=image_id, profile__user=request.user)
        
        # SECURITY FIX: Prevent deletion if it would go below approved standards
        if image.profile.is_approved and not image.can_delete_safely():
            return JsonResponse({
                'success': False, 
                'error': 'Cannot delete photo - would go below approved profile standards'
            }, status=400)
        
        was_profile_photo = (image.image_type == 'profile')
        
        image.delete()
        
        # ✅ ADDED: Track photo deletion (SAFE: Won't break deletion)
        track_user_activity(
            request.user, 
            'photo_deleted', 
            request,
            {'was_profile_photo': was_profile_photo, 'image_id': image_id}
        )
        
        # If we deleted a profile photo, promote the first additional photo
        if was_profile_photo:
            next_profile_image = ProfileImage.objects.filter(
                profile=image.profile,
                image_type='additional'
            ).first()
            
            if next_profile_image:
                next_profile_image.image_type = 'profile'
                next_profile_image.save()
                return JsonResponse({
                    'success': True, 
                    'message': 'Image deleted successfully',
                    'promoted_image_id': next_profile_image.id
                })
        
        return JsonResponse({
            'success': True, 
            'message': 'Image deleted successfully',
            'promoted_image_id': None
        })
        
    except ProfileImage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ======================
# ENHANCED PHOTO UPLOAD WITH APPROVAL WORKFLOW
# ======================

@login_required
@csrf_exempt
def upload_profile_image_api(request):
    """UNIFIED API endpoint for uploading profile images - WITH APPROVAL WORKFLOW"""
    print("=" * 60)
    print("🚀 DEBUG: UPLOAD_PROFILE_IMAGE_API CALLED - SECURE VERSION")
    print("=" * 60)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST requests allowed'}, status=400)
    
    # Check for image file
    if 'image' not in request.FILES:
        print("❌ DEBUG: No 'image' in request.FILES")
        return JsonResponse({'success': False, 'error': 'No image file provided'}, status=400)
    
    image_file = request.FILES['image']
    
    # ✅ FIXED: CONSISTENT PARAMETER HANDLING
    # Get photo type from ALL possible parameter names
    photo_type = (
        request.POST.get('photo_type') or 
        request.POST.get('image_type') or 
        'additional'  # default fallback
    )
    
    print(f"🎯 DEBUG: Final photo_type: {photo_type}")
    print(f"📋 DEBUG: All POST parameters: {dict(request.POST)}")
    
    try:
        # File type validation
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if image_file.content_type not in allowed_types:
            return JsonResponse({'success': False, 'error': f'Invalid file type: {image_file.content_type}'}, status=400)
        
        # File size validation
        max_size = 5 * 1024 * 1024
        if image_file.size > max_size:
            return JsonResponse({'success': False, 'error': f'File too large: {image_file.size} bytes (max: {max_size})'}, status=400)
        
        # Photo type validation
        valid_types = ['profile', 'additional', 'private']
        if photo_type not in valid_types:
            return JsonResponse({'success': False, 'error': f'Invalid photo type: {photo_type}. Must be one of: {valid_types}'}, status=400)
        
        # Get user profile
        profile, created = Profile.objects.get_or_create(user=request.user)
        
        # SECURITY FIX: For approved profiles, new photos need approval
        needs_approval = profile.is_approved
        is_approved = not needs_approval  # Auto-approve for unapproved profiles
        
        # Photo limit validation
        if photo_type in ['profile', 'additional']:
            public_photos_count = ProfileImage.objects.filter(
                profile=profile,
                image_type__in=['profile', 'additional'],
                is_approved=True
            ).count()
            
            if public_photos_count >= 4:
                return JsonResponse({
                    'success': False,
                    'error': f'Maximum 4 public photos allowed (current: {public_photos_count})'
                }, status=400)

        elif photo_type == 'private':
            private_photos_count = ProfileImage.objects.filter(
                profile=profile,
                image_type='private',
                is_approved=True
            ).count()
            
            if private_photos_count >= 4:
                return JsonResponse({
                    'success': False,
                    'error': f'Maximum 4 private photos allowed (current: {private_photos_count})'
                }, status=400)
        
        # Handle profile photo demotion if needed
        if photo_type == 'profile':
            try:
                updated_count = ProfileImage.objects.filter(
                    profile=profile, 
                    image_type='profile'
                ).update(image_type='additional', is_primary=False)
                print(f"✅ DEBUG: Demoted {updated_count} existing profile photos")
            except Exception as e:
                print(f"⚠️ DEBUG: Profile photo demotion warning: {str(e)}")
        
        # Determine primary status
        is_primary = (photo_type == 'profile')
        print(f"🔍 DEBUG: Setting is_primary to: {is_primary}")
        
        # Create the ProfileImage record with approval workflow
        print("🔍 DEBUG: Creating ProfileImage record...")
        try:
            profile_image = ProfileImage.objects.create(
                profile=profile,
                image=image_file,
                image_type=photo_type,
                is_primary=is_primary,
                needs_approval=needs_approval,
                is_approved=is_approved
            )
            print(f"✅ DEBUG: ProfileImage created - ID: {profile_image.id}")
            
            # ✅ ADDED: Track photo upload (SAFE: Won't break upload functionality)
            track_user_activity(
                request.user, 
                'photo_uploaded', 
                request,
                {'photo_type': photo_type, 'image_id': profile_image.id, 'needs_approval': needs_approval}
            )
            
        except Exception as e:
            print(f"❌ DEBUG: PROFILEIMAGE CREATION FAILED - {str(e)}")
            import traceback
            print(f"❌ DEBUG: TRACEBACK:\n{traceback.format_exc()}")
            return JsonResponse({'success': False, 'error': f'Database error: {str(e)}'}, status=400)
        
        print("🎉 DEBUG: SUCCESS - Image uploaded and saved successfully")
        return JsonResponse({
            'success': True, 
            'image_id': profile_image.id,
            'image_url': profile_image.image.url,
            'filename': image_file.name,
            'photo_type': photo_type,
            'is_private': (photo_type == 'private'),
            'needs_approval': needs_approval,
            'is_approved': is_approved
        })
        
    except Exception as e:
        print(f"💥 DEBUG: UNEXPECTED EXCEPTION: {str(e)}")
        import traceback
        print(f"💥 DEBUG: FULL TRACEBACK:\n{traceback.format_exc()}")
        
        return JsonResponse({
            'success': False, 
            'error': f'Upload failed: {str(e)}'
        }, status=500)

# ======================
# ENHANCED ADMIN APPROVAL WITH CONTENT SNAPSHOT
# ======================

@login_required
def admin_approve_profile(request, profile_id):
    """Approve a profile (admin only) - WITH CONTENT SNAPSHOT"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    profile = get_object_or_404(Profile, id=profile_id)
    profile.is_approved = True
    profile.approved_at = timezone.now()
    profile.approved_by = request.user
    
    # SECURITY FIX: Capture approved content state
    profile.capture_approved_state()
    
    profile.save()
    
    # ✅ ADDED: Track admin approval (SAFE: Won't break admin)
    track_user_activity(
        request.user, 
        'admin_profile_approved', 
        request,
        {'approved_user_id': profile.user.id}
    )
    
    # Send profile approved email
    try:
        login_url = request.build_absolute_uri(reverse('login'))
        send_profile_approved_email(profile.user.email, profile.user.username, login_url)
    except Exception as e:
        print(f"DEBUG: Profile approved email failed: {e}")
    
    messages.success(request, f"Profile for {profile.user.username} has been approved and content state captured.")
    return redirect('admin_profile_approvals')

# ======================
# PREVIEW USE - START (NEW VIEWS)
# ======================

@csrf_exempt  # ✅ KEEP CSRF EXEMPT FOR SIGNUP
def join_view(request):
    """Handle new user signups - redirect to preview gate"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')  # Single password field
        
        # Enhanced validation
        if not email or '@' not in email:
            messages.error(request, "Valid email is required")
            return render(request, 'pages/join_gr8date_singlepw_show.html')
        
        # ✅ ADDED: STRONG PASSWORD VALIDATION
        try:
            validate_password(password)
        except ValidationError as e:
            # Show all password errors to user
            for error in e.messages:
                messages.error(request, error)
            return render(request, 'pages/join_gr8date_singlepw_show.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return render(request, 'pages/join_gr8date_singlepw_show.html')
        
        # Generate temporary username from email + timestamp
        base_username = email.split('@')[0]
        temp_username = f"{base_username}_{int(timezone.now().timestamp())}"
        
        # Ensure username is unique and not too long
        temp_username = temp_username[:28]  # Leave room for counter
        counter = 1
        original_username = temp_username
        
        while User.objects.filter(username=temp_username).exists():
            temp_username = f"{original_username}_{counter}"
            counter += 1
            if counter > 100:  # Safety limit
                temp_username = f"user_{int(timezone.now().timestamp())}"
                break
        
        try:
            # Create user with temporary username
            user = User.objects.create_user(
                username=temp_username,
                email=email,
                password=password,
                is_active=True
            )
            
            # Log the user in immediately
            from django.contrib.auth import login
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # ✅ ADDED: Track user registration (SAFE: Won't break registration)
            track_user_activity(user, 'user_registered', request)
            
            # ✅ PRODUCTION-SAFE: Create initial profile (WON'T CRASH)
            try:
                profile, created = Profile.objects.get_or_create(user=user)
                if created:
                    print(f"✅ New profile created for {email}")
                else:
                    print(f"ℹ️ Profile already existed for {email} - continuing")
            except Exception as profile_error:
                print(f"⚠️ Non-critical profile issue: {profile_error}")
                # Don't break user registration flow
            
            # ✅ INTEGRATION: Send welcome email
            try:
                complete_profile_url = request.build_absolute_uri(reverse('create_profile'))
                send_welcome_email(user.email, user.username, complete_profile_url)
            except Exception as e:
                print(f"DEBUG: Welcome email failed: {e}")
                # Don't break the flow if email fails
            
            messages.success(request, "Welcome! Complete your profile to get started.")
            return redirect('preview_gate')
            
        except Exception as e:
            messages.error(request, f"Error creating account: {str(e)}")
            return render(request, 'pages/join_gr8date_singlepw_show.html')
    
    return render(request, 'pages/join_gr8date_singlepw_show.html')

def preview_gate(request):
    """Preview gate homepage for unapproved users"""
    if request.user.is_authenticated:
        try:
            user_profile = Profile.objects.get(user=request.user)
            if user_profile.is_approved or request.user.is_staff:
                return redirect('dashboard')
        except Profile.DoesNotExist:
            # ✅ PRODUCTION-SAFE: Create profile if it doesn't exist
            try:
                Profile.objects.get_or_create(user=request.user)
            except Exception:
                pass  # Silently continue
    
    return render(request, 'pages/preview_gate.html')

@login_required
def browse_preview(request):
    """Preview browsing for unapproved users - LIMITED TO 12 SPECIFIC PROFILES"""
    try:
        user_profile = Profile.objects.get(user=request.user)
        if user_profile.is_approved or request.user.is_staff:
            return redirect('dashboard')
    except Profile.DoesNotExist:
        pass
    
    # FIXED: Only show these 12 specific profiles in preview mode
    fixed_profile_ids = [470, 365, 361, 358, 356, 717, 459, 301, 208, 207, 205, 363]
    
    # Get the specific profiles
    profiles = Profile.objects.filter(
        id__in=fixed_profile_ids,
        is_approved=True
    ).prefetch_related('images').order_by('-created_at')
    
    paginator = Paginator(profiles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # ✅ ADDED: Track preview browsing (SAFE: Won't break preview)
    track_user_activity(request.user, 'preview_browse', request)
    
    context = {
        'is_approved_user': False,
        'suggested_profiles': page_obj,
        'search_query': None,
        'search_performed': False,
    }
    return render(request, 'pages/preview_gr8date_dashboard_fixed_v10_nolines.html', context)


# ======================
# PASSWORD RESET - STYLED VERSION  
# ======================

def custom_password_reset(request):
    """Custom password reset view that uses our Brevo email system"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            
            # Generate token and reset URL
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            
            # Send email using your Brevo system
            success = send_password_reset_email(
                user_email=user.email,
                username=user.username,
                reset_url=reset_url
            )
            
            if success:
                messages.success(request, 'Password reset email sent! Check your inbox.')
            else:
                messages.error(request, 'Failed to send email. Please try again.')
                
        except User.DoesNotExist:
            # Still show success for security (don't reveal which emails exist)
            messages.success(request, 'If that email exists in our system, a password reset link has been sent.')
        
        return redirect('password_reset_done')
    
    # If GET request, show the password reset form
    from django.contrib.auth.forms import PasswordResetForm
    form = PasswordResetForm()
    return render(request, 'registration/password_reset_form.html', {'form': form})

# ======================
# PASSWORD RESET SUPPORTING VIEWS
# ======================

from django.contrib.auth.views import (
    PasswordResetDoneView, 
    PasswordResetConfirmView, 
    PasswordResetCompleteView
)

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'

# ======================
# PREVIEW USE - END
# ======================

# Core Pages
def home(request):
    """Home page - redirect to dashboard if authenticated"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'pages/home.html')

@login_required
def dashboard(request):
    """Main dashboard with SMART PROFILE MIXING + ROTATING FIRST 48 PROFILES + ALL PROFILES BEYOND"""
    # ✅ ADDED: Track dashboard view (SAFE: Won't break dashboard)
    track_user_activity(request.user, 'dashboard_view', request)
    
    try:
        user_profile = Profile.objects.get(user=request.user)
        is_approved_user = user_profile.is_approved
    except Profile.DoesNotExist:
        is_approved_user = False
        user_profile = None
    
    # Redirect to preview gate if not approved
    if not is_approved_user and not request.user.is_staff:
        return redirect('preview_gate')

    # ========== FIXED TWO-WAY GENDER MATCHING ALGORITHM ==========
    def get_genders_user_wants(looking_for):
        """Convert 'looking_for' to list of genders user wants to see"""
        mapping = {
            'male': ['male'],
            'female': ['female'],
            'men': ['male'],      # Add variations
            'women': ['female'],   # Add variations
            'bisexual': ['male', 'female'],  # Bisexual sees both
        }
        return mapping.get(looking_for, [])  # Empty list for anything else
    
    # Start with base queryset
    if user_profile and user_profile.is_approved and not request.user.is_superuser:
        # TWO-WAY MATCHING for regular users:
        # Show profiles whose gender matches what I'm looking for AND who are looking for my gender
        user_gender = user_profile.my_gender
        user_looking_for = user_profile.looking_for
        
        # Get genders I want to see
        genders_i_want = get_genders_user_wants(user_looking_for)
        
        # Get genders that would want me
        genders_that_want_me = []
        if user_gender == 'male':
            genders_that_want_me = ['female', 'bisexual']
        elif user_gender == 'female':
            genders_that_want_me = ['male', 'bisexual']
        elif user_gender == 'nonbinary':
            genders_that_want_me = ['bisexual']  # Adjust based on your app's logic
        
        suggested_profiles = Profile.objects.filter(
            is_approved=True
        ).filter(
            # Their gender is what I'm looking for
            my_gender__in=genders_i_want,
            # AND they are looking for my gender or are bisexual
            looking_for__in=genders_that_want_me + [user_gender, 'bisexual', 'unspecified']
        )
    else:
        # Superusers see ALL profiles, or fallback for unapproved users
        suggested_profiles = Profile.objects.filter(is_approved=True)
    
    # Exclude blocked users and self
    suggested_profiles = suggested_profiles.exclude(
        Q(user=request.user) |
        Q(user__in=Block.objects.filter(blocker=request.user).values('blocked')) |
        Q(user__in=Block.objects.filter(blocked=request.user).values('blocker'))
    ).prefetch_related('images')
    # ========== END MATCHING ALGORITHM ==========     
    
    # Check if we have a search query from session
    search_query = request.session.pop('search_query', None)
    search_performed = request.session.pop('search_performed', False)
    
    if search_query and search_performed:
        # Apply search filtering (your existing search logic)
        age_range_match = re.match(r'(\d+)-(\d+)', search_query)
        if age_range_match:
            min_age = int(age_range_match.group(1))
            max_age = int(age_range_match.group(2))
            
            if min_age > max_age:
                min_age, max_age = max_age, min_age
            
            today = date.today()
            max_birth_date = today.replace(year=today.year - min_age)
            min_birth_date = today.replace(year=today.year - max_age - 1)
            
            suggested_profiles = suggested_profiles.filter(
                date_of_birth__gte=min_birth_date,
                date_of_birth__lte=max_birth_date
            )
        
        elif search_query.isdigit():
            age = int(search_query)
            today = date.today()
            min_birth_date = today.replace(year=today.year - age - 1)
            max_birth_date = today.replace(year=today.year - age)
            
            suggested_profiles = suggested_profiles.filter(
                date_of_birth__gte=min_birth_date,
                date_of_birth__lte=max_birth_date
            )
        
        else:
            search_conditions = Q()
            search_terms = search_query.split()
            
            for term in search_terms:
                term_condition = Q()
                term_condition |= Q(user__username__icontains=term)
                term_condition |= Q(user__first_name__icontains=term)
                term_condition |= Q(user__last_name__icontains=term)
                term_condition |= Q(headline__icontains=term)
                term_condition |= Q(about__icontains=term)
                term_condition |= Q(location__icontains=term)
                term_condition |= Q(my_interests__icontains=term)
                term_condition |= Q(pets__icontains=term)
                term_condition |= Q(diet__icontains=term)
                
                search_conditions &= term_condition
            
            suggested_profiles = suggested_profiles.filter(search_conditions)
    
    # ========== FIXED: ENHANCED ROTATION FOR FIRST 48 + ALL PROFILES BEYOND ==========
    def get_rotated_featured_profiles(profiles, user_id):
        """Get rotated featured profiles for first 48 spots - EXCLUDING BRAND NEW PROFILES"""
        
        # Get or create user's rotation index
        from django.core.cache import cache
        cache_key = f"user_{user_id}_rotation_index"
        rotation_index = cache.get(cache_key)
        
        if rotation_index is None:
            # Initialize rotation index based on user ID for different starting points
            rotation_index = user_id % 8  # 8 different starting positions
            cache.set(cache_key, rotation_index, 60 * 60 * 24)  # Store for 24 hours
        
        # EXCLUDE profiles created in the last 3 days from rotation pool
        three_days_ago = timezone.now() - timedelta(days=3)
        established_profiles = profiles.filter(created_at__lt=three_days_ago)
        
        # If we don't have enough established profiles, include some newer ones
        if established_profiles.count() < 48:
            # Get some newer profiles to fill the gap, but prioritize older ones
            one_day_ago = timezone.now() - timedelta(days=1)
            newer_profiles = profiles.filter(created_at__gte=three_days_ago, created_at__lt=one_day_ago)
            all_profiles = list(established_profiles) + list(newer_profiles)
            
            # ✅ FIX: Manually calculate photo_count for each profile when using lists
            for profile in all_profiles:
                profile.photo_count = profile.images.count()
            
            profiles_with_photos = all_profiles
        else:
            # ✅ FIX: Use annotate but keep as QuerySet
            profiles_with_photos = established_profiles.annotate(photo_count=Count('images'))
        
        # Create scoring system focused on photo-rich profiles
        profiles_list = list(profiles_with_photos)
        scored_profiles = []
        
        for profile in profiles_list:
            # Photo score (0-70 points) - heavily weighted toward profiles with photos
            photo_score = min(profile.photo_count, 4) * 17.5  # Max 4 photos = 70 points
            
            # Recency score (0-30 points) - lighter weight for recency
            days_old = (timezone.now() - profile.created_at).days
            recency_score = max(0, 30 - (days_old * 1.5))  # Newer profiles get higher score
            
            # Activity bonus (recently active users)
            last_login_bonus = 0
            if profile.user.last_login:
                days_since_login = (timezone.now() - profile.user.last_login).days
                if days_since_login <= 7:  # Active in last week
                    last_login_bonus = 10
            
            total_score = photo_score + recency_score + last_login_bonus
            scored_profiles.append((profile, total_score))
        
        # Sort by total score descending
        scored_profiles.sort(key=lambda x: x[1], reverse=True)
        
        # Take top 72 profiles for rotation pool (larger pool for better rotation)
        top_profiles = [p for p, score in scored_profiles[:72]]
        
        if not top_profiles:
            return []
        
        # Rotate the list based on rotation index (more movement for 48 profiles)
        rotation_offset = rotation_index * 6  # Move 6 positions each login for more noticeable change
        
        # Use modulo to wrap around
        rotated_profiles = top_profiles[rotation_offset:] + top_profiles[:rotation_offset]
        
        # Increment rotation index for next time (0-7 cycle)
        next_rotation = (rotation_index + 1) % 8
        cache.set(cache_key, next_rotation, 60 * 60 * 24)
        
        return rotated_profiles[:48]  # Return first 48 for pages 1-4
    
    def smart_profile_mixing(profiles, page_number, user_id):
        """Smart mixing algorithm with rotation for first 48 profiles + all profiles beyond"""
        
        from django.core.paginator import Paginator
        current_page = page_number or 1
        
        if current_page <= 4:
            # PAGES 1-4: Use rotated featured profiles
            rotated_profiles = get_rotated_featured_profiles(profiles, user_id)
            
            if rotated_profiles:
                # Get the slice for current page from rotated pool
                start_idx = (current_page - 1) * 12
                end_idx = start_idx + 12
                page_profiles = rotated_profiles[start_idx:end_idx]
                
                # Create paginator-like object for the full rotated set
                paginator = Paginator(profiles, 12)
                page_obj = paginator.page(current_page)
                page_obj.object_list = page_profiles
                
                return page_obj
            else:
                # Fallback: photo-rich profiles ordered by score
                fallback_profiles = profiles.annotate(
                    photo_count=Count('images')
                ).order_by('-photo_count', '-created_at')
                
                paginator = Paginator(fallback_profiles, 12)
                page_obj = paginator.page(current_page)
                return page_obj
            
        else:
            # PAGE 5+: Show ALL remaining profiles with proper pagination
            # Get IDs of profiles already shown in first 48
            rotated_profiles = get_rotated_featured_profiles(profiles, user_id)
            shown_ids = [p.id for p in rotated_profiles] if rotated_profiles else []
            
            # Get remaining profiles (excluding those already shown)
            remaining_profiles = profiles.exclude(id__in=shown_ids)
            
            # Create proper paginator for ALL remaining profiles
            paginator = Paginator(remaining_profiles, 12)
            page_obj = paginator.page(current_page)
            
            return page_obj
    
    # Get current page number
    try:
        page_number = int(request.GET.get('page', 1))
    except (TypeError, ValueError):
        page_number = 1
    
    # Apply smart mixing with rotation
    page_obj = smart_profile_mixing(suggested_profiles, page_number, request.user.id)
    
    context = {
        'profile': user_profile,
        'suggested_profiles': page_obj,
        'search_query': search_query,
        'search_performed': search_performed,
        'is_approved_user': is_approved_user,
    }
    return render(request, 'pages/gr8date_dashboard_fixed_v10_nolines.html', context)

@login_required
def search(request):
    """Enhanced search - redirect to dashboard with filtered results"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return redirect('dashboard')
    
    # ✅ ADDED: Track search activity (SAFE: Won't break search)
    track_user_activity(request.user, 'search_performed', request, {'query': query})
    
    # Store search query in session for dashboard to use
    request.session['search_query'] = query
    request.session['search_performed'] = True
    
    return redirect('dashboard')

# Profile Management
@login_required
def profile_view(request):
    """View current user's profile"""
    # ✅ ADDED: Track own profile view (SAFE: Won't break profile view)
    track_user_activity(request.user, 'profile_self_view', request)
    
    profile = get_object_or_404(Profile, user=request.user)
    context = {'profile': profile}
    return render(request, 'pages/profile_view.html', context)

@login_required
def profile_detail(request, user_id):
    """View another user's profile"""
    # ✅ ADDED: Track profile viewing (SAFE: Won't break profile detail)
    track_user_activity(
        request.user, 
        'profile_view', 
        request,
        {'viewed_user_id': user_id}
    )
    
    profile = get_object_or_404(
        Profile.objects.prefetch_related('images'),
        user_id=user_id
    )
    is_own_profile = request.user == profile.user
    
    # SUPERUSER PRIVILEGE: Superusers see all private photos without access requests
    has_private_access = False
    access_request = None
    has_pending_request = False
    
    if request.user.is_superuser:
        # Superusers automatically have access to all private photos
        has_private_access = True
    elif not is_own_profile and request.user.is_authenticated:
        access_request = PrivateAccessRequest.objects.filter(
            requester=request.user,
            target_user=profile.user
        ).first()
        
        if access_request:
            if access_request.status == 'approved':
                # Check if approval is still valid (72 hours)
                if access_request.reviewed_at and (timezone.now() - access_request.reviewed_at) < timedelta(hours=72):
                    has_private_access = True
                else:
                    # Auto-expire old approvals
                    access_request.status = 'expired'
                    access_request.save()
            elif access_request.status == 'pending':
                has_pending_request = True
    
    # Get images - FIXED: Use new image_type system
    public_images = profile.images.filter(image_type__in=['profile', 'additional'])
    private_images = profile.images.filter(image_type='private')
    
    # Check likes and blocks
    is_liked = Like.objects.filter(
        liker=request.user, 
        liked_user=profile.user
    ).exists()
    
    is_blocked = Block.objects.filter(
        blocker=request.user,
        blocked=profile.user
    ).exists()
    
    # Get next/previous profiles for navigation
    all_profiles = Profile.objects.filter(
        is_approved=True
    ).exclude(user=request.user).prefetch_related('images')
    
    current_index = None
    for idx, p in enumerate(all_profiles):
        if p.user_id == profile.user_id:
            current_index = idx
            break
    
    previous_profile_id = None
    next_profile_id = None
    
    if current_index is not None:
        if current_index > 0:
            previous_profile_id = all_profiles[current_index - 1].user_id
        if current_index < len(all_profiles) - 1:
            next_profile_id = all_profiles[current_index + 1].user_id
    
    context = {
        'profile': profile,
        'public_images': public_images,
        'private_images': private_images,
        'is_own_profile': is_own_profile,
        'has_private_access': has_private_access,
        'has_pending_request': has_pending_request,
        'access_request': access_request,
        'is_liked': is_liked,
        'is_blocked': is_blocked,
        'previous_profile_id': previous_profile_id,
        'next_profile_id': next_profile_id,
    }
    return render(request, 'pages/profile_view.html', context)

# Likes & Matching
@login_required
def like_user(request, user_id):
    """Like or unlike a user"""
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=user_id)
        
        # Don't allow liking yourself
        if request.user == target_user:
            return JsonResponse({'status': 'error', 'message': 'Cannot like yourself'})
        
        like, created = Like.objects.get_or_create(
            liker=request.user,
            liked_user=target_user
        )
        
        if not created:
            # ✅ ADDED: Track unlike (SAFE: Won't break like functionality)
            track_user_activity(
                request.user, 
                'user_unlike', 
                request,
                {'target_user_id': user_id}
            )
            like.delete()
            return JsonResponse({'status': 'success', 'action': 'unliked'})
        
        # ✅ ADDED: Track like (SAFE: Won't break like functionality)
        track_user_activity(
            request.user, 
            'user_like', 
            request,
            {'target_user_id': user_id}
        )
        
        # Check if it's a match (target user also liked current user)
        is_match = Like.objects.filter(
            liker=target_user,
            liked_user=request.user
        ).exists()
        
        # Create match message if it's a match
        if is_match:
            match_message = f"🎉 It's a match! You and {target_user.username} have liked each other."
            thread = Thread.get_or_create_for(request.user, target_user)
            Message.objects.create(
                thread=thread,
                sender=request.user,
                recipient=target_user,
                text=match_message
            )
        
        return JsonResponse({
            'status': 'success', 
            'action': 'liked',
            'is_match': is_match
        })
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def unfavorite_user(request, user_id):
    """Unfavorite a user (alias for unlike)"""
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=user_id)
        
        Like.objects.filter(
            liker=request.user,
            liked_user=target_user
        ).delete()
        
        # ✅ ADDED: Track unfavorite (SAFE: Won't break unfavorite functionality)
        track_user_activity(
            request.user, 
            'user_unfavorite', 
            request,
            {'target_user_id': user_id}
        )
        
        return JsonResponse({'status': 'success', 'action': 'unliked'})
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def likes_received(request):
    """View likes received by current user"""
    likes = Like.objects.filter(
        liked_user=request.user
    ).select_related('liker', 'liker__profile').prefetch_related('liker__profile__images')
    
    # ✅ ADDED: Track likes received view (SAFE: Won't break likes functionality)
    track_user_activity(request.user, 'likes_received_view', request)
    
    context = {'likes': likes}
    return render(request, 'pages/likes_received.html', context)

@login_required
def likes_given(request):
    """View likes given by current user"""
    likes = Like.objects.filter(
        liker=request.user
    ).select_related('liked_user', 'liked_user__profile').prefetch_related('liked_user__profile__images')
    
    # ✅ ADDED: Track likes given view (SAFE: Won't break likes functionality)
    track_user_activity(request.user, 'likes_given_view', request)
    
    context = {'likes': likes}
    return render(request, 'pages/likes_given.html', context)

@login_required
def matches_list(request):
    """View matches (mutual likes)"""
    # Get all likes given by current user
    likes_given = Like.objects.filter(
        liker=request.user
    ).select_related('liked_user', 'liked_user__profile').prefetch_related('liked_user__profile__images')
    
    # Get all likes received by current user  
    likes_received = Like.objects.filter(
        liked_user=request.user
    ).select_related('liker', 'liker__profile').prefetch_related('liker__profile__images')
    
    # Get all blocked users
    blocked_users = Block.objects.filter(
        blocker=request.user
    ).select_related('blocked', 'blocked__profile')
    
    # Calculate mutual matches
    given_user_ids = set(like.liked_user_id for like in likes_given)
    received_user_ids = set(like.liker_id for like in likes_received)
    match_user_ids = given_user_ids & received_user_ids
    
    # ✅ ADDED: Track matches view (SAFE: Won't break matches functionality)
    track_user_activity(request.user, 'matches_viewed', request)
    
    context = {
        'likes_given': likes_given,
        'likes_received': likes_received, 
        'blocked_users': blocked_users,
        'match_user_ids': match_user_ids,
    }
    return render(request, 'pages/matches_list.html', context)

# Messaging
@login_required
def messages_combined(request):
    """Combined messages view with threads and pending requests"""
    threads = Thread.objects.filter(
        Q(user_a=request.user) | Q(user_b=request.user)
    ).prefetch_related('messages').order_by('-updated_at')

    # Create thread data with other_user information
    thread_data = []
    for thread in threads:
        other_user = thread.get_other_user(request.user)
        unread_count = thread.messages.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        thread_data.append({
            'thread': thread,
            'other_user': other_user,
            'unread_count': unread_count,
            'last_message': thread.last_message,
            'updated_at': thread.updated_at
        })

    # Mark threads as read when user views them
    for thread in threads:
        thread.messages.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)

    # Get access requests for the current user
    pending_requests_received = PrivateAccessRequest.objects.filter(
        target_user=request.user,
        status='pending'
    ).select_related('requester', 'requester__profile')

    # ✅ ADDED: Track messages view (SAFE: Won't break messages functionality)
    track_user_activity(request.user, 'messages_viewed', request)

    context = {
        'threads': thread_data,
        'pending_requests_received': pending_requests_received
    }
    return render(request, 'pages/messages_combined.html', context)

@login_required
def message_thread(request, user_id):
    """View and send messages in a thread"""
    other_user = get_object_or_404(User, id=user_id)
    
    # Don't allow messaging yourself
    if request.user == other_user:
        messages.error(request, "You cannot message yourself")
        return redirect('messages_combined')
    
    # Get or create thread
    thread = Thread.get_or_create_for(request.user, other_user)
    
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            message = Message.objects.create(
                thread=thread,
                sender=request.user,
                recipient=other_user,
                text=text
            )
            
            # ✅ ADDED: Track message sent (SAFE: Won't break messaging)
            track_user_activity(
                request.user, 
                'message_sent', 
                request,
                {'recipient_id': user_id, 'message_id': message.id}
            )
            
            # Update thread timestamp
            thread.save()
            
            # Return message data for AJAX handling
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message_id': message.id,
                    'text': message.text,
                    'created_at': message.created_at.strftime('%b %d, %Y %H:%M'),
                    'sender_id': message.sender_id
                })
            else:
                return redirect('message_thread', user_id=user_id)
        
        # If empty text and AJAX
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Empty message'})
        else:
            return redirect('message_thread', user_id=user_id)
    
    # GET request - show the thread
    messages_list = thread.messages.all().order_by('created_at')
    
    # Mark messages as read when viewing thread
    thread.messages.filter(recipient=request.user, is_read=False).update(is_read=True)
    
    # ✅ ADDED: Track thread view (SAFE: Won't break thread functionality)
    track_user_activity(
        request.user, 
        'thread_viewed', 
        request,
        {'other_user_id': user_id}
    )
    
    context = {
        'thread': thread,
        'other_user': other_user,
        'messages': messages_list,
    }
    return render(request, 'pages/message_thread.html', context)

@login_required
@csrf_exempt
def send_quick_message(request, user_id):
    """Quick message sending endpoint"""
    if request.method == 'POST':
        other_user = get_object_or_404(User, id=user_id)
        text = request.POST.get('text', '').strip()
        
        if not text:
            return JsonResponse({'success': False, 'error': 'Empty message'})
        
        # Don't allow messaging yourself
        if request.user == other_user:
            return JsonResponse({'success': False, 'error': 'Cannot message yourself'})
        
        thread = Thread.get_or_create_for(request.user, other_user)
        message = Message.objects.create(
            thread=thread,
            sender=request.user,
            recipient=other_user,
            text=text
        )
        
        # ✅ ADDED: Track quick message (SAFE: Won't break quick messaging)
        track_user_activity(
            request.user, 
            'quick_message_sent', 
            request,
            {'recipient_id': user_id, 'message_id': message.id}
        )
        
        # Update thread timestamp
        thread.save()
        
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'text': message.text,
            'created_at': message.created_at.strftime('%b %d, %Y %H:%M'),
            'sender_id': message.sender_id
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def delete_conversation(request, thread_id):
    """Delete all messages in a conversation"""
    if request.method == 'POST':
        thread = get_object_or_404(Thread, id=thread_id)
        
        # Verify user is part of the thread
        if request.user not in [thread.user_a, thread.user_b]:
            return JsonResponse({'ok': False, 'error': 'Not authorized'})
        
        # Delete all messages in the thread
        thread.messages.all().delete()
        
        # ✅ ADDED: Track conversation deletion (SAFE: Won't break deletion)
        track_user_activity(
            request.user, 
            'conversation_deleted', 
            request,
            {'thread_id': thread_id}
        )
        
        return JsonResponse({'ok': True})
    
    return JsonResponse({'ok': False, 'error': 'Invalid method'})

@login_required
def messages_unread_count(request):
    """Return count of unread messages for the current user"""
    try:
        count = Message.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        return JsonResponse({'count': count})
    except Exception as e:
        return JsonResponse({'count': 0})

# Private Photo Access Views
@login_required
def request_private_access(request, user_id):
    """Request access to private photos"""
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=user_id)
        
        # Don't allow requesting access to yourself
        if request.user == target_user:
            return JsonResponse({'status': 'error', 'message': 'Cannot request access to your own photos'})
        
        # Check if already exists
        existing_request = PrivateAccessRequest.objects.filter(
            requester=request.user,
            target_user=target_user
        ).first()
        
        if existing_request:
            if existing_request.status == 'pending':
                return JsonResponse({'status': 'pending', 'message': 'Request already pending'})
            elif existing_request.status == 'approved':
                # Check if still valid
                if existing_request.reviewed_at and (timezone.now() - existing_request.reviewed_at) < timedelta(hours=72):
                    return JsonResponse({'status': 'already_approved', 'message': 'You already have access'})
                else:
                    # Expired approval, create new request
                    existing_request.delete()
        
        # Create new request
        access_request = PrivateAccessRequest.objects.create(
            requester=request.user,
            target_user=target_user
        )
        
        # ✅ ADDED: Track private access request (SAFE: Won't break access requests)
        track_user_activity(
            request.user, 
            'private_access_requested', 
            request,
            {'target_user_id': user_id}
        )
        
        # Send notification message to target user
        message_text = f"🔒 {request.user.username} requested access to your private photos. Go to your pending requests to approve or deny."
        Message.objects.create(
            thread=Thread.get_or_create_for(request.user, target_user),
            sender=request.user,
            recipient=target_user,
            text=message_text
        )
        
        return JsonResponse({'status': 'request_sent', 'message': 'Access request sent!'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def approve_private_access(request, request_id):
    """Approve private photo access request"""
    access_request = get_object_or_404(
        PrivateAccessRequest, 
        id=request_id, 
        target_user=request.user
    )
    
    if access_request.status == 'pending':
        access_request.status = 'approved'
        access_request.reviewed_by = request.user
        access_request.reviewed_at = timezone.now()
        access_request.save()
        
        # ✅ ADDED: Track private access approval (SAFE: Won't break approval)
        track_user_activity(
            request.user, 
            'private_access_approved', 
            request,
            {'requester_id': access_request.requester.id}
        )
        
        # Send approval message with 72-hour notice
        approval_message = f"✅ {request.user.username} approved your private photo access request! You can now view their private photos for 72 hours."
        Message.objects.create(
            thread=Thread.get_or_create_for(request.user, access_request.requester),
            sender=request.user,
            recipient=access_request.requester,
            text=approval_message
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'approved', 'message': 'Access granted for 72 hours!'})
        else:
            return redirect('messages_combined')
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def deny_private_access(request, request_id):
    """Deny private photo access request"""
    access_request = get_object_or_404(
        PrivateAccessRequest, 
        id=request_id, 
        target_user=request.user
    )
    
    if access_request.status == 'pending':
        access_request.status = 'denied'
        access_request.reviewed_by = request.user
        access_request.reviewed_at = timezone.now()
        access_request.save()
        
        # ✅ ADDED: Track private access denial (SAFE: Won't break denial)
        track_user_activity(
            request.user, 
            'private_access_denied', 
            request,
            {'requester_id': access_request.requester.id}
        )
        
        # Send denial message
        denial_message = f"❌ {request.user.username} denied your private photo access request."
        Message.objects.create(
            thread=Thread.get_or_create_for(request.user, access_request.requester),
            sender=request.user,
            recipient=access_request.requester,
            text=denial_message
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'denied', 'message': 'Access denied'})
        else:
            return redirect('messages_combined')
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def pending_requests(request):
    """View pending private access requests"""
    pending_requests_list = PrivateAccessRequest.objects.filter(
        target_user=request.user,
        status='pending'
    ).select_related('requester', 'requester__profile')
    
    # ✅ ADDED: Track pending requests view (SAFE: Won't break requests)
    track_user_activity(request.user, 'pending_requests_viewed', request)
    
    context = {
        'pending_requests': pending_requests_list
    }
    return render(request, 'pages/pending_requests.html', context)

# Blog
def blog_list(request):
    """List published blog posts"""
    posts = Blog.objects.filter(
        status='published',
        published_at__lte=timezone.now()
    ).order_by('-published_at')
    
    # Add pagination
    paginator = Paginator(posts, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # ✅ ADDED: Track blog list view (SAFE: Won't break blog)
    if request.user.is_authenticated:
        track_user_activity(request.user, 'blog_list_viewed', request)
    
    context = {
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'posts': page_obj.object_list
    }
    return render(request, 'pages/blog_list.html', context)

def blog_detail(request, slug):
    """View individual blog post"""
    post = get_object_or_404(Blog, slug=slug, status='published')
    
    # ✅ ADDED: Track blog detail view (SAFE: Won't break blog)
    if request.user.is_authenticated:
        track_user_activity(
            request.user, 
            'blog_post_viewed', 
            request,
            {'post_slug': slug, 'post_title': post.title}
        )
    
    context = {'post': post}
    return render(request, 'pages/blog_detail.html', context)

# Admin Approval System
@login_required
def admin_profile_approvals(request):
    """Admin view for profile approvals"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    pending_profiles = Profile.objects.filter(is_approved=False).select_related('user')
    
    # ✅ ADDED: Track admin approvals view (SAFE: Won't break admin)
    track_user_activity(request.user, 'admin_approvals_viewed', request)
    
    context = {'pending_profiles': pending_profiles}
    return render(request, 'pages/admin_approvals.html', context)

@login_required
def admin_reject_profile(request, profile_id):
    """Reject a profile (admin only)"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    profile = get_object_or_404(Profile, id=profile_id)
    username = profile.user.username
    profile.delete()
    
    # ✅ ADDED: Track admin rejection (SAFE: Won't break admin)
    track_user_activity(
        request.user, 
        'admin_profile_rejected', 
        request,
        {'rejected_username': username}
    )
    
    messages.success(request, f"Profile for {username} has been rejected and deleted.")
    return redirect('admin_profile_approvals')

# NEW ADMIN VIEW FOR NEW PROFILES
@login_required
def admin_new_profile(request):
    """Admin view for new profiles that need approval"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    # Get profiles that are not yet approved
    new_profiles = Profile.objects.filter(
        is_approved=False
    ).select_related('user').prefetch_related('images').order_by('-created_at')
    
    # ✅ ADDED: Track admin new profiles view (SAFE: Won't break admin)
    track_user_activity(request.user, 'admin_new_profiles_viewed', request)
    
    context = {
        'new_profiles': new_profiles,
        'title': 'New Profiles - Admin'
    }
    return render(request, 'pages/admin_new_profiles.html', context)

# NEW ADMIN QUICK APPROVE PROFILE
@login_required
def admin_quick_approve_profile(request, profile_id):
    """Quick approve a profile via AJAX (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Not authorized'})
    
    if request.method == 'POST':
        try:
            profile = get_object_or_404(Profile, id=profile_id)
            profile.is_approved = True
            profile.approved_at = timezone.now()
            profile.approved_by = request.user
            
            # SECURITY FIX: Capture approved content state
            profile.capture_approved_state()
            
            profile.save()
            
            # ✅ ADDED: Track admin quick approval (SAFE: Won't break admin)
            track_user_activity(
                request.user, 
                'admin_quick_approve', 
                request,
                {'approved_user_id': profile.user.id}
            )
            
            # Send profile approved email
            try:
                login_url = request.build_absolute_uri(reverse('dashboard'))
                send_profile_approved_email(profile.user.email, profile.user.username, login_url)
            except Exception as e:
                print(f"DEBUG: Profile approved email failed: {e}")
            
            return JsonResponse({
                'success': True, 
                'message': f'Profile for {profile.user.username} approved successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': f'Error approving profile: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

# ======================
# NEW ADMIN NOTIFICATION SYSTEM
# ======================

@login_required
def admin_new_signups(request):
    """Admin view for ALL users (even incomplete profiles)"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    try:
        # Get all users with their profiles
        users = User.objects.all().select_related('profile').order_by('-date_joined')
        
        # Calculate statistics
        total_users = users.count()
        approved_count = users.filter(profile__is_approved=True).count()
        verified_count = users.filter(profile__email_verified=True).count()
        pending_count = users.filter(profile__is_approved=False).count()
        
        # Handle users without profiles
        users_without_profiles = users.filter(profile__isnull=True)
        incomplete_count = users_without_profiles.count()
        
        # ✅ ADDED: Track admin signups view (SAFE: Won't break admin)
        track_user_activity(request.user, 'admin_signups_viewed', request)
        
        context = {
            'users': users,
            'total_users': total_users,
            'approved_count': approved_count,
            'verified_count': verified_count,
            'pending_count': pending_count,
            'incomplete_count': incomplete_count,
            'title': 'All Users - Admin'
        }
        return render(request, 'pages/admin_new_signups.html', context)
    
    except Exception as e:
        print(f"DEBUG: Error in admin_new_signups: {e}")
        # Fallback context if queries fail
        context = {
            'users': User.objects.all().order_by('-date_joined'),
            'total_users': 0,
            'approved_count': 0,
            'verified_count': 0,
            'pending_count': 0,
            'incomplete_count': 0,
            'title': 'All Users - Admin',
            'error': str(e)
        }
        return render(request, 'pages/admin_new_signups.html', context)

@login_required
def admin_send_message(request, profile_id):
    """Allow admins to message users about profile changes"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    profile = get_object_or_404(Profile, id=profile_id)
    
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        
        if message_text:
            # Create admin message
            admin_message = AdminMessage.objects.create(
                profile=profile,
                admin_user=request.user,
                message=message_text
            )
            
            # ✅ ADDED: Track admin message sent (SAFE: Won't break admin)
            track_user_activity(
                request.user, 
                'admin_message_sent', 
                request,
                {'target_user_id': profile.user.id}
            )
            
            # Send email notification to user
            try:
                profile_edit_url = request.build_absolute_uri(reverse('profile_edit'))
                send_admin_message_notification(
                    profile.user.email, 
                    profile.user.username, 
                    message_text, 
                    profile_edit_url
                )
            except Exception as e:
                print(f"DEBUG: Admin message notification email failed: {e}")
            
            messages.success(request, f"Message sent to {profile.user.username}")
            return redirect('admin_new_profiles')
        else:
            messages.error(request, "Message cannot be empty")
    
    context = {
        'profile': profile,
        'title': f'Send Message to {profile.user.username}'
    }
    return render(request, 'pages/admin_send_message.html', context)

def verify_email(request, token):
    """Handle email verification links - DEVELOPMENT MODE"""
    print(f"🎯 DEBUG: Verification attempted with token: {token}")
    
    # AUTO-VERIFY for development - remove time restriction
    try:
        profile = Profile.objects.get(email_verification_token=token)
        if not profile.email_verified:
            profile.email_verified = True
            profile.save()
            
            # ✅ ADDED: Track email verification (SAFE: Won't break verification)
            track_user_activity(
                profile.user, 
                'email_verified', 
                request
            )
            
            messages.success(request, "✅ Email verified successfully! (Development Mode)")
            print(f"✅ AUTO-VERIFIED: {profile.user.username}")
        else:
            messages.info(request, "✅ Email already verified.")
            print(f"ℹ️ Already verified: {profile.user.username}")
    except Profile.DoesNotExist:
        messages.error(request, "❌ Invalid verification token")
        print(f"❌ Token not found: {token}")
    
    # Redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('home')

# Blocking
@login_required
def block_user(request, user_id):
    """Block a user"""
    if request.method == 'POST':
        try:
            target_user = get_object_or_404(User, id=user_id)
            
            # Don't allow blocking yourself
            if request.user == target_user:
                return JsonResponse({'status': 'error', 'message': 'Cannot block yourself'})
    
            block, created = Block.objects.get_or_create(
                blocker=request.user,
                blocked=target_user
            )

            # ✅ ADDED: Track user block (SAFE: Won't break blocking)
            track_user_activity(
                request.user, 
                'user_blocked', 
                request,
                {'blocked_user_id': user_id}
            )

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'User blocked successfully'})
            return redirect('profile_detail', user_id=user_id)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def unblock_user(request, user_id):
    """Unblock a user"""
    if request.method == 'POST':
        try:
            target_user = get_object_or_404(User, id=user_id)

            Block.objects.filter(
                blocker=request.user,
                blocked=target_user
            ).delete()
            
            # ✅ ADDED: Track user unblock (SAFE: Won't break unblocking)
            track_user_activity(
                request.user, 
                'user_unblocked', 
                request,
                {'unblocked_user_id': user_id}
            )
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'User unblocked successfully'})
            return redirect('profile_detail', user_id=user_id)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

# ======================
# HotDates - WITH MISSING hotdate_detail VIEW ADDED
# ======================

@login_required
def hotdates_new_count(request):
    """Count new Hot Dates AND cancellation notifications for the current user"""
    try:
        # Get Hot Dates created in the last 24 hours that the user hasn't viewed
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        # Get Hot Dates created recently that user hasn't viewed
        new_hotdates_count = HotDate.objects.filter(
            created_at__gte=cutoff_time,
            is_active=True,
            is_cancelled=False
        ).exclude(
            views__user=request.user
        ).count()
        
        # Get unread cancellation notifications
        cancellation_notifications_count = HotDateNotification.objects.filter(
            user=request.user,
            is_read=False,
            notification_type='cancelled'
        ).count()
        
        total_count = new_hotdates_count + cancellation_notifications_count
        
        return JsonResponse({
            'count': total_count,
            'preview': getattr(request, 'preview_mode', False)
        })
        
    except Exception as e:
        return JsonResponse({
            'count': 0,
            'preview': getattr(request, 'preview_mode', False)
        })

@login_required
def hotdate_list(request):
    """Display list of Hot Dates with cancellation status"""
    hot_dates = HotDate.objects.filter(
        is_active=True,
        date_time__gte=timezone.now()
    ).order_by('date_time')
    
    # Get which Hot Dates the user has already viewed
    viewed_hotdates = HotDateView.objects.filter(
        user=request.user
    ).values_list('hot_date_id', flat=True)
    
    # Mark cancellation notifications as read when user views the list
    HotDateNotification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)
    
    # ✅ ADDED: Track hotdate list view (SAFE: Won't break hotdates)
    track_user_activity(request.user, 'hotdate_list_viewed', request)
    
    return render(request, 'pages/hotdate_list.html', {
        'hot_dates': hot_dates,
        'viewed_hotdates': viewed_hotdates
    })

# ✅ ADDED: MISSING hotdate_detail VIEW
@login_required
def hotdate_detail(request, hotdate_id):
    """Display Hot Date details"""
    hot_date = get_object_or_404(HotDate, id=hotdate_id)
    
    # Mark as viewed by current user
    HotDateView.objects.get_or_create(
        user=request.user,
        hot_date=hot_date
    )
    
    # ✅ ADDED: Track hotdate detail view (SAFE: Won't break hotdate detail)
    track_user_activity(
        request.user, 
        'hotdate_viewed', 
        request,
        {'hotdate_id': hotdate_id, 'activity': hot_date.activity}
    )
    
    return render(request, 'pages/hotdate_detail.html', {
        'hot_date': hot_date
    })

@login_required
def hotdate_mark_seen(request, hotdate_id):
    """Mark a Hot Date as seen by the user"""
    try:
        hot_date = HotDate.objects.get(id=hotdate_id)
        HotDateView.objects.get_or_create(
            user=request.user,
            hot_date=hot_date
        )
        return JsonResponse({'success': True})
    except HotDate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Hot Date not found'})

@login_required
def hotdate_cancel(request, hotdate_id):
    """Cancel a Hot Date and send notifications to interested users"""
    try:
        hot_date = HotDate.objects.get(id=hotdate_id, host=request.user)
        
        # Mark as cancelled
        hot_date.is_cancelled = True
        hot_date.cancelled_at = timezone.now()
        hot_date.save()
        
        # ✅ ADDED: Track hotdate cancellation (SAFE: Won't break cancellation)
        track_user_activity(
            request.user, 
            'hotdate_cancelled', 
            request,
            {'hotdate_id': hotdate_id, 'activity': hot_date.activity}
        )
        
        # Send cancellation notifications to users who viewed this Hot Date
        viewers = HotDateView.objects.filter(hot_date=hot_date).exclude(user=request.user)
        for view in viewers:
            HotDateNotification.objects.create(
                user=view.user,
                hot_date=hot_date,
                notification_type='cancelled',
                message=f"Hot Date '{hot_date.activity}' has been cancelled by the host"
            )
        
        return JsonResponse({
            'success': True, 
            'message': 'Hot Date cancelled successfully. Notifications sent to interested users.'
        })
        
    except HotDate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Hot Date not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def hotdate_notification_mark_read(request, notification_id):
    """Mark a Hot Date notification as read"""
    try:
        notification = HotDateNotification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return JsonResponse({'success': True})
    except HotDateNotification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})

# Activity Tracking
@login_required
def track_activity(request, activity_type):
    """Track user activity for analytics"""
    if request.user.is_authenticated:
        UserActivity.objects.create(
            user=request.user,
            activity_type=activity_type
        )
    return JsonResponse({'status': 'success'})

# Profile Creation Views
@login_required
def create_profile(request):
    """Handle comprehensive profile creation for new users"""
    # If user already has an approved profile, redirect to dashboard
    try:
        existing_profile = Profile.objects.get(user=request.user)
        if existing_profile.is_approved:
            return redirect('dashboard')
    except Profile.DoesNotExist:
        pass
    
    if request.method == 'POST':
        try:
            # Get or create profile
            profile, created = Profile.objects.get_or_create(user=request.user)
            
            # Update user's username
            username = request.POST.get('username', '').strip()
            if username and username != request.user.username:
                # Check if username is available
                if not User.objects.filter(username=username).exclude(id=request.user.id).exists():
                    request.user.username = username
                    request.user.save()
            
            # Update profile fields
            profile.headline = request.POST.get('headline', '')
            profile.about = request.POST.get('about', '')
            profile.location = request.POST.get('location', '')
            
            # Handle date of birth
            date_of_birth = request.POST.get('date_of_birth')
            if date_of_birth:
                profile.date_of_birth = date_of_birth
            
            profile.my_gender = request.POST.get('my_gender', '')
            profile.looking_for = request.POST.get('looking_for', '')
            
            # Handle array fields (convert to comma-separated strings)
            my_interests = request.POST.getlist('my_interests[]')
            profile.my_interests = ','.join(my_interests) if my_interests else ''
            
            # ✅ SYNCED: ADD missing fields from forms
            profile.body_type = request.POST.get('body_type', '')
            profile.ethnicity = request.POST.get('ethnicity', '')
            profile.relationship_status = request.POST.get('relationship_status', '')
            profile.children = request.POST.get('children', '')
            profile.want_children = request.POST.get('want_children', '')
            profile.smoking = request.POST.get('smoking', '')
            profile.drinking = request.POST.get('drinking', '')
            profile.preferred_intent = request.POST.get('preferred_intent', '')
            
            # Mark as submitted for approval (but not approved yet)
            profile.is_approved = False
            profile.save()
            
            # ✅ ADDED: Track profile creation (SAFE: Won't break profile creation)
            track_user_activity(request.user, 'profile_created', request)
            
            # Send profile submitted email
            try:
                send_profile_submitted_email(request.user.email, request.user.username)
            except Exception as e:
                print(f"DEBUG: Profile submitted email failed: {e}")
            
            messages.success(request, 'Profile submitted for admin approval! You can now browse profiles in preview mode.')
            return redirect('preview_gate')
            
        except Exception as e:
            messages.error(request, f'Error creating profile: {str(e)}')
            print(f"DEBUG: Profile creation error: {e}")
    
    # GET request - show the form
    context = {}
    return render(request, 'pages/create_your_profile.html', context)

@login_required
def check_username(request):
    """Check if username is available"""
    username = request.GET.get('username', '').strip().lower()
    
    if not username or len(username) < 3:
        return JsonResponse({'available': False, 'error': 'Username too short'})
    
    # Check if username exists (excluding current user)
    exists = User.objects.filter(username__iexact=username).exclude(id=request.user.id).exists()
    
    return JsonResponse({'available': not exists})

@login_required
def preview_profile_detail(request, user_id):
    """Limited profile viewing for unapproved users"""
    # Redirect to full dashboard if user is approved
    try:
        user_profile = Profile.objects.get(user=request.user)
        if user_profile.is_approved or request.user.is_staff:
            return redirect('profile_detail', user_id=user_id)
    except Profile.DoesNotExist:
        pass
    
    # FIXED: Only allow preview of the 12 specific profiles
    fixed_profile_ids = [470, 365, 361, 358, 356, 717, 459, 301, 208, 207, 205, 363]
    
    # Get the target profile WITH IMAGES PREFETCHED
    profile = get_object_or_404(
        Profile.objects.prefetch_related('images'),
        user_id=user_id, 
        is_approved=True
    )
    
    # Security check: Only allow preview of the 12 fixed profiles
    if profile.id not in fixed_profile_ids:
        return redirect('preview_gate')
    
    # ✅ ADDED: Track preview profile view (SAFE: Won't break preview)
    track_user_activity(
        request.user, 
        'preview_profile_viewed', 
        request,
        {'viewed_user_id': user_id}
    )
    
    # Only show limited information
    context = {
        'profile': profile,
        'is_own_profile': False,
        'is_preview_mode': True,  # New flag for preview mode
    }
    return render(request, 'pages/preview_profile_detail.html', context)

@login_required
@csrf_exempt
def create_profile_api(request):
    """API endpoint for comprehensive profile creation - SYNCED WITH FRONTEND"""
    if request.method == 'POST':
        try:
            # Get or create profile
            profile, created = Profile.objects.get_or_create(user=request.user)

            # Update user's username
            username = request.POST.get('username', '').strip()
            if username and username != request.user.username:
                # Check if username is available
                if not User.objects.filter(username=username).exclude(id=request.user.id).exists():
                    request.user.username = username
                    request.user.save()
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Username is already taken'
                    }, status=400)
    
            # Update profile fields
            profile.headline = request.POST.get('headline', '')
            profile.about = request.POST.get('about', '')
            profile.location = request.POST.get('location', '')
        
            # Handle date of birth
            date_of_birth = request.POST.get('date_of_birth')
            if date_of_birth:   
                profile.date_of_birth = date_of_birth
        
            profile.my_gender = request.POST.get('my_gender', '')
            profile.looking_for = request.POST.get('looking_for', '')

            # Handle array fields (convert to comma-separated strings)
            my_interests = request.POST.getlist('my_interests') or request.POST.getlist('my_interests[]')
            profile.my_interests = ','.join(my_interests) if my_interests else ''
        
            # ✅ SYNCED: ADD missing fields from forms
            profile.body_type = request.POST.get('body_type', '')
            profile.ethnicity = request.POST.get('ethnicity', '')
            profile.relationship_status = request.POST.get('relationship_status', '')
            profile.children = request.POST.get('children', '')
            profile.want_children = request.POST.get('want_children', '')
            profile.smoking = request.POST.get('smoking', '')
            profile.drinking = request.POST.get('drinking', '')
            profile.preferred_intent = request.POST.get('preferred_intent', '')
        
            # Handle profile photo 
            profile_photo_id = request.POST.get('profile_photo_id')
            if profile_photo_id:
                try:
                    # Set this as primary photo
                    profile_image = ProfileImage.objects.get(id=profile_photo_id, profile=profile)
                    # FIXED LINE: Complete the method call
                    ProfileImage.objects.filter(profile=profile, image_type='profile').exclude(id=profile_image.id).update(image_type='additional')
                    profile_image.image_type = 'profile'
                    profile_image.is_primary = True
                    profile_image.save()
                except ProfileImage.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Profile photo not found'
                    }, status=400)
                    
            # Mark as submitted for approval
            profile.is_complete = True
            profile.last_submitted_for_approval = timezone.now()
            
            # Generate verification token
            profile.email_verification_token = secrets.token_urlsafe(32)
            profile.email_verification_sent_at = timezone.now()
            profile.save()
            
            # ✅ ADDED: Track profile API creation (SAFE: Won't break API)
            track_user_activity(request.user, 'profile_api_created', request)
            
            # Send profile submitted email
            try:
                send_profile_submitted_email(request.user.email, request.user.username)
            except Exception as e:
                print(f"DEBUG: Profile submitted email failed: {e}")
            
            # Send email verification to user
            try:
                verification_url = request.build_absolute_uri(
                    reverse('verify_email', kwargs={'token': profile.email_verification_token})
                )
                send_email_verification_email(request.user.email, request.user.username, verification_url)
            except Exception as e:
                print(f"DEBUG: Verification email failed: {e}")
            
            # Notify admins about new submission
            try:
                admin_emails = User.objects.filter(
                    is_staff=True,
                    is_active=True 
                ).values_list('email', flat=True)
            
                profile_url = request.build_absolute_uri(
                    reverse('admin_new_profiles')
                )
                    
                for admin_email in admin_emails:
                    if admin_email:
                        send_admin_notification_email(admin_email, request.user.username, profile_url)
            except Exception as e:
                print(f"DEBUG: Admin notification failed: {e}")
                        
            return JsonResponse({ 
                'success': True,
                'message': 'Profile submitted for admin approval! Please check your email for verification.',
                'profile_id': profile.id
            })
            
        except Exception as e:
            print(f"DEBUG: Profile creation error: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Profile creation failed: {str(e)}'
            }, status=500)
            
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

# ======================
# ✅ ADDED: CUSTOM LOGOUT WITH ACTIVITY TRACKING
# ======================

from django.contrib.auth import logout

@login_required
def custom_logout(request):
    """Custom logout with activity tracking - SAFE: Won't break existing logout"""
    # ✅ Track logout before logging out
    track_user_activity(request.user, 'user_logout', request)
    
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')

# ======================
# ✅ ADDED: TEST ACTIVITY TRACKING VIEW
# ======================

@login_required
def test_activity_tracking(request):
    """Temporary view to test activity tracking - SAFE: Can be removed later"""
    if request.user.is_authenticated:
        # Create test activities
        track_user_activity(request.user, 'login', request)
        track_user_activity(request.user, 'profile_view', request, {'test': True})
        track_user_activity(request.user, 'test_action', request)
        
        from django.contrib import messages
        messages.success(request, "Test activities created! Check UserActivity admin.")
        return redirect('admin:pages_useractivity_changelist')
    return redirect('login')

# ======================
# ERROR HANDLING
# ======================

def handler404(request, exception):
    """Custom 404 error handler"""
    return render(request, 'pages/404.html', status=404)

def handler500(request):
    """Custom 500 error handler"""
    return render(request, 'pages/500.html', status=500)

# ======================
# HELPER FUNCTIONS
# ======================

def log_user_activity(user, activity_type, request, admin_message=None, target_user_id=None):
    """Helper function to log user activity"""
    try:
        activity = UserActivity.objects.create(
            user=user,
            activity_type=activity_type,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            admin_message=admin_message,
            target_user_id=target_user_id
        )
        return activity
    except Exception as e:
        print(f"DEBUG: Error logging activity: {e}")
        return None

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
