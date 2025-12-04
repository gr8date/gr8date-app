# views.py - COMPLETE WITH ALL WORKING VIEWS
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
import csv
from pathlib import Path

from django.contrib.auth.forms import PasswordResetForm
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMessage
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from .models import (
    BlogPost, UserLike, UserFavorite, UserBlock, DateEvent, DateView, 
    ProfileEditRequest, UserProfile, Conversation, Message, UserIdMapping,
    PrivateAccessRequest, PrivateImage, UserActivityLog  # Added UserActivityLog
)
from .db_helpers import get_profile_by_id, get_all_profile_ids, get_all_profiles
from django.utils.dateparse import parse_datetime

# ============================================================================
# ID MAPPING HELPER FUNCTIONS - ADDED FOR CSV IMPORT FIX
# ============================================================================

def get_django_user_id(external_profile_id):
    """Convert external profile_id to Django user.id"""
    try:
        # First try to get UserProfile with the external_profile_id
        profile = UserProfile.objects.get(id=external_profile_id)
        return profile.user.id
    except UserProfile.DoesNotExist:
        # If UserProfile doesn't exist, fall back to old logic
        return external_profile_id  # Because we made them match

def get_external_profile_id(django_user_id):
    """Convert Django user.id to external profile_id"""
    try:
        # Try to find a UserProfile associated with this user
        profile = UserProfile.objects.get(user_id=django_user_id)
        return profile.id
    except UserProfile.DoesNotExist:
        # If no UserProfile exists, fall back to old logic
        return django_user_id  # Because we made them match

# Elite profiles used on the Discover page (12 fixed IDs - UPDATED)
ELITE_MALE_IDS = [72, 3, 359, 191, 337, 66]    # Profile IDs for male elite users
ELITE_FEMALE_IDS = [16, 158, 181, 114, 11, 160]  # Profile IDs for female elite users


def _initialize_notifications(request):
    """Initialize empty notifications for new users"""
    if 'unviewed_likes' not in request.session:
        request.session['unviewed_likes'] = []
    
    if 'unviewed_mutual_matches' not in request.session:
        request.session['unviewed_mutual_matches'] = []
    
    # Initialize viewed items storage
    if 'viewed_likes' not in request.session:
        request.session['viewed_likes'] = []
    if 'viewed_mutual_matches' not in request.session:
        request.session['viewed_mutual_matches'] = []


# -------------------------
# BLOG
# -------------------------

def blog(request):
    blog_posts = BlogPost.objects.filter(
        is_published=True
    ).order_by('position', '-published_date')

    context = {
        'blog_posts': blog_posts,
        'page_title': 'Blog | Synergy Dating Insights & Relationship Advice',
        'meta_description': 'Explore Synergy dating blog for insights and relationship advice'
    }
    return render(request, 'website/blog.html', context)


def blog_post(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)

    context = {
        'post': post,
        'page_title': post.meta_title or post.title,
        'meta_description': post.meta_description or post.excerpt
    }
    return render(request, 'website/blog_post.html', context)


# -------------------------
# CORE PAGES
# -------------------------

def index(request):
    return render(request, 'website/index.html')


def login_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        from django.contrib.auth import authenticate, login
        
        username = request.POST.get('login')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Successfully signed in!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials. Please try again.')
    
    return render(request, 'website/loginpage.html')


