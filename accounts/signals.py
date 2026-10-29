from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from matches.models import Match, MatchPlayer, PottingSequence

from .cache import LANDING_PAGE_CACHE_KEY
from .models import User


@receiver([post_save, post_delete], sender=User)
@receiver([post_save, post_delete], sender=Match)
@receiver([post_save, post_delete], sender=MatchPlayer)
@receiver([post_save, post_delete], sender=PottingSequence)
def invalidate_landing_page_cache(**kwargs):
    cache.delete(LANDING_PAGE_CACHE_KEY)
