# pages/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date, datetime
import json
from django.db.models import Q
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
            
            # Create initial profile
            Profile.objects.create(user=user)
            
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
            # Create profile if it doesn't exist
            Profile.objects.create(user=request.user)
    
    return render(request, 'pages/preview_gate.html')

@login_required
def browse_preview(request):
    """Preview browsing for unapproved users"""
    try:
        user_profile = Profile.objects.get(user=request.user)
        if user_profile.is_approved or request.user.is_staff:
            return redirect('dashboard')
    except Profile.DoesNotExist:
        pass
    
    # Show limited profiles for preview with images prefetched
    profiles = Profile.objects.filter(
        is_approved=True
    ).prefetch_related('images'
    ).exclude(
        Q(user=request.user) |
        Q(user__in=Block.objects.filter(blocker=request.user).values('blocked')) |
        Q(user__in=Block.objects.filter(blocked=request.user).values('blocker'))
    ).order_by('-created_at')
    
    paginator = Paginator(profiles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
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
    """Main dashboard with PROFILE MATCHING based on gender preferences"""
    try:
        user_profile = Profile.objects.get(user=request.user)
        is_approved_user = user_profile.is_approved
    except Profile.DoesNotExist:
        is_approved_user = False
        user_profile = None
    
    # Redirect to preview gate if not approved
    if not is_approved_user and not request.user.is_staff:
        return redirect('preview_gate')
    
    # ========== ENHANCED GENDER MATCHING ALGORITHM ==========
    def get_genders_user_wants(looking_for):
        """Convert 'looking_for' to list of genders user wants to see"""
        mapping = {
            'male': ['male'],
            'female': ['female'],
            'bisexual': ['male', 'female'],
            'unspecified': ['male', 'female', 'nonbinary']
        }
        return mapping.get(looking_for, ['male', 'female', 'nonbinary'])
    
    def who_wants_my_gender(my_gender):
        """Convert my gender to what others would look for to see me"""
        mapping = {
            'male': ['male', 'bisexual', 'unspecified'],
            'female': ['female', 'bisexual', 'unspecified'],
            'nonbinary': ['unspecified'],
            'unspecified': ['male', 'female', 'bisexual', 'unspecified']
        }
        return mapping.get(my_gender, ['unspecified'])
    
    # Start with base queryset
    if user_profile and user_profile.is_approved and not request.user.is_superuser:
        # TWO-WAY MATCHING for regular users: 
        # 1. Their gender matches what I'm looking for
        # 2. AND they are looking for my gender
        suggested_profiles = Profile.objects.filter(
            is_approved=True
        ).filter(
            # Their gender is what I want
            my_gender__in=get_genders_user_wants(user_profile.looking_for),
            # AND they want my gender
            looking_for__in=who_wants_my_gender(user_profile.my_gender)
        )
    else:
        # Superusers see ALL profiles, or fallback for unapproved users
        suggested_profiles = Profile.objects.filter(is_approved=True)
    
    # Exclude blocked users and self
    suggested_profiles = suggested_profiles.exclude(
        Q(user=request.user) |
        Q(user__in=Block.objects.filter(blocker=request.user).values('blocked')) |
        Q(user__in=Block.objects.filter(blocked=request.user).values('blocker'))
    ).prefetch_related('images').order_by('-created_at')
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
                term_condition |= Q(must_have_tags__icontains=term)
                term_condition |= Q(pets__icontains=term)
                term_condition |= Q(diet__icontains=term)
                
                search_conditions &= term_condition
            
            suggested_profiles = suggested_profiles.filter(search_conditions)
    
    # Order and paginate
    suggested_profiles = suggested_profiles.order_by('-created_at')
    paginator = Paginator(suggested_profiles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
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
    
    # Store search query in session for dashboard to use
    request.session['search_query'] = query
    request.session['search_performed'] = True
    
    return redirect('dashboard')

# Profile Management
@login_required
def profile_view(request):
    """View current user's profile"""
    profile = get_object_or_404(Profile, user=request.user)
    context = {'profile': profile}
    return render(request, 'pages/profile_view.html', context)

@login_required
def profile_edit(request):
    """Edit current user's profile"""
    profile = get_object_or_404(Profile, user=request.user)
     
    if request.method == 'POST':
        try:
            # Update profile fields
            profile.headline = request.POST.get('headline', '')
            profile.about = request.POST.get('about', '')
            profile.location = request.POST.get('location', '')
            profile.my_gender = request.POST.get('my_gender', '')
            profile.looking_for = request.POST.get('looking_for', '')
            profile.my_interests = request.POST.get('my_interests', '')
            profile.children = request.POST.get('children', '')
            
            # Handle age preferences with validation
            preferred_age_min = int(request.POST.get('preferred_age_min', 18))
            preferred_age_max = int(request.POST.get('preferred_age_max', 99))
            
            if preferred_age_min < 18:
                preferred_age_min = 18
            if preferred_age_max > 99:
                preferred_age_max = 99
            if preferred_age_min > preferred_age_max:
                preferred_age_min, preferred_age_max = preferred_age_max, preferred_age_min
            
            profile.preferred_age_min = preferred_age_min
            profile.preferred_age_max = preferred_age_max
            
            profile.preferred_intent = request.POST.get('preferred_intent', '')
            profile.preferred_distance = request.POST.get('preferred_distance', '')
            profile.save()
            
            messages.success(request, "Profile updated successfully!")
            return redirect('profile_view')
            
        except Exception as e:
            messages.error(request, f"Error updating profile: {str(e)}")
    
    context = {
        'me': profile,
        'ages': range(18, 81),
    }
    return render(request, 'pages/profile_edit.html', context)

@login_required
def profile_detail(request, user_id):
    """View another user's profile"""
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
    
    # Get images
    public_images = profile.images.filter(is_private=False)
    private_images = profile.images.filter(is_private=True)
    
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

@login_required
@csrf_exempt
def upload_profile_image(request):
    """Upload profile image (legacy endpoint)"""
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            is_private = request.POST.get('is_private') == 'true'
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return JsonResponse({
                    'success': False, 
                    'error': 'Invalid file type. Please upload JPEG, PNG, GIF, or WebP.'
                }, status=400)
            
            # Validate file size (max 5MB)
            if image_file.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'error': 'File too large. Maximum size is 5MB.'
                }, status=400)
            
            # Get or create user profile
            profile, created = Profile.objects.get_or_create(user=request.user)
            
            # Create new ProfileImage
            profile_image = ProfileImage.objects.create(
                profile=profile,
                image=image_file,
                is_private=is_private
            )
            
            return JsonResponse({
                'success': True, 
                'image_id': profile_image.id,
                'image_url': profile_image.image.url
            })
            
        except Exception as e:
            print(f"DEBUG: Error uploading image: {e}")
            return JsonResponse({
                'success': False, 
                'error': f'Upload failed: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False, 
        'error': 'No image file provided'
    }, status=400)