def join(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        messages.success(request, 'Account created successfully! Please complete your profile.')
        return redirect('create_profile_step1')

    return render(request, 'website/join.html')


def help_center(request):
    return render(request, 'website/helpcenter.html')


def premium(request):
    return render(request, 'website/premium.html')


def terms(request):
    return render(request, 'website/terms.html')


def privacy(request):
    return render(request, 'website/privacy.html')


def safety_center(request):
    """CONSOLIDATED SAFETY CENTER - Replaces safetyguidelines.html and trustsafety.html"""
    return render(request, 'website/safetycenter.html')


def trust(request):
    """Redirect old trust-safety to new safety center"""
    return redirect('safety')


def success_stories(request):
    return render(request, 'website/successstories.html')


def about(request):
    return render(request, 'website/aboutus.html')


def contact(request):
    return render(request, 'website/contact.html')


# -------------------------
# DISCOVER (PUBLIC MARKETING)
# -------------------------

def discover(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Get elite profiles from database
    elite_women = []
    elite_men = []

    # Get actual elite users from database - USING UPDATED IDs
    for user_id in ELITE_FEMALE_IDS:
        profile = get_profile_by_id(user_id)
        if profile:
            elite_women.append({
                "user_id": user_id,
                "username": profile.get('username'),
                "profile_name": profile.get('profile_name'),
                "age": profile.get('age'),
                "location": profile.get('location'),
                "relationship_status": profile.get('relationship_status'),
                "profile_image": profile.get('profile_image'),
            })

    for user_id in ELITE_MALE_IDS:
        profile = get_profile_by_id(user_id)
        if profile:
            elite_men.append({
                "user_id": user_id,
                "username": profile.get('username'),
                "profile_name": profile.get('profile_name'),
                "age": profile.get('age'),
                "location": profile.get('location'),
                "relationship_status": profile.get('relationship_status'),
                "profile_image": profile.get('profile_image'),
            })

    context = {
        "elite_women": elite_women,
        "elite_men": elite_men,
    }
    return render(request, 'website/discoverelitemembers.html', context)


def events(request):
    return render(request, 'website/exclusiveevents.html')


def faq(request):
    return render(request, 'website/faq.html')


# -------------------------
# DASHBOARD - USES DATABASE
# -------------------------

@login_required
def dashboard(request):
    # Get current user's profile ID
    current_user_profile_id = None
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        current_user_profile_id = user_profile.id
    except UserProfile.DoesNotExist:
        # User doesn't have a profile yet, don't exclude anything
        current_user_profile_id = None
    
    # Get all profiles EXCEPT current user's
    all_profiles = get_all_profiles(exclude_id=current_user_profile_id)
    
    print(f"DEBUG: Getting profiles, excluding ID: {current_user_profile_id}")
    print(f"DEBUG: Got {len(all_profiles)} profiles")
    
    paginator = Paginator(all_profiles, 12)
    page = request.GET.get('page', 1)
    
    try:
        profiles = paginator.page(page)
    except PageNotAnInteger:
        profiles = paginator.page(1)
    except EmptyPage:
        profiles = paginator.page(paginator.num_pages)
    
    context = {
        'profiles': profiles,
        'page_obj': profiles,
    }
    return render(request, 'website/dashboard.html', context)

# -------------------------
# PROFILE CREATION FLOW
# -------------------------

@login_required
def create_profile_step1(request):
    if request.method == 'POST':
        messages.success(request, 'Basic info saved! Now tell us more about yourself.')
        return redirect('create_profile_step2')

    messages.success(request, 'Profile creation started! Complete your profile to get matches.')
    return render(request, 'website/create_profile_step1.html')


@login_required
def create_profile_step2(request):
    if request.method == 'POST':
        messages.success(request, 'Personal details saved! Almost done.')
        return redirect('create_profile_step3')

    return render(request, 'website/create_profile_step2.html')


@login_required
def create_profile_step3(request):
    if request.method == 'POST':
        messages.success(request, 'Preferences saved! Final step.')
        return redirect('create_profile_step4')

    return render(request, 'website/create_profile_step3.html')


@login_required
def create_profile_step4(request):
    if request.method == 'POST':
        messages.success(request, 'Profile completed successfully! Welcome to Synergy Dating.')
        return redirect('join_success')

    return render(request, 'website/create_profile_step4.html')


@login_required
def create_profile(request):
    return redirect('create_profile_step1')


@login_required
def join_success(request):
    messages.success(request, 'Welcome to Synergy Dating! Your profile is now complete and active.')
    return render(request, 'website/join_success.html')


# -------------------------
# PROFILE DETAIL - USES DATABASE
# -------------------------

def profile_detail(request, user_id: int):
    """
    LEGACY ENDPOINT - Redirects to the new profile system
    Maintains backward compatibility for old /profile/{id}/ URLs
    """
    # Simply redirect to the main entry point
    return redirect('profile_detail', profile_id=user_id)


def profile_detail_public(request, profile_id):
    """
    PUBLIC version - for non-logged-in users
    Shows join funnel (all buttons go to /join/)
    """
    # If user is logged in, redirect to member version
    if request.user.is_authenticated:
        return redirect('profile_detail_member', profile_id=profile_id)
    
    profile = get_profile_by_id(profile_id)
    if not profile:
        raise Http404("Profile not found")
    
    # Get next/previous IDs for navigation - use elite IDs for public view
    elite_ids_ordered = ELITE_FEMALE_IDS + ELITE_MALE_IDS
    
    try:
        current_index = elite_ids_ordered.index(profile_id)
    except ValueError:
        # If profile not in elite IDs, use all available IDs
        all_ids = get_all_profile_ids()
        current_index = next((i for i, pid in enumerate(all_ids) if pid == profile_id), -1)
        if current_index == -1:
            raise Http404("Profile not found")
        prev_id = all_ids[current_index - 1] if current_index > 0 else None
        next_id = all_ids[current_index + 1] if current_index < len(all_ids) - 1 else None
    else:
        # Profile is in elite IDs, use elite sequence
        prev_id = elite_ids_ordered[current_index - 1] if current_index > 0 else elite_ids_ordered[-1]
        next_id = elite_ids_ordered[current_index + 1] if current_index < len(elite_ids_ordered) - 1 else elite_ids_ordered[0]
    
    return render(request, 'website/profile_detail_public.html', {
        'profile': profile,
        'from_discover': True,
        'prev_id': prev_id,
        'next_id': next_id
    })

@login_required
def profile_detail_member(request, profile_id):
    """
    MEMBER version - for logged-in users  
    Shows real functionality (send message, like, block)
    """
    # Get the UserProfile using profile_id (which is the UserProfile.id, NOT User.id)
    user_profile = get_object_or_404(UserProfile, id=profile_id)
    
    # Get the associated User object
    user = user_profile.user
    
    # Get profile info from database
    profile = get_profile_by_id(profile_id)
    if not profile:
        raise Http404("Profile not found")
    
    # Get next/previous IDs for navigation
    all_ids = get_all_profile_ids()
    
    try:
        current_index = all_ids.index(profile_id)
    except ValueError:
        raise Http404("Profile not found")
    
    prev_id = all_ids[current_index - 1] if current_index > 0 else all_ids[-1]
    next_id = all_ids[current_index + 1] if current_index < len(all_ids) - 1 else all_ids[0]
    
    # Use the user's ID (user.id) for database queries instead of profile_id
    django_user_id = user.id
    
    # Check if user has liked/blocked this profile
    is_liked = UserLike.objects.filter(user=request.user, liked_user_id=django_user_id).exists()
    is_favorited = UserFavorite.objects.filter(user=request.user, favorite_user_id=django_user_id).exists()
    is_blocked = UserBlock.objects.filter(user=request.user, blocked_user_id=django_user_id).exists()
    
    # Check private access status
    has_private_access = False
    private_access_request = None
    
    if request.user.is_authenticated:
        has_private_access = PrivateAccessRequest.objects.filter(
            requester=request.user,
            target_user=user,  # Use the User object, not profile_id
            status='granted'
        ).exists()
        
        private_access_request = PrivateAccessRequest.objects.filter(
            requester=request.user,
            target_user=user  # Use the User object, not profile_id
        ).first()
    
    return render(request, 'website/profile_detail_member.html', {
        'profile': profile,
        'user_profile': user_profile,  # Add UserProfile object to context
        'profile_user': user,  # Add User object to context
        'prev_id': prev_id,
        'next_id': next_id,
        'is_liked': is_liked,
        'is_favorited': is_favorited,
        'is_blocked': is_blocked,
        'has_private_access': has_private_access,
        'private_access_request': private_access_request
    })

def profile_detail_redirect(request, profile_id):
    """
    MAIN ENTRY POINT - redirects to appropriate version
    """
    if request.user.is_authenticated:
        return redirect('profile_detail_member', profile_id=profile_id)
    else:
        return redirect('profile_detail_public', profile_id=profile_id)


# -------------------------
# MESSAGING SYSTEM - iPhone Style
# -------------------------

@login_required
def messages_list(request):
    """iPhone-style messages list with conversation previews"""
    # Get real conversations from database
    conversations = []
    
    # Get conversations where user is participant
    user_conversations = Conversation.objects.filter(participants=request.user).order_by('-updated_at')
    
    for conv in user_conversations:
        # Get the other participant
        other_participant = conv.participants.exclude(id=request.user.id).first()
        if other_participant:
            # Get the UserProfile for this user
            try:
                other_profile = UserProfile.objects.get(user=other_participant)
                external_profile_id = other_profile.id
                profile = get_profile_by_id(external_profile_id)
            except UserProfile.DoesNotExist:
                # Fallback to user info if no profile
                external_profile_id = other_participant.id
                profile = {
                    'profile_name': other_participant.username,
                    'profile_image': None
                }
            
            if profile:
                # Get last message
                last_message = conv.messages.order_by('-created_at').first()
                
                # Count unread messages
                unread_count = conv.messages.filter(
                    sender=other_participant,
                    is_read=False
                ).count()
                
                conversations.append({
                    'user_id': external_profile_id,  # Use external ID for URLs
                    'profile_name': profile.get('profile_name', other_participant.username),
                    'profile_image': profile.get('profile_image'),
                    'last_message': last_message.content if last_message else "No messages yet",
                    'timestamp': last_message.created_at if last_message else conv.updated_at,
                    'unread_count': unread_count,
                })
    
    context = {
        'conversations': conversations,
        'unread_count': sum(conv['unread_count'] for conv in conversations),
    }
    return render(request, 'website/messages_list.html', context)


@login_required
def message_detail(request, user_id: int):
    """Individual message conversation view"""
    # Convert external user_id to UserProfile, then get the User
    try:
        user_profile = UserProfile.objects.get(id=user_id)
        other_user = user_profile.user
    except UserProfile.DoesNotExist:
        # Fallback: try to get user directly
        other_user = get_object_or_404(get_user_model(), id=user_id)
    
    # Get or create conversation using Django ID
    conversation = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=other_user
    ).distinct().first()
    
    # If no conversation exists, create one
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other_user)
        conversation.save()
    
    # Get profile info from database using external ID
    profile = get_profile_by_id(user_id)
    if not profile:
        # Try to create a basic profile from user info
        profile = {
            'profile_name': other_user.username,
            'profile_image': None
        }
    
    # Get message history
    message_history = conversation.messages.order_by('created_at')
    
    # Mark messages from other user as read
    conversation.messages.filter(
        sender=other_user,
        is_read=False
    ).update(is_read=True)
    
    context = {
        'profile': profile,
        'messages': message_history,
        'other_user_id': user_id,  # Use external ID for templates
        'conversation_id': conversation.id,
    }
    return render(request, 'website/message_detail.html', context)


