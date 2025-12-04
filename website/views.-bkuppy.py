from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import get_user_model
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

from .models import BlogPost

# Path to the master CSV that drives profile data
MASTER_CSV_PATH = Path(settings.BASE_DIR) / "data" / "Master_user_sheet.csv"

# Elite profiles used on the Discover page (12 fixed IDs)
ELITE_MALE_IDS = [906, 932, 981, 806, 718, 627]
# NOTE: 153 replaced with 911 as per your instruction
ELITE_FEMALE_IDS = [640, 885, 925, 889, 635, 911]


def _read_master_csv():
    """Load all rows from the master CSV as a list of dicts."""
    rows = []
    try:
        with MASTER_CSV_PATH.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except FileNotFoundError:
        # In dev, fail silently so templates can still render
        return []
    return rows


def get_profile_by_id(user_id: int):
    """Return a single profile dict from the CSV by numeric user_id, or None."""
    rows = _read_master_csv()
    target = str(user_id)
    for row in rows:
        if str(row.get("user_id")) == target:
            return row
    return None


# -------------------------
# BLOG
# -------------------------

def blog(request):
    # Get published blog posts, ordered by position and publish date
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
    # Get individual blog post
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)

    # Set dynamic meta tags for SEO
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
    """
    Custom-styled login page.

    Right now this view does NOT perform real authentication –
    it just shows the login template and, on POST, pretends success
    and redirects to the dashboard.

    Later, we can wire this to django-allauth or Django auth to
    do real login while keeping this template.
    """
    if request.method == 'POST':
        # Placeholder: we are not authenticating yet
        login_value = request.POST.get('login')  # email or username
        password = request.POST.get('password')

        # For now, just redirect to dashboard
        messages.success(request, 'Successfully signed in!')
        return redirect('dashboard')

    return render(request, 'website/loginpage.html')


