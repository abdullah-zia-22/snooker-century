from django.core.cache import cache
from django.db.models import Max, Q, Sum, Value
from django.db.models.functions import Coalesce

from matches.models import Match, MatchPlayer, PottingSequence

from .models import User

LANDING_PAGE_CACHE_KEY = "accounts:landing-page:v1"
LANDING_PAGE_CACHE_TIMEOUT = 60


def get_landing_page_data():
    data = cache.get(LANDING_PAGE_CACHE_KEY)
    if data is not None:
        return data

    live_match = Match.objects.filter(is_active=True).order_by("-date", "-id").first()
    live_players = []
    if live_match:
        players = (
            MatchPlayer.objects.filter(match=live_match)
            .select_related("player")
            .annotate(
                live_total=Coalesce(Sum("potting_sequences__potted_balls"), Value(0)),
                live_best=Coalesce(
                    Max(
                        "potting_sequences__potted_balls",
                        filter=Q(potting_sequences__potted_balls__gt=0),
                    ),
                    Value(0),
                ),
            )
        )
        players = sorted(players, key=lambda player: (-player.live_total, player.player.display_name.casefold()))
        live_players = [
            {
                "name": player.player.display_name,
                "live_total": player.live_total,
                "live_best": player.live_best,
            }
            for player in players
        ]

    data = {
        "player_count": User.objects.filter(
            is_active=True, is_staff=False, is_superuser=False, is_admin=False
        ).count(),
        "match_count": MatchPlayer.objects.values("match_id").distinct().count(),
        "century_count": PottingSequence.objects.filter(
            potted_balls__gte=100, match_player__match__is_active=False
        ).count(),
        "live_match": {"title": live_match.title} if live_match else None,
        "live_players": live_players,
    }
    cache.set(LANDING_PAGE_CACHE_KEY, data, LANDING_PAGE_CACHE_TIMEOUT)
    return data