@login_required
def send_message(request, user_id: int):
    """Send a new message in a conversation"""
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        
        if message_text:
            # Convert external user_id to UserProfile, then get the User
            try:
                user_profile = UserProfile.objects.get(id=user_id)
                other_user = user_profile.user
            except UserProfile.DoesNotExist:
                # Fallback: try to get user directly
                other_user = get_object_or_404(get_user_model(), id=user_id)
            
            # Get conversation using Django ID
            conversation = Conversation.objects.filter(
                participants=request.user
            ).filter(
                participants=other_user
            ).distinct().first()
            
            if not conversation:
                conversation = Conversation.objects.create()
                conversation.participants.add(request.user, other_user)
                conversation.save()
            
            # Create message
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=message_text
            )
            
            # Update conversation timestamp
            conversation.updated_at = timezone.now()
            conversation.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Message sent successfully',
                'message_text': message_text,
                'timestamp': message.created_at.strftime('%I:%M %p'),
                'message_id': message.id
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


# -------------------------
# MATCHES & LIKES FUNCTIONALITY
# -------------------------

@login_required
def like_profile(request, user_id):
    """Like or unlike a profile - FIXED VERSION"""
    if request.method == 'POST':
        print(f"DEBUG: Like request for user_id: {user_id} from user: {request.user.id}")
        
        try:
            # Convert external profile_id to Django user
            target_user = None
            
            # Method 1: Try to get UserProfile
            try:
                user_profile = UserProfile.objects.get(id=user_id)
                target_user = user_profile.user
                print(f"DEBUG: Found via UserProfile - Profile ID: {user_id} -> User ID: {target_user.id}")
            except UserProfile.DoesNotExist:
                # Method 2: Try direct user lookup
                try:
                    target_user = get_user_model().objects.get(id=user_id)
                    print(f"DEBUG: Found via direct user lookup - User ID: {target_user.id}")
                except:
                    print(f"DEBUG: User not found with ID: {user_id}")
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'User not found'
                    }, status=404)
            
            # Check if like already exists
            like_exists = UserLike.objects.filter(
                user=request.user,
                liked_user_id=target_user.id
            ).exists()
            
            print(f"DEBUG: Like exists: {like_exists}")
            
            if not like_exists:
                # CREATE NEW LIKE
                like = UserLike.objects.create(
                    user=request.user,
                    liked_user_id=target_user.id
                )
                print(f"DEBUG: Created like ID: {like.id}")
                
                # Check if it's a mutual like
                mutual_like = UserLike.objects.filter(
                    user_id=target_user.id,
                    liked_user_id=request.user.id
                ).exists()
                
                print(f"DEBUG: Mutual like check: {mutual_like}")
                
                if mutual_like:
                    # Initialize session if needed
                    if 'unviewed_mutual_matches' not in request.session:
                        request.session['unviewed_mutual_matches'] = []
                    
                    # Add to mutual matches (use external ID for session)
                    if user_id not in request.session['unviewed_mutual_matches']:
                        request.session['unviewed_mutual_matches'].append(user_id)
                        request.session.modified = True
                        print(f"DEBUG: Added to mutual matches: {user_id}")
                
                # Also add to unviewed likes for the liked user's session
                # (This would typically be handled when they check their likes)
                
                return JsonResponse({
                    'status': 'success', 
                    'action': 'liked',
                    'liked': True,
                    'message': 'Profile liked successfully'
                })
                
            else:
                # REMOVE LIKE (unlike)
                deleted_count = UserLike.objects.filter(
                    user=request.user,
                    liked_user_id=target_user.id
                ).delete()[0]
                
                print(f"DEBUG: Deleted {deleted_count} like(s)")
                
                return JsonResponse({
                    'status': 'success', 
                    'action': 'unliked',
                    'liked': False,
                    'message': 'Like removed'
                })
                
        except Exception as e:
            print(f"DEBUG: Error in like_profile: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'status': 'error', 
                'message': f'Server error: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Invalid request method'
    }, status=400)