def join(request):
    """
    Custom join page.

    Right now this view does NOT create a real user account – it just
    simulates success and sends the user into the profile creation flow.

    The form collects email + password (no name/location), and later we
    will hook this into django-allauth so that:
      - a real User is created,
      - Brevo sends verification,
      - user is logged in and redirected to Step 1.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # For now, just redirect to create profile
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


def safety(request):
    return render(request, 'website/safetyguidelines.html')


def trust(request):
    return render(request, 'website/trustsafety.html')


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
    """
    Public 'Discover' marketing page showing ONLY the 12 fixed elite profiles.

    - If NOT logged in: show the 12 elite profiles (from CSV) using your
      luxury Discover design.
    - If logged in: redirect to dashboard (they shouldn't browse Discover).
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    rows = _read_master_csv()

    # Build a lookup of elite rows by user_id
    elite_lookup = {}
    for row in rows:
        try:
            uid_int = int(row.get("user_id"))
        except (TypeError, ValueError):
            continue
        if uid_int in ELITE_FEMALE_IDS or uid_int in ELITE_MALE_IDS:
            elite_lookup[uid_int] = row

    elite_women = []
    elite_men = []

    # Helper to normalise age to int
    def _normalise_age(raw):
        if not raw:
            return None
        try:
            return int(float(raw))
        except (ValueError, TypeError):
            return None

    # Preserve the order you specified in the constants
    for uid in ELITE_FEMALE_IDS:
        row = elite_lookup.get(uid)
        if not row:
            continue
        elite_women.append({
            "user_id": uid,
            "username": row.get("username"),
            "profile_name": row.get("profile_name"),
            "age": _normalise_age(row.get("age")),
            "location": row.get("location"),
            "relationship_status": row.get("relationship_status"),
            "profile_image": row.get("profile_image"),
        })

    for uid in ELITE_MALE_IDS:
        row = elite_lookup.get(uid)
        if not row:
            continue
        elite_men.append({
            "user_id": uid,
            "username": row.get("username"),
            "profile_name": row.get("profile_name"),
            "age": _normalise_age(row.get("age")),
            "location": row.get("location"),
            "relationship_status": row.get("relationship_status"),
            "profile_image": row.get("profile_image"),
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
# DASHBOARD
# -------------------------

def dashboard(request):
    """
    Main logged-in dashboard.

    For now, just renders the dashboard template. Later, this will
    paginate profiles (12 per page), but Prev/Next on the profile
    detail page will be independent and use the global ordering.
    """
    return render(request, 'website/dashboard.html')


# -------------------------
# PROFILE CREATION FLOW
# -------------------------

def create_profile_step1(request):
    if request.method == 'POST':
        # Later: process and save Step 1 fields into UserProfile
        messages.success(request, 'Basic info saved! Now tell us more about yourself.')
        return redirect('create_profile_step2')

    # GET request - show the form
    messages.success(request, 'Profile creation started! Complete your profile to get matches.')
    return render(request, 'website/create_profile_step1.html')


def create_profile_step2(request):
    if request.method == 'POST':
        # Later: process and save Step 2
        messages.success(request, 'Personal details saved! Almost done.')
        return redirect('create_profile_step3')

    return render(request, 'website/create_profile_step2.html')


def create_profile_step3(request):
    if request.method == 'POST':
        # Later: process and save Step 3
        messages.success(request, 'Preferences saved! Final step.')
        return redirect('create_profile_step4')

    return render(request, 'website/create_profile_step3.html')


def create_profile_step4(request):
    if request.method == 'POST':
        # Later: process and save Step 4 and mark profile as complete
        messages.success(request, 'Profile completed successfully! Welcome to Synergy Dating.')
        return redirect('join_success')

    return render(request, 'website/create_profile_step4.html')


def create_profile(request):
    # Main profile creation entry point
    return redirect('create_profile_step1')


def join_success(request):
    # Show success page after profile completion
    messages.success(request, 'Welcome to Synergy Dating! Your profile is now complete and active.')
    return render(request, 'website/join_success.html')


# -------------------------
# PROFILE DETAIL (PUBLIC + MEMBER MODES)
# -------------------------

def profile_detail(request, user_id: int):
    """
    Profile preview/detail page driven from the master CSV.

    MODES:

    1) GUEST DISCOVER PREVIEW (marketing mode)
       - Not authenticated AND ?from=discover
       - Only allow the 12 fixed elite IDs
       - Prev/Next cycles within those 12
       - Template JS gates clicks → Join page

    2) MEMBER MODE (full site use via dashboard)
       - Authenticated user (regardless of ?from)
       - Allow ANY profile from CSV
       - Prev/Next cycles across ALL profiles (ignores pagination)
       - No join gating
    """
    profile = get_profile_by_id(user_id)
    if not profile:
        from django.http import Http404
        raise Http404("Profile not found")

    # Normalise age here so templates get a clean int (no .0)
    raw_age = profile.get("age")
    try:
        profile["age"] = int(float(raw_age)) if raw_age else None
    except (ValueError, TypeError):
        profile["age"] = None

    # Normalize ID and elite set
    try:
        uid_int = int(user_id)
    except (TypeError, ValueError):
        from django.http import Http404
        raise Http404("Invalid profile id")

    elite_ids_ordered = ELITE_FEMALE_IDS + ELITE_MALE_IDS
    came_from_discover = (request.GET.get("from") == "discover")

    # Decide mode
    if request.user.is_authenticated:
        # MEMBER MODE – full access, regardless of ?from
        all_rows = _read_master_csv()
        all_ids = []
        for row in all_rows:
            try:
                all_ids.append(int(row.get("user_id")))
            except (TypeError, ValueError):
                continue
        all_ids = sorted(set(all_ids))

        if uid_int not in all_ids:
            from django.http import Http404
            raise Http404("Profile not listed")
        guest_from_discover = False  # don't gate members
    else:
        # GUEST MODE
        if uid_int not in elite_ids_ordered:
            # Guests only see the 12 Discover profiles; bounce anywhere else
            return redirect('discover')

        # Prev/Next limited to elite set
        all_ids = elite_ids_ordered
        guest_from_discover = came_from_discover

    # Compute Prev/Next within the chosen ID list
    try:
        current_index = all_ids.index(uid_int)
    except ValueError:
        from django.http import Http404
        raise Http404("Profile not in active sequence")

    prev_id = all_ids[current_index - 1] if current_index > 0 else None
    next_id = all_ids[current_index + 1] if current_index < len(all_ids) - 1 else None

    # Choose a display name
    display_name = (
        profile.get("profile_name")
        or profile.get("username")
        or "Member"
    )

    context = {
        "profile": profile,
        "username": display_name,
        "prev_id": prev_id,
        "next_id": next_id,
        "is_elite": uid_int in elite_ids_ordered,
        # Only true for guests who actually came from Discover
        "from_discover": guest_from_discover,
    }
    return render(request, 'website/profile_detail.html', context)


# -------------------------
# AJAX & AUTH UTILITIES
# -------------------------

def check_username(request):
    """
    AJAX endpoint used by Step 1 to ensure usernames are unique.
    Checks against the auth User model.
    """
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
    """
    Custom 'Forgot Password' page.
    Uses Django's password reset token system but keeps your Synergy layout.

    Flow:
      - User enters email on your custom forgot_password page.
      - We look up the User by that email.
      - If found, send them a password reset email using Django's token system.
      - Always show the same success message whether user exists or not
        (for privacy).
    """
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]

            # Find users linked to that email (usually 0 or 1)
            UserModel = get_user_model()
            associated_users = UserModel.objects.filter(email__iexact=email)

            if associated_users.exists():
                # Use the first matching user
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

            # Always redirect, even if no user found – for privacy
            messages.success(
                request,
                "If an account with that email exists, a reset link has been sent."
            )
            return redirect('password_reset_sent')

    # GET or invalid POST – just show the form template
    return render(request, "website/forgot_password.html")


def password_reset_sent(request):
    """
    Simple confirmation page after requesting a password reset.
    """
    return render(request, "website/password_reset_sent.html")

