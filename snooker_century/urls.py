from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from accounts import views as account_views

urlpatterns = [
    path("django-admin/", admin.site.urls),  # Django's built-in admin (not the primary portal)
    re_path(
        r"^media/profile_pics/(?P<filename>[^/]+)$",
        account_views.serve_profile_picture,
        name="profile_picture",
    ),
    path("", include("accounts.urls")),
    path("matches/", include("matches.urls")),
    path("stats/", include("stats.urls")),
]

# Serve uploaded media only in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