@login_required
def favorite_profile(request, user_id):
    """Favorite a profile - ALSO creates a like for matching"""
    if request.method == 'POST': 
        print(f"Favorite request for user_id: {user_id}")

        try:
            # Convert external user_id to Django user
            try:
                user_profile = UserProfile.objects.get(id=user_id)
                django_user_id = user_profile.user.id
            except UserProfile.DoesNotExist:
                # Fallback
                django_user_id = get_django_user_id(user_id)
            
            # Check if already favorited
            favorite_exists = UserFavorite.objects.filter(
                user=request.user,
                favorite_user_id=django_user_id
            ).exists()
        
            if not favorite_exists:
                # 1. Create Favorite
                favorite = UserFavorite.objects.create(
                    user=request.user,
                    favorite_user_id=django_user_id
                )
                print(f"Created favorite: {favorite.id}")
            
                # 2. ALSO Create a Like (for matching system)
                like_exists = UserLike.objects.filter(
                    user=request.user,
                    liked_user_id=django_user_id
                ).exists()
              
                if not like_exists:
                    like = UserLike.objects.create(
                        user=request.user,
                        liked_user_id=django_user_id 
                    )
                    print(f"Also created like: {like.id}")
    
                    # Check for mutual like
                    mutual_like = UserLike.objects.filter(
                        user_id=django_user_id,
                        liked_user_id=request.user.id
                    ).exists()

                    if mutual_like:
                        # Add to mutual matches
                        if 'unviewed_mutual_matches' not in request.session:
                            request.session['unviewed_mutual_matches'] = []
                
                        if user_id not in request.session['unviewed_mutual_matches']:
                            request.session['unviewed_mutual_matches'].append(user_id)
                            request.session.modified = True 
                            print(f"Added to mutual matches: {user_id}")
            
                return JsonResponse({
                    'status': 'success',
                    'action': 'favorited',
                    'liked': True  # Tell frontend this also counted as a like
                })
            
            else:
                # Remove favorite
                UserFavorite.objects.filter(
                    user=request.user,
                    favorite_user_id=django_user_id
                ).delete()
            
                # DO NOT remove the like - keep likes separate from favorites
                # Users may want to keep someone liked even if not favorited
              
                return JsonResponse({
                    'status': 'success',
                    'action': 'unfavorited',
                    'liked': True  # Like might still exist
                })   
                    
        except Exception as e:
            print(f"Error in favorite_profile: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def block_profile(request, user_id):
    """Block a user - prevent them from contacting you and hide your profile from them"""
    if request.method == 'POST':
        # Convert external user_id to UserProfile, then get the User
        try:
            user_profile = UserProfile.objects.get(id=user_id)
            django_user_id = user_profile.user.id
        except UserProfile.DoesNotExist:
            # Fallback: use direct mapping
            django_user_id = get_django_user_id(user_id)
        
        block, created = UserBlock.objects.get_or_create(
            user=request.user,
            blocked_user_id=django_user_id
        )
        
        if created:
            # Also remove any existing likes/favorites when blocking
            UserLike.objects.filter(user=request.user, liked_user_id=django_user_id).delete()
            UserFavorite.objects.filter(user=request.user, favorite_user_id=django_user_id).delete()
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Profile blocked successfully',
                'action': 'blocked'
            })
        else:
            return JsonResponse({
                'status': 'success',
                'message': 'Profile already blocked',
                'action': 'already_blocked'
            })
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def unblock_profile(request, user_id):
    """Unblock a user"""
    if request.method == 'POST':
        # Convert external user_id to UserProfile, then get the User
        try:
            user_profile = UserProfile.objects.get(id=user_id)
            django_user_id = user_profile.user.id
        except UserProfile.DoesNotExist:
            # Fallback: use direct mapping
            django_user_id = get_django_user_id(user_id)
        
        deleted_count, _ = UserBlock.objects.filter(
            user=request.user,
            blocked_user_id=django_user_id
        ).delete()
        
        if deleted_count > 0:
            return JsonResponse({
                'status': 'success',
                'message': 'Profile unblocked successfully',
                'action': 'unblocked'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Profile not found in blocked list'
            }, status=400)
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def get_user_likes_data(request):
    """Return real likes data from database"""
    try:
        liked_ids = list(UserLike.objects.filter(
            user=request.user
        ).values_list('liked_user_id', flat=True))
        
        # Convert Django IDs to external IDs
        liked_external_ids = []
        for django_id in liked_ids:
            try:
                profile = UserProfile.objects.get(user_id=django_id)
                liked_external_ids.append(profile.id)
            except UserProfile.DoesNotExist:
                # Fallback to old logic
                liked_external_ids.append(get_external_profile_id(django_id))
        
        # Get likes received (these are Django IDs from other users)
        likes_received_django_ids = list(UserLike.objects.filter(
            liked_user_id=request.user.id
        ).values_list('user_id', flat=True))
        
        # Convert to external IDs
        likes_received_ids = []
        for django_id in likes_received_django_ids:
            try:
                profile = UserProfile.objects.get(user_id=django_id)
                likes_received_ids.append(profile.id)
            except UserProfile.DoesNotExist:
                # Fallback to old logic
                likes_received_ids.append(get_external_profile_id(django_id))
        
        # Get mutual likes
        mutual_ids = []
        for liked_django_id in liked_ids:
            if UserLike.objects.filter(user_id=liked_django_id, liked_user_id=request.user.id).exists():
                try:
                    profile = UserProfile.objects.get(user_id=liked_django_id)
                    mutual_ids.append(profile.id)
                except UserProfile.DoesNotExist:
                    # Fallback to old logic
                    mutual_ids.append(get_external_profile_id(liked_django_id))
        
        return JsonResponse({
            'liked': liked_external_ids,
            'likes_received': likes_received_ids,
            'mutual': mutual_ids
        })
    except Exception as e:
        return JsonResponse({
            'liked': [],
            'likes_received': [],
            'mutual': []
        })

@login_required
def get_likes_counts(request):
    """Return counts for likes badge - FIXED VERSION"""
    print(f"DEBUG: Getting likes counts for user: {request.user.id}")
    
    # Initialize notifications
    _initialize_notifications(request)
    
    try:
        # Count of profiles user has liked
        liked_count = UserLike.objects.filter(user=request.user).count()
        print(f"DEBUG: User liked {liked_count} profiles")
        
        # Get ALL likes received by this user
        likes_received_count = UserLike.objects.filter(liked_user_id=request.user.id).count()
        print(f"DEBUG: User received {likes_received_count} likes")
        
        # Get mutual likes count
        liked_ids = list(UserLike.objects.filter(
            user=request.user
        ).values_list('liked_user_id', flat=True))
        
        mutual_count = 0
        mutual_details = []
        
        for liked_id in liked_ids:
            if UserLike.objects.filter(
                user_id=liked_id, 
                liked_user_id=request.user.id
            ).exists():
                mutual_count += 1
                mutual_details.append(liked_id)
        
        print(f"DEBUG: Mutual likes: {mutual_count}")
        print(f"DEBUG: Mutual user IDs: {mutual_details}")
        
        # Get session counts for unviewed (these use external IDs)
        unviewed_likes = request.session.get('unviewed_likes', [])
        unviewed_mutual = request.session.get('unviewed_mutual_matches', [])
        
        unviewed_likes_count = len(unviewed_likes)
        unviewed_mutual_count = len(unviewed_mutual)
        
        print(f"DEBUG: Unviewed likes: {unviewed_likes_count}")
        print(f"DEBUG: Unviewed mutual: {unviewed_mutual_count}")
        
        # Get blocked count
        blocked_count = UserBlock.objects.filter(user=request.user).count()
        
        # For badge: total unviewed notifications
        total_notifications = unviewed_likes_count + unviewed_mutual_count
        
        return JsonResponse({
            'liked': liked_count,
            'likes_received': likes_received_count,
            'mutual': mutual_count,
            'blocked': blocked_count,
            'unviewed_likes': unviewed_likes_count,
            'unviewed_mutual': unviewed_mutual_count,
            'total': total_notifications
        })
        
    except Exception as e:
        print(f"DEBUG: Error in get_likes_counts: {str(e)}")
        return JsonResponse({
            'liked': 0,
            'likes_received': 0,
            'mutual': 0,
            'blocked': 0,
            'unviewed_likes': 0,
            'unviewed_mutual': 0,
            'total': 0
        })


