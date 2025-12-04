from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.views.static import serve

urlpatterns = [
    # Your Synergy front-end
    path('', include('website.urls')),

    # Django admin
    path('admin/', admin.site.urls),

    # django-allauth: login/logout/signup/email/social
    path('accounts/', include('allauth.urls')),
]

# DEVELOPMENT ONLY - Manual static and media file serving
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {
            'document_root': settings.BASE_DIR / 'static',
        }),
        re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]