@login_required
def delete_image(request, image_id):
    """Delete profile image (legacy endpoint)"""
    try:
        image = ProfileImage.objects.get(id=image_id, profile__user=request.user)
        image.delete()
        return JsonResponse({'success': True})
    except ProfileImage.DoesNotExist:
        return JsonResponse({'success': False}, status=404)

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
            like.delete()
            return JsonResponse({'status': 'success', 'action': 'unliked'})
        
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
        
        return JsonResponse({'status': 'success', 'action': 'unliked'})
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def likes_received(request):
    """View likes received by current user"""
    likes = Like.objects.filter(
        liked_user=request.user
    ).select_related('liker', 'liker__profile').prefetch_related('liker__profile__images')
    
    context = {'likes': likes}
    return render(request, 'pages/likes_received.html', context)

@login_required
def likes_given(request):
    """View likes given by current user"""
    likes = Like.objects.filter(
        liker=request.user
    ).select_related('liked_user', 'liked_user__profile').prefetch_related('liked_user__profile__images')
    
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
        print(f"DEBUG: Error in messages_unread_count: {e}")
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
    
    context = {
        'pending_requests': pending_requests_list
    }
    return render(request, 'pages/pending_requests.html', context)

# Blog - FIXED PAGINATION
def blog_list(request):
    """List published blog posts"""
    posts = Blog.objects.filter(
        status='published',
        published_at__lte=timezone.now()
    ).order_by('-published_at')
    
    # Add pagination (9 posts per page as your grid shows 3 columns)
    paginator = Paginator(posts, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'posts': page_obj.object_list  # Include both for flexibility
    }
    return render(request, 'pages/blog_list.html', context)