# NEW: Combined notification counts endpoint
@login_required
def notification_counts(request):
    """Return all notification counts in one call"""
    _initialize_notifications(request)
    
    # Messages count
    unread_messages_count = 0
    conversations = Conversation.objects.filter(participants=request.user)
    for conv in conversations:
        other_participant = conv.participants.exclude(id=request.user.id).first()
        if other_participant:
            unread_messages_count += conv.messages.filter(
                sender=other_participant,
                is_read=False
            ).count()
    
    # Likes count (unviewed from session)
    unviewed_likes_count = len(request.session.get('unviewed_likes', []))
    
    # Mutual matches count (unviewed from session)
    unviewed_mutual_count = len(request.session.get('unviewed_mutual_matches', []))
    
    # Dates count
    viewed_date_ids = DateView.objects.filter(user=request.user).values_list('date_event_id', flat=True)
    new_dates_count = DateEvent.objects.exclude(id__in=viewed_date_ids).exclude(
        is_cancelled=True
    ).filter(date_time__gt=timezone.now()).count()
    
    # Calculate totals
    likes_total = unviewed_likes_count + unviewed_mutual_count
    total_notifications = unread_messages_count + likes_total + new_dates_count
    
    return JsonResponse({
        'messages': unread_messages_count,
        'likes': likes_total,  # Combined likes and mutual matches
        'dates': new_dates_count,
        'total': total_notifications,
        'detailed': {
            'unread_messages': unread_messages_count,
            'unviewed_likes': unviewed_likes_count,
            'unviewed_mutual': unviewed_mutual_count,
            'new_dates': new_dates_count
        }
    })

@login_required
def mark_matches_viewed(request):
    """Mark matches as viewed"""
    if request.method == 'POST':
        request.session['matches_viewed'] = True
        request.session.modified = True
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Matches marked as viewed'
        })
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def mark_like_viewed(request, user_id):
    """TRIGGER: When user clicks 'View' on a like notification"""
    if request.method == 'POST':
        unviewed_likes = request.session.get('unviewed_likes', [])
        viewed_likes = request.session.get('viewed_likes', [])
        
        # Remove this user_id from unviewed likes and add to viewed
        if user_id in unviewed_likes:
            unviewed_likes.remove(user_id)
            if user_id not in viewed_likes:
                viewed_likes.append(user_id)
            
            request.session['unviewed_likes'] = unviewed_likes
            request.session['viewed_likes'] = viewed_likes
            request.session.modified = True
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Like from user {user_id} marked as viewed',
                'new_likes_count': len(unviewed_likes)
            })
        
        return JsonResponse({'status': 'error', 'message': 'Like not found'}, status=400)
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def mark_mutual_match_viewed(request, user_id):
    """TRIGGER: When user clicks 'View' on a mutual match notification"""
    if request.method == 'POST':
        unviewed_mutual = request.session.get('unviewed_mutual_matches', [])
        viewed_mutual = request.session.get('viewed_mutual_matches', [])
        
        # Remove this user_id from unviewed mutual matches and add to viewed
        if user_id in unviewed_mutual:
            unviewed_mutual.remove(user_id)
            if user_id not in viewed_mutual:
                viewed_mutual.append(user_id)
            
            request.session['unviewed_mutual_matches'] = unviewed_mutual
            request.session['viewed_mutual_matches'] = viewed_mutual
            request.session.modified = True
            
            return JsonResponse({
                'status': 'success',
                'message': f'Mutual match with user {user_id} marked as viewed', 
                'new_mutual_count': len(unviewed_mutual)
            })
        
        return JsonResponse({'status': 'error', 'message': 'Mutual match not found'}, status=400)
    
    return JsonResponse({'status': 'error'}, status=400)

# MESSAGING BADGE SYSTEM
@login_required
def messages_unread_count(request):
    """Return count of unread conversations"""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    
    # Get real unread count from database
    unread_count = 0
    conversations = Conversation.objects.filter(participants=request.user)
    
    for conv in conversations:
        other_participant = conv.participants.exclude(id=request.user.id).first()
        if other_participant:
            unread_count += conv.messages.filter(
                sender=other_participant,
                is_read=False
            ).count()
    
    return JsonResponse({'count': unread_count})

@login_required
def mark_conversation_viewed(request, user_id):
    """Mark a conversation as viewed (remove from unread)"""
    if request.method == 'POST':
        # Convert external user_id to UserProfile, then get the User
        try:
            user_profile = UserProfile.objects.get(id=user_id)
            other_user = user_profile.user
        except UserProfile.DoesNotExist:
            # Fallback: try to get user directly
            other_user = get_object_or_404(get_user_model(), id=user_id)
        
        # Mark messages from this user as read
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).distinct().first()
        
        if conversation:
            conversation.messages.filter(
                sender=other_user,
                is_read=False
            ).update(is_read=True)
            
            # Get new unread count
            unread_count = 0
            conversations = Conversation.objects.filter(participants=request.user)
            for conv in conversations:
                other_participant = conv.participants.exclude(id=request.user.id).first()
                if other_participant:
                    unread_count += conv.messages.filter(
                        sender=other_participant,
                        is_read=False
                    ).count()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Conversation with user {user_id} marked as read',
                'new_count': unread_count
            })
    
    return JsonResponse({'status': 'error'}, status=400)

