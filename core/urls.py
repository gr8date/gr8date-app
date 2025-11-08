# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os

# ADD THIS IMPORT - it should NOT cause circular imports now
from pages import views

from django.contrib.sitemaps.views import sitemap
from pages.sitemaps import BlogSitemap, StaticViewSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogSitemap,
}

# Hybrid media serving function
def hybrid_media_serve(request, path):
    """
    Serve media files from local storage if they exist locally,
    otherwise return 404 (S3 files will be handled by storage backend)
    """
    local_file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    # If file exists locally, serve it directly
    if os.path.exists(local_file_path):
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    
    # If file doesn't exist locally but we're using S3, let the template
    # handle the S3 URL (it will use the storage backend to generate URL)
    from django.http import Http404
    raise Http404("File not found")

urlpatterns = [
    # ========================
    # ALLAUTH URLs - MUST COME FIRST
    # ========================
    path("accounts/", include("allauth.urls")),
    path("accounts/login/", TemplateView.as_view(template_name="account/login.html"), name="login"),
    
    # ========================
    # REDIRECTS for Allauth (must come after allauth include)
    # ========================
    # ✅ REDIRECT: Allauth signup to styled join page
    path("accounts/signup/", RedirectView.as_view(url='/join/', permanent=False)),
    
    # ✅ NEW REDIRECT: Allauth password reset to styled password reset page
    path("accounts/password/reset/", RedirectView.as_view(url='/password-reset/', permanent=False)),
    
    # ========================
    # HOME PAGE
    # ========================
    path("", TemplateView.as_view(template_name="pages/index.html"), name="home"),
    
    # ========================
    # CUSTOM ADMIN URLS
    # ========================
    path("admin/approvals/", views.admin_profile_approvals, name="admin_profile_approvals"),
    path("admin/approve-profile/<int:profile_id>/", views.admin_approve_profile, name="admin_approve_profile"),
    path("admin/reject-profile/<int:profile_id>/", views.admin_reject_profile, name="admin_reject_profile"),
    path("admin/new-profiles/", views.admin_new_profile, name="admin_new_profiles"),
    path("admin/new-signups/", views.admin_new_signups, name="admin_new_signups"),
    path("admin/send-message/<int:profile_id>/", views.admin_send_message, name="admin_send_message"),
    
    # ========================
    # STANDARD DJANGO ADMIN
    # ========================
    path("admin/", admin.site.urls),
    
    # ========================
    # LEGACY REDIRECTS
    # ========================
    # Redirect old /login/ to new /accounts/login/
    path('login/', RedirectView.as_view(url='/accounts/login/', permanent=False)),
    
    # ========================
    # PAGES APP URLs
    # ========================
    path("", include("pages.urls")),
    
    # ========================
    # SITEMAP & SEO
    # ========================
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    
    # Robots.txt
    path(
        "robots.txt",
        TemplateView.as_view(
            template_name="robots.txt",
            content_type="text/plain"
        ),
        name="robots.txt"
    ),
    
    # Google Search Console Verification
    path(
        "google-site-verification.html",
        TemplateView.as_view(
            template_name="google-site-verification.html",
            content_type="text/html"
        ),
        name="google_verification"
    ),
]

# Static files for development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ✅ HYBRID MEDIA SERVING - WORKS IN BOTH DEV AND PRODUCTION
urlpatterns += [
    path('media/<path:path>', hybrid_media_serve, name='media_serve'),
]
