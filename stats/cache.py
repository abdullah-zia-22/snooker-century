from django.core.cache import cache

from .models import PlayerStats

LEADERBOARD_CACHE_KEY = "stats:leaderboard:v1"
LEADERBOARD_CACHE_TIMEOUT = 300


def get_leaderboard_stats():
    stats = cache.get(LEADERBOARD_CACHE_KEY)
    if stats is not None:
        return stats

    from accounts.models import User

    players = User.objects.filter(is_active=True, is_superuser=False, is_admin=False)
    missing = players.filter(stats__isnull=True)
    PlayerStats.objects.bulk_create([PlayerStats(player=user) for user in missing])
    stats = list(
        PlayerStats.objects.select_related("player")
        .filter(player__in=players)
        .order_by("-wins", "-total_centuries", "-highest_break", "player__username")
    )
    cache.set(LEADERBOARD_CACHE_KEY, stats, LEADERBOARD_CACHE_TIMEOUT)
    return stats