# UPDATED MATCHES LIST - USES DATABASE
@login_required
def matches_list(request):
    """Show all matches (both viewed and unviewed) and blocked profiles"""
    # Initialize notifications
    _initialize_notifications(request)
    
    # Get user's likes data (these are Django IDs)
    liked_django_ids = list(UserLike.objects.filter(
        user=request.user
    ).values_list('liked_user_id', flat=True))
    
    # Convert to external IDs and get profiles
    liked_profiles = []
    for django_id in liked_django_ids:
        try:
            # Try to find UserProfile for this user
            user_profile = UserProfile.objects.get(user_id=django_id)
            external_id = user_profile.id
            profile = get_profile_by_id(external_id)
        except UserProfile.DoesNotExist:
            # Fallback to old logic
            external_id = get_external_profile_id(django_id)
            profile = get_profile_by_id(external_id)
        
        if profile:
            profile['user_id'] = external_id  # Use external ID for templates
            liked_profiles.append(profile)
    
    # Get ALL likes received (both viewed and unviewed) - these are external IDs
    unviewed_likes_ids = request.session.get('unviewed_likes', [])
    viewed_likes_ids = request.session.get('viewed_likes', [])
    all_likes_received_ids = unviewed_likes_ids + viewed_likes_ids
    
    likes_received_profiles = []
    for user_id in all_likes_received_ids:
        profile = get_profile_by_id(user_id)
        if profile:
            profile['user_id'] = user_id
            profile['is_new'] = user_id in unviewed_likes_ids
            likes_received_profiles.append(profile)
    
    # Get ALL mutual matches (both viewed and unviewed) - these are external IDs
    unviewed_mutual_ids = request.session.get('unviewed_mutual_matches', [])
    viewed_mutual_ids = request.session.get('viewed_mutual_matches', [])
    all_mutual_ids = unviewed_mutual_ids + viewed_mutual_ids
    
    mutual_profiles = []
    for user_id in all_mutual_ids:
        profile = get_profile_by_id(user_id)
        if profile:
            profile['user_id'] = user_id
            profile['is_new'] = user_id in unviewed_mutual_ids
            mutual_profiles.append(profile)
    
    # Get blocked profiles (these are Django IDs)
    blocked_django_ids = list(UserBlock.objects.filter(
        user=request.user
    ).values_list('blocked_user_id', flat=True))
    
    blocked_profiles = []
    for django_id in blocked_django_ids:
        try:
            # Try to find UserProfile for this user
            user_profile = UserProfile.objects.get(user_id=django_id)
            external_id = user_profile.id
            profile = get_profile_by_id(external_id)
        except UserProfile.DoesNotExist:
            # Fallback to old logic
            external_id = get_external_profile_id(django_id)
            profile = get_profile_by_id(external_id)
        
        if profile:
            profile['user_id'] = external_id  # Use external ID for templates
            blocked_profiles.append(profile)
    
    context = {
        'liked_profiles': liked_profiles,
        'likes_received_profiles': likes_received_profiles,
        'mutual_profiles': mutual_profiles,
        'blocked_profiles': blocked_profiles,
        'likes_received_count': len(unviewed_likes_ids),
        'mutual_count': len(unviewed_mutual_ids),
        'you_liked_count': len(liked_profiles),
        'blocked_count': len(blocked_profiles),
    }
    return render(request, 'website/matches_list.html', context)


# ============================================================================
# PROFILE EDIT SYSTEM - USES DATABASE
# ============================================================================

@login_required
def profile_edit(request):
    """Main profile edit page - Database version"""
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        # If no profile exists, create a default one
        user_profile = UserProfile.objects.create(
            user=request.user,
            profile_name=request.user.username,
            relationship_status='single',
            body_type='average',
            location='Unknown',
            story='Please update your profile information.',
            communication_style='Friendly',
            preferred_age_min=25,
            preferred_age_max=45,
            preferred_distance=50,
            is_complete=False,
            is_approved=False
        )
        messages.info(request, 'A default profile has been created for you. Please update your information.')
    
    # Check for pending edit requests
    pending_requests = ProfileEditRequest.objects.filter(
        user=request.user, 
        status='pending'
    ).count()
    
    # Get recent edit request history
    edit_history = ProfileEditRequest.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'user_profile': user_profile,
        'pending_requests': pending_requests,
        'edit_history': edit_history,
    }
    return render(request, 'website/profile_edit.html', context)

@login_required
@csrf_exempt
def profile_edit_request(request):
    """API endpoint to submit profile changes for approval"""
    if request.method == 'POST':
        try:
            # Get current profile
            current_profile = request.user.profile
            
            # Create new edit request
            edit_request = ProfileEditRequest(user=request.user)
            
            # Process form data
            data = request.POST
            
            # Update fields that are provided in the request
            for field in ['profile_name', 'date_of_birth', 'relationship_status', 
                         'body_type', 'location', 'story', 'communication_style',
                         'preferred_age_min', 'preferred_age_max', 'preferred_distance',
                         'height', 'gender', 'looking_for']:
                if field in data and data[field]:
                    setattr(edit_request, field, data[field])
            
            # Handle boolean fields
            if 'has_children' in data:
                edit_request.has_children = data['has_children'] == 'true'
            if 'is_smoker' in data:
                edit_request.is_smoker = data['is_smoker'] == 'true'
            
            # Handle children details
            if 'children_details' in data:
                edit_request.children_details = data['children_details']
            
            # Handle JSON fields
            json_fields = ['personality_traits', 'life_priorities', 'core_values',
                          'arrangement_preferences', 'lifestyle_interests',
                          'privacy_settings', 'notification_preferences']
            
            for json_field in json_fields:
                if json_field in data and data[json_field]:
                    try:
                        edit_request.__setattr__(json_field, json.loads(data[json_field]))
                    except json.JSONDecodeError:
                        # If it's not valid JSON, store as string
                        edit_request.__setattr__(json_field, data[json_field])
            
            # Handle file upload (profile photo)
            if 'profile_photo' in request.FILES:
                edit_request.profile_photo = request.FILES['profile_photo']
            
            # Save the edit request
            edit_request.save()
            
            messages.success(request, 'Your profile changes have been submitted for admin approval. You will be notified once they are reviewed.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Profile changes submitted for approval',
                    'request_id': edit_request.id
                })
            else:
                return redirect('profile_edit')
                
        except UserProfile.DoesNotExist:
            error_msg = 'User profile not found. Please complete your profile first.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
            else:
                messages.error(request, error_msg)
                return redirect('create_profile_step1')
                
        except Exception as e:
            error_msg = f'Error submitting profile changes: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
            else:
                messages.error(request, error_msg)
                return redirect('profile_edit')
    
    # GET request - show form
    return redirect('profile_edit')


# ============================================================================
# DATES - WORKING VERSION
# ============================================================================