def blog_detail(request, slug):
    """View individual blog post"""
    post = get_object_or_404(Blog, slug=slug, status='published')
    context = {'post': post}
    return render(request, 'pages/blog_detail.html', context)

# Admin Approval System
@login_required
def admin_profile_approvals(request):
    """Admin view for profile approvals"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    pending_profiles = Profile.objects.filter(is_approved=False).select_related('user')
    context = {'pending_profiles': pending_profiles}
    return render(request, 'pages/admin_approvals.html', context)

@login_required
def admin_approve_profile(request, profile_id):
    """Approve a profile (admin only)"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    profile = get_object_or_404(Profile, id=profile_id)
    profile.is_approved = True
    profile.approved_at = timezone.now()
    profile.approved_by = request.user
    profile.save()
    
    # ✅ INTEGRATION: Send profile approved email
    try:
        login_url = request.build_absolute_uri(reverse('dashboard'))
        send_profile_approved_email(profile.user.email, profile.user.username, login_url)
    except Exception as e:
        print(f"DEBUG: Profile approved email failed: {e}")
        # Don't break the flow if email fails
    
    messages.success(request, f"Profile for {profile.user.username} has been approved.")
    return redirect('admin_profile_approvals')

@login_required
def admin_reject_profile(request, profile_id):
    """Reject a profile (admin only)"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    profile = get_object_or_404(Profile, id=profile_id)
    username = profile.user.username
    profile.delete()
    
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
            profile.save()
            
            # ✅ INTEGRATION: Send profile approved email
            try:
                login_url = request.build_absolute_uri(reverse('dashboard'))
                send_profile_approved_email(profile.user.email, profile.user.username, login_url)
            except Exception as e:
                print(f"DEBUG: Profile approved email failed: {e}")
                # Don't break the flow if email fails
            
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
# NEW ADMIN NOTIFICATION SYSTEM - FIXED VERSION
# ======================

@login_required
def admin_new_signups(request):
    """Admin view for ALL users (even incomplete profiles)"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    try:
        # Get all users with their profiles
        users = User.objects.all().select_related('profile').order_by('-date_joined')
        
        # Calculate statistics - FIXED QUERIES
        total_users = users.count()
        approved_count = users.filter(profile__is_approved=True).count()
        verified_count = users.filter(profile__email_verified=True).count()
        pending_count = users.filter(profile__is_approved=False).count()
        
        # Handle users without profiles
        users_without_profiles = users.filter(profile__isnull=True)
        incomplete_count = users_without_profiles.count()
        
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
            
            # ✅ NEW: Send email notification to user
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
            
            # Log the activity
            log_user_activity(
                request.user, 
                'admin_message_sent', 
                request, 
                admin_message,
                target_user_id=profile.user.id
            )
            
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
    """Handle email verification links"""
    try:
        profile = Profile.objects.get(
            email_verification_token=token,
            email_verification_sent_at__gte=timezone.now() - timedelta(hours=24)
        )
        
        if not profile.email_verified:
            profile.email_verified = True
            profile.save()
            
            messages.success(request, "✅ Email verified successfully! Your profile is now complete.")
        else:
            messages.info(request, "✅ Email already verified.")
            
    except Profile.DoesNotExist:
        messages.error(request, "❌ Invalid or expired verification link.")
    
    # Redirect to appropriate page
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

            deleted_count, _ = Block.objects.filter(
                blocker=request.user,
                blocked=target_user
            ).delete()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'User unblocked successfully'})
            return redirect('profile_detail', user_id=user_id)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

