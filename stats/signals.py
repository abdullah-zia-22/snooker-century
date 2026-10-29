from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from accounts.models import User

from .cache import LEADERBOARD_CACHE_KEY
from .models import PlayerStats


@receiver([post_save, post_delete], sender=PlayerStats)
@receiver([post_save, post_delete], sender=User)
def invalidate_leaderboard_cache(**kwargs):
    cache.delete(LEADERBOARD_CACHE_KEY)