@login_required
def dates_list(request):
    """Dates list page with real database data"""
    # Get all date events, ordered by date
    date_events = DateEvent.objects.all().order_by('date_time')
    
    # Get which dates the current user has viewed
    viewed_dates = list(DateView.objects.filter(
        user=request.user
    ).values_list('date_event_id', flat=True))
    
    context = {
        'date_events': date_events,
        'viewed_dates': viewed_dates,
    }
    return render(request, 'website/dates_list.html', context)

@login_required
def dates_create(request):
    """Create a new date event"""
    if request.method == 'POST':
        try:
            # Combine date and time
            date_str = request.POST.get('date')
            time_str = request.POST.get('time')
            
            if not date_str or not time_str:
                messages.error(request, 'Date and time are required')
                return render(request, 'website/dates_create.html')
                
            date_time_str = f"{date_str} {time_str}"
            date_time = parse_datetime(date_time_str)
            
            if not date_time:
                messages.error(request, 'Invalid date/time format')
                return render(request, 'website/dates_create.html')
            
            # Create the date event
            date_event = DateEvent(
                host=request.user,
                title=request.POST.get('title', 'New Date'),
                activity=request.POST.get('activity'),
                vibe=request.POST.get('vibe'),
                budget=request.POST.get('budget'),
                duration=request.POST.get('duration'),
                date_time=date_time,
                area=request.POST.get('area'),
                group_size=request.POST.get('group_size'),
                audience=request.POST.get('audience'),
            )
            date_event.save()
            
            messages.success(request, 'Date created successfully!')
            return redirect('dates_list')
            
        except Exception as e:
            messages.error(request, f'Error creating date: {str(e)}')
    
    # If GET request or error, show the form
    return render(request, 'website/dates_create.html')

@login_required
def mark_date_seen(request, dates_id):
    """Mark a date as seen by the current user"""
    if request.method == 'POST':
        try:
            date_event = DateEvent.objects.get(id=dates_id)
            DateView.objects.get_or_create(
                user=request.user,
                date_event=date_event
            )
            return JsonResponse({'success': True})
        except DateEvent.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Date not found'}, status=404)
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def cancel_date(request, dates_id):
    """Cancel a date (only host can do this)"""
    if request.method == 'POST':
        try:
            date_event = DateEvent.objects.get(id=dates_id)
            
            # Check if user is the host
            if date_event.host != request.user:
                return JsonResponse({
                    'success': False, 
                    'error': 'You can only cancel your own dates'
                }, status=403)
            
            date_event.is_cancelled = True
            date_event.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Date cancelled successfully'
            })
            
        except DateEvent.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Date not found'}, status=404)
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def dates_new_count(request):
    """Return count of new/unseen dates for badge"""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    
    # Count dates that user hasn't viewed yet
    viewed_date_ids = DateView.objects.filter(
        user=request.user
    ).values_list('date_event_id', flat=True)
    
    new_dates_count = DateEvent.objects.exclude(
        id__in=viewed_date_ids
    ).exclude(
        is_cancelled=True
    ).filter(
        date_time__gt=timezone.now()
    ).count()
    
    return JsonResponse({'count': new_dates_count})

# -------------------------
# PRIVATE ACCESS MANAGEMENT
# -------------------------

@login_required
def request_private_access(request, user_id):
    """Request access to view another user's private images"""
    try:
        # Convert external user_id to UserProfile, then get the User
        try:
            user_profile = UserProfile.objects.get(id=user_id)
            target_user = user_profile.user
        except UserProfile.DoesNotExist:
            # Fallback: try to get user directly
            target_user = get_user_model().objects.get(id=user_id)
        
        # Check if request already exists
        existing_request = PrivateAccessRequest.objects.filter(
            requester=request.user,
            target_user=target_user
        ).first()
        
        if existing_request:
            if existing_request.status == 'pending':
                return JsonResponse({
                    'status': 'info',
                    'message': 'Request already pending approval',
                    'request_id': existing_request.id,
                    'status': existing_request.status
                })
            elif existing_request.status == 'granted':
                return JsonResponse({
                    'status': 'info', 
                    'message': 'You already have access to private photos',
                    'request_id': existing_request.id,
                    'status': existing_request.status
                })
            elif existing_request.status in ['denied', 'revoked']:
                # Create new request
                message = request.POST.get('message', '') if request.method == 'POST' else ''
                new_request = PrivateAccessRequest.objects.create(
                    requester=request.user,
                    target_user=target_user,
                    message=message,
                    status='pending'
                )
                return JsonResponse({
                    'status': 'success',
                    'message': 'Access request sent successfully',
                    'request_id': new_request.id
                })
        else:
            # Create new request
            message = request.POST.get('message', '') if request.method == 'POST' else ''
            new_request = PrivateAccessRequest.objects.create(
                requester=request.user,
                target_user=target_user,
                message=message,
                status='pending'
            )
            return JsonResponse({
                'status': 'success',
                'message': 'Access request sent successfully',
                'request_id': new_request.id
            })
            
    except get_user_model().DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)

@login_required
def check_private_access_status(request, user_id):
    """Check if user has access to private images of another user"""
    try:
        # Convert external user_id to UserProfile, then get the User
        try:
            user_profile = UserProfile.objects.get(id=user_id)
            target_user = user_profile.user
        except UserProfile.DoesNotExist:
            # Fallback: try to get user directly
            target_user = get_user_model().objects.get(id=user_id)
        
        access_request = PrivateAccessRequest.objects.filter(
            requester=request.user,
            target_user=target_user
        ).first()
        
        if access_request:
            return JsonResponse({
                'status': 'success',
                'has_access': access_request.status == 'granted',
                'request_status': access_request.status,
                'request_id': access_request.id,
                'message': access_request.message,
                'requested_at': access_request.created_at.isoformat() if access_request.created_at else None
            })
        else:
            return JsonResponse({
                'status': 'success',
                'has_access': False,
                'request_status': 'none',
                'message': 'No access request found'
            })
            
    except get_user_model().DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)

@login_required
def grant_private_access(request, request_id):
    """Grant private access to a user (admin/target user only)"""
    try:
        access_request = PrivateAccessRequest.objects.get(id=request_id)
        
        # Check if current user is the target user or admin
        if request.user != access_request.target_user and not request.user.is_staff:
            return JsonResponse({
                'status': 'error',
                'message': 'You are not authorized to grant access'
            }, status=403)
        
        access_request.grant()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Private access granted successfully',
            'request_id': access_request.id,
            'status': access_request.status,
            'granted_at': access_request.granted_at.isoformat() if access_request.granted_at else None
        })
        
    except PrivateAccessRequest.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Access request not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)