# HotDates - FIXED MISSING VIEWS
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
        print(f"DEBUG: Error in hotdates_new_count: {e}")
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
    
    return render(request, 'pages/hotdate_list.html', {
        'hot_dates': hot_dates,
        'viewed_hotdates': viewed_hotdates
    })

@login_required
def hotdate_create(request):
    """Display and handle Hot Date creation form"""
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
                host=request.user,  # Changed from user to host to match your model
                activity=activity,
                vibe=vibe,
                budget=budget,
                duration=duration,
                date_time=date_time,
                area=area,
                group_size=group_size
            )
            
            messages.success(request, "Hot Date created successfully!")
            return redirect('hotdate_list')
            
        except Exception as e:
            messages.error(request, f"Error creating Hot Date: {str(e)}")
            return render(request, 'pages/hotdate_create.html')
    
    return render(request, 'pages/hotdate_create.html')

@login_required
def hotdate_detail(request, hotdate_id):
    """Display Hot Date details"""
    hot_date = get_object_or_404(HotDate, id=hotdate_id)
    
    # Mark as viewed by current user
    HotDateView.objects.get_or_create(
        user=request.user,
        hot_date=hot_date
    )
    
    return render(request, 'pages/hotdate_detail.html', {
        'hot_date': hot_date
    })

# MISSING VIEWS - ADD THESE
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
            
            must_have_tags = request.POST.getlist('must_have_tags[]')
            profile.must_have_tags = ','.join(must_have_tags) if must_have_tags else ''
            
            profile.children = request.POST.get('children', '')
            profile.smoking = request.POST.get('smoking', '')
            profile.drinking = request.POST.get('drinking', '')
            profile.exercise = request.POST.get('exercise', '')
            profile.pets = request.POST.get('pets', '')
            profile.diet = request.POST.get('diet', '')
            
            # Preferences
            profile.preferred_age_min = request.POST.get('preferred_age_min', 18)
            profile.preferred_age_max = request.POST.get('preferred_age_max', 99)
            profile.preferred_intent = request.POST.get('preferred_intent', '')
            profile.preferred_distance = request.POST.get('preferred_distance', '')
            
            # Mark as submitted for approval (but not approved yet)
            profile.is_approved = False
            profile.save()
            
            # ✅ INTEGRATION: Send profile submitted email
            try:
                send_profile_submitted_email(request.user.email, request.user.username)
            except Exception as e:
                print(f"DEBUG: Profile submitted email failed: {e}")
                # Don't break the flow if email fails
            
            messages.success(request, 'Profile submitted for admin approval! You can now browse profiles in preview mode.')
            return redirect('preview_gate')
            
        except Exception as e:
            messages.error(request, f'Error creating profile: {str(e)}')
            print(f"DEBUG: Profile creation error: {e}")
    
    # GET request - show the form
    context = {
        'ages': range(18, 81),
    }
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
    
    # Get the target profile WITH IMAGES PREFETCHED
    profile = get_object_or_404(
        Profile.objects.prefetch_related('images'),
        user_id=user_id, 
        is_approved=True
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
def upload_profile_image_api(request):
    """API endpoint for uploading cropped profile images"""
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            photo_type = request.POST.get('photo_type', 'additional')
            is_profile = photo_type == 'profile'
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return JsonResponse({
                    'success': False, 
                    'error': 'Invalid file type. Please upload JPEG, PNG, GIF, or WebP.'
                }, status=400)
            
            # Validate file size (max 5MB)
            if image_file.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'error': 'File too large. Maximum size is 5MB.'
                }, status=400)
            
            # Get or create user profile
            profile, created = Profile.objects.get_or_create(user=request.user)
            
            # Create new ProfileImage
            profile_image = ProfileImage.objects.create(
                profile=profile,
                image=image_file,
                is_private=(photo_type == 'private'),
                is_primary=is_profile
            )
            
            # If this is a profile photo, ensure it's the only primary image
            if is_profile:
                ProfileImage.objects.filter(profile=profile, is_primary=True).exclude(id=profile_image.id).update(is_primary=False)
            
            return JsonResponse({
                'success': True, 
                'image_id': profile_image.id,
                'image_url': profile_image.image.url,
                'filename': image_file.name
            })
            
        except Exception as e:
            print(f"DEBUG: Error uploading image: {e}")
            return JsonResponse({
                'success': False, 
                'error': f'Upload failed: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False, 
        'error': 'No image file provided'
    }, status=400)

