"""Business logic for matches, kept out of the views so it can be tested directly."""
from django.db import transaction
from django.db.models import Max, Sum

from stats.models import PlayerStats, PlayerVsPlayerStats

from .models import MatchPlayer, PottingSequence


def recalculate_match_player(mp):
    """Recompute and persist a player's total score and highest break from their sequences."""
    agg = PottingSequence.objects.filter(match_player=mp).aggregate(total=Sum("potted_balls"), best=Max("potted_balls"))
    mp.total_score = agg["total"] or 0
    mp.highest_break = max(agg["best"] or 0, 0)
    mp.save(update_fields=["total_score", "highest_break"])
    return mp


def add_sequence(match, player_id, potted_balls):
    """Append a sequence for a player and keep their running totals correct."""
    with transaction.atomic():
        mp = MatchPlayer.objects.select_for_update().get(match=match, player_id=player_id)
        last = PottingSequence.objects.filter(match_player=mp).aggregate(n=Max("sequence_number"))["n"] or 0
        sequence = PottingSequence.objects.create(match_player=mp, potted_balls=potted_balls, sequence_number=last + 1)
        recalculate_match_player(mp)
    return mp, sequence


def undo_last_sequence(match):
    """Delete the most recent entry in the match. Returns the removed entry or None."""
    with transaction.atomic():
        last = (
            PottingSequence.objects.filter(match_player__match=match)
            .select_related("match_player__player")
            .order_by("-id")
            .first()
        )
        if not last:
            return None
        mp = last.match_player
        last.delete()
        recalculate_match_player(mp)
    return last


def finish_match(match):
    """Close the match, decide the winner (a tie is a draw) and refresh all affected stats.

    Returns the winning MatchPlayer, or None for a draw.
    """
    with transaction.atomic():
        players = list(MatchPlayer.objects.select_for_update().filter(match=match).select_related("player"))
        for mp in players:
            recalculate_match_player(mp)

        top = max((mp.total_score for mp in players), default=0)
        leaders = [mp for mp in players if mp.total_score == top]
        winner = leaders[0] if len(leaders) == 1 else None

        for mp in players:
            mp.is_winner = mp is winner
        MatchPlayer.objects.bulk_update(players, ["is_winner"])

        match.is_active = False
        match.save(update_fields=["is_active"])

        for mp in players:
            stats, _ = PlayerStats.objects.get_or_create(player=mp.player)
            stats.update_stats()
        for i, first in enumerate(players):
            for second in players[i + 1:]:
                PlayerVsPlayerStats.get_for(first.player, second.player).update_stats()
    return winner


def result_for(entry):
    """'live' | 'won' | 'lost' | 'draw' for a MatchPlayer (uses prefetched players when available)."""
    match = entry.match
    if match.is_active:
        return "live"
    if entry.is_winner:
        return "won"
    if any(p.is_winner for p in match.players.all()):
        return "lost"
    return "draw"
