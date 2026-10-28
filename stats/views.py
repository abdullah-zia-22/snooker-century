from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from matches.models import Match, MatchPlayer
from matches.services import result_for

from .models import PlayerStats, PlayerVsPlayerStats


@login_required
def player_stats(request, username=None):
    """A player's statistics (defaults to the signed-in user)."""
    player = get_object_or_404(User, username=username) if username else request.user

    stats, created = PlayerStats.objects.get_or_create(player=player)
    if created or request.GET.get("refresh_stats"):
        stats.update_stats()

    entries = (
        MatchPlayer.objects.filter(player=player)
        .select_related("match")
        .prefetch_related("match__players")
        .order_by("-match__date")[:10]
    )
    recent_matches = [{"entry": e, "match": e.match, "result": result_for(e)} for e in entries]

    head_to_head = (
        PlayerVsPlayerStats.objects.filter(Q(player1=player) | Q(player2=player))
        .filter(total_matches__gt=0)
        .select_related("player1", "player2")
    )
    rivalries = []
    for record in head_to_head:
        mine, theirs, opponent = (
            (record.player1_wins, record.player2_wins, record.player2)
            if record.player1_id == player.id
            else (record.player2_wins, record.player1_wins, record.player1)
        )
        rivalries.append({"record": record, "opponent": opponent, "mine": mine, "theirs": theirs})

    context = {
        "player": player,
        "stats": stats,
        "is_self": player.id == request.user.id,
        "recent_matches": recent_matches,
        "rivalries": rivalries,
    }
    return render(request, "player_stats.html", context)


@login_required
def player_vs_player(request, username1, username2):
    """Head-to-head record between two players."""
    player1 = get_object_or_404(User, username=username1)
    player2 = get_object_or_404(User, username=username2)
    if player1 == player2:
        return redirect("player_stats", username=player1.username)

    stats = PlayerVsPlayerStats.get_for(player1, player2)
    stats.update_stats()  # cheap, and avoids showing stale numbers

    # Present the pair in the order the URL asked for.
    if stats.player1_id == player1.id:
        wins1, wins2 = stats.player1_wins, stats.player2_wins
    else:
        wins1, wins2 = stats.player2_wins, stats.player1_wins

    matches = (
        Match.objects.filter(players__player=player1)
        .filter(players__player=player2)
        .distinct()
        .order_by("-date")
        .prefetch_related("players__player")
    )
    rows = []
    for match in matches:
        participants = list(match.players.all())
        winner = next((p.player for p in participants if p.is_winner), None)
        can_open = any(p.player_id == request.user.id for p in participants)
        rows.append({"match": match, "winner": winner, "can_open": can_open})

    total = stats.total_matches or 0
    context = {
        "player1": player1,
        "player2": player2,
        "stats": stats,
        "wins1": wins1,
        "wins2": wins2,
        "draws": stats.draws,
        "pct1": round(100 * wins1 / total) if total else 0,
        "pct2": round(100 * wins2 / total) if total else 0,
        "rows": rows,
    }
    return render(request, "player_vs_player.html", context)


@login_required
def leaderboard(request):
    """Ranking of all active, non-admin players."""
    players = User.objects.filter(is_active=True, is_superuser=False, is_admin=False)

    # Make sure everyone has a stats row so new players appear on the board straight away.
    missing = players.filter(stats__isnull=True)
    PlayerStats.objects.bulk_create([PlayerStats(player=u) for u in missing])

    stats = (
        PlayerStats.objects.select_related("player")
        .filter(player__in=players)
        .order_by("-wins", "-total_centuries", "-highest_break", "player__username")
    )
    return render(request, "leaderboard.html", {"stats": list(stats)})