@login_required
@csrf_exempt
def delete_image_api(request, image_id):
    """API endpoint for deleting images"""
    try:
        image = ProfileImage.objects.get(id=image_id, profile__user=request.user)
        image.delete()
        return JsonResponse({'success': True, 'message': 'Image deleted successfully'})
    except ProfileImage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@csrf_exempt
def create_profile_api(request):
    """API endpoint for comprehensive profile creation"""
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
            
            must_have_tags = request.POST.getlist('must_have_tags') or request.POST.getlist('must_have_tags[]')
            profile.must_have_tags = ','.join(must_have_tags) if must_have_tags else ''
            
            # Lifestyle fields
            profile.children = request.POST.get('children', '')
            profile.smoking = request.POST.get('smoking', '')
            profile.drinking = request.POST.get('drinking', '')
            profile.exercise = request.POST.get('exercise', '')
            profile.pets = request.POST.get('pets', '')
            profile.diet = request.POST.get('diet', '')
            
            # Preferences
            profile.preferred_age_min = int(request.POST.get('preferred_age_min', 18))
            profile.preferred_age_max = int(request.POST.get('preferred_age_max', 99))
            profile.preferred_intent = request.POST.get('preferred_intent', '')
            profile.preferred_distance = request.POST.get('preferred_distance', '')
            
            # Handle profile photo
            profile_photo_id = request.POST.get('profile_photo_id')
            if profile_photo_id:
                try:
                    # Set this as primary photo
                    profile_image = ProfileImage.objects.get(id=profile_photo_id, profile=profile)
                    ProfileImage.objects.filter(profile=profile, is_primary=True).exclude(id=profile_image.id).update(is_primary=False)
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
            
            # ✅ ENHANCED: GENERATE VERIFICATION TOKEN
            profile.email_verification_token = secrets.token_urlsafe(32)
            profile.email_verification_sent_at = timezone.now()
            profile.save()
            
            # ✅ ENHANCED: Send profile submitted email
            try:
                send_profile_submitted_email(request.user.email, request.user.username)
            except Exception as e:
                print(f"DEBUG: Profile submitted email failed: {e}")
            
            # ✅ NEW: Send email verification to user
            try:
                verification_url = request.build_absolute_uri(
                    reverse('verify_email', kwargs={'token': profile.email_verification_token})
                )
                send_email_verification_email(request.user.email, request.user.username, verification_url)
            except Exception as e:
                print(f"DEBUG: Verification email failed: {e}")
            
            # ✅ NEW: Notify admins about new submission
            try:
                admin_emails = User.objects.filter(
                    is_staff=True, 
                    is_active=True
                ).values_list('email', flat=True)
                
                profile_url = request.build_absolute_uri(
                    reverse('admin_new_profiles')
                )
                
                for admin_email in admin_emails:
                    if admin_email:  # Ensure email is not empty
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
# ERROR HANDLING
# ======================

def handler404(request, exception):
    """Custom 404 error handler"""
    return render(request, 'pages/404.html', status=404)

def handler500(request):
    """Custom 500 error handler"""
    return render(request, 'pages/500.html', status=500)

# ======================
# MISSING HELPER FUNCTION
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