@login_required
def revoke_private_access(request, user_id):
    """Revoke private access from a user"""
    try:
        # Convert external user_id to UserProfile, then get the User
        try:
            user_profile = UserProfile.objects.get(id=user_id)
            target_user = user_profile.user
        except UserProfile.DoesNotExist:
            # Fallback: try to get user directly
            target_user = get_user_model().objects.get(id=user_id)
        
        # Find the access request
        access_request = PrivateAccessRequest.objects.filter(
            requester=target_user,
            target_user=request.user
        ).first()
        
        if not access_request:
            return JsonResponse({
                'status': 'error',
                'message': 'No access request found'
            }, status=404)
        
        if access_request.status != 'granted':
            return JsonResponse({
                'status': 'error',
                'message': 'Access is not currently granted'
            }, status=400)
        
        # Revoke access
        reason = request.POST.get('reason', 'Access revoked by user')
        access_request.revoke(reason)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Private access revoked successfully',
            'request_id': access_request.id,
            'status': access_request.status,
            'revoked_at': access_request.revoked_at.isoformat() if access_request.revoked_at else None
        })
        
    except get_user_model().DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)

# -------------------------
# AJAX & AUTH UTILITIES
# -------------------------

def check_username(request):
    if request.method != "POST":
        return JsonResponse({"available": False}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        data = request.POST

    username = data.get("username", "").strip()
    if not username:
        return JsonResponse({"available": False}, status=200)

    User = get_user_model()
    exists = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({"available": not exists}, status=200)


def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            UserModel = get_user_model()
            associated_users = UserModel.objects.filter(email__iexact=email)

            if associated_users.exists():
                user = associated_users.first()
                subject = "Reset your Synergy password"
                context = {
                    "email": user.email,
                    "domain": request.get_host(),
                    "site_name": "Synergy",
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "user": user,
                    "token": default_token_generator.make_token(user),
                    "protocol": 'https' if request.is_secure() else 'http',
                }

                email_body = render_to_string("website/password_reset_email.html", context)
                email_msg = EmailMessage(
                    subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )
                email_msg.content_subtype = "html"
                email_msg.send()

            messages.success(
                request,
                "If an account with that email exists, a reset link has been sent."
            )
            return redirect('password_reset_sent')

    return render(request, "website/forgot_password.html")


def password_reset_sent(request):
    return render(request, "website/password_reset_sent.html")

# -------------------------
# LEGAL COMPLIANCE ENDPOINTS
# -------------------------

@login_required
def delete_message(request, message_id):
    """Soft delete a message for legal compliance"""
    try:
        message = Message.objects.get(id=message_id)
        
        # Check if user is authorized to delete
        if message.sender == request.user:
            message.is_deleted_for_sender = True
            message.deleted_by = request.user
            message.deleted_at = timezone.now()
            message.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Message deleted for you',
                'deleted_for': 'sender'
            })
        elif request.user in message.conversation.participants.all():
            message.is_deleted_for_receiver = True
            message.deleted_by = request.user
            message.deleted_at = timezone.now()
            message.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Message deleted for you',
                'deleted_for': 'receiver'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Not authorized to delete this message'
            }, status=403)
            
    except Message.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Message not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)

@login_required
def export_user_data(request, user_id=None):
    """Export user data for legal compliance (GDPR)"""
    try:
        # If user_id is provided and user is staff, export that user's data
        # Otherwise, export the current user's data
        if user_id and request.user.is_staff:
            user = get_user_model().objects.get(id=user_id)
        else:
            user = request.user
            
        # Collect user data
        user_data = {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'is_active': user.is_active,
            },
            'profile': None,
            'messages_sent': [],
            'messages_received': [],
            'likes_given': [],
            'likes_received': [],
            'private_access_requests': [],
            'activity_logs': []
        }
        
        # Get profile data
        try:
            profile = user.profile
            user_data['profile'] = {
                'profile_name': profile.profile_name,
                'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,
                'relationship_status': profile.relationship_status,
                'body_type': profile.body_type,
                'location': profile.location,
                'story': profile.story,
                'created_at': profile.created_at.isoformat(),
                'updated_at': profile.updated_at.isoformat(),
            }
        except UserProfile.DoesNotExist:
            pass
        
        # Get messages sent
        messages_sent = Message.objects.filter(sender=user).order_by('-created_at')[:100]
        for msg in messages_sent:
            user_data['messages_sent'].append({
                'id': msg.id,
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
                'is_read': msg.is_read,
                'conversation_id': msg.conversation.id
            })
        
        # Get messages received
        messages_received = Message.objects.filter(
            conversation__participants=user
        ).exclude(sender=user).order_by('-created_at')[:100]
        
        for msg in messages_received:
            user_data['messages_received'].append({
                'id': msg.id,
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
                'is_read': msg.is_read,
                'sender': msg.sender.username,
                'conversation_id': msg.conversation.id
            })
        
        # Get likes given
        likes_given = UserLike.objects.filter(user=user)
        for like in likes_given:
            user_data['likes_given'].append({
                'liked_user_id': like.liked_user_id,
                'created_at': like.created_at.isoformat()
            })
        
        # Get likes received
        likes_received = UserLike.objects.filter(liked_user_id=user.id)
        for like in likes_received:
            user_data['likes_received'].append({
                'user_id': like.user_id,
                'created_at': like.created_at.isoformat()
            })
        
        # Get private access requests
        access_requests = PrivateAccessRequest.objects.filter(
            requester=user
        ) | PrivateAccessRequest.objects.filter(
            target_user=user
        )
        
        for req in access_requests:
            user_data['private_access_requests'].append({
                'id': req.id,
                'requester': req.requester.username,
                'target_user': req.target_user.username,
                'status': req.status,
                'message': req.message,
                'created_at': req.created_at.isoformat(),
                'granted_at': req.granted_at.isoformat() if req.granted_at else None,
                'denied_at': req.denied_at.isoformat() if req.denied_at else None,
                'revoked_at': req.revoked_at.isoformat() if req.revoked_at else None
            })
        
        # Get activity logs
        activity_logs = UserActivityLog.objects.filter(user=user).order_by('-created_at')[:100]
        for log in activity_logs:
            user_data['activity_logs'].append({
                'id': log.id,
                'activity_type': log.activity_type,
                'target_user': log.target_user.username if log.target_user else None,
                'ip_address': log.ip_address,
                'created_at': log.created_at.isoformat(),
                'additional_data': log.additional_data
            })
        
        # Return as JSON
        response = JsonResponse(user_data, json_dumps_params={'indent': 2})
        response['Content-Disposition'] = f'attachment; filename="user_data_{user.id}_{timezone.now().date()}.json"'
        return response
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error exporting data: {str(e)}'
        }, status=500)
