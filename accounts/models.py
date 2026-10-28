from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model for the Snooker Century application."""

    is_admin = models.BooleanField(default=False)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)

    def __str__(self):
        return self.username

    # --- Convenience properties (no DB columns, so no migration needed) ---
    @property
    def is_site_admin(self):
        """True for portal admins and superusers."""
        return bool(self.is_admin or self.is_superuser)

    @property
    def display_name(self):
        return self.get_full_name().strip() or self.username

    @property
    def initials(self):
        parts = [p for p in (self.first_name, self.last_name) if p]
        if parts:
            return "".join(p[0] for p in parts[:2]).upper()
        return (self.username[:2] or "?").upper()
