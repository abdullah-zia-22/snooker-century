from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MatchForm, PottingSequenceForm
from .models import Match, MatchPlayer, PottingSequence
from .services import add_sequence, finish_match, result_for, undo_last_sequence


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


@login_required
def match_list(request):
    """Matches the current user takes part in, newest first."""
    status = request.GET.get("status", "")
    entries = (
        MatchPlayer.objects.filter(player=request.user)
        .select_related("match__created_by")
        .prefetch_related("match__players__player")
        .order_by("-match__date")
    )
    if status == "live":
        entries = entries.filter(match__is_active=True)
    elif status == "finished":
        entries = entries.filter(match__is_active=False)

    rows = []
    for entry in entries:
        others = [p.player for p in entry.match.players.all() if p.player_id != request.user.id]
        rows.append({"match": entry.match, "result": result_for(entry), "others": others})
    return render(request, "match_list.html", {"rows": rows, "status": status})


@login_required
def match_create(request):
    if request.method == "POST":
        form = MatchForm(request.POST, user=request.user)
        if form.is_valid():
            match = form.save(commit=False)
            match.created_by = request.user
            match.save()

            players = list(form.cleaned_data["players"])
            if request.user not in players:
                players.append(request.user)
            MatchPlayer.objects.bulk_create([MatchPlayer(match=match, player=p) for p in players])

            messages.success(request, f"Match '{match.title}' created. Good luck!")
            return redirect("match_detail", match_id=match.id)
        messages.error(request, "Please fix the highlighted fields below.")
    else:
        form = MatchForm(user=request.user)
    return render(request, "match_form.html", {"form": form})


def _scoreboard(match):
    """Players with their sequences and live totals (computed from the sequences themselves)."""
    sequences = Prefetch("potting_sequences", queryset=PottingSequence.objects.order_by("sequence_number"))
    players = list(match.players.select_related("player").prefetch_related(sequences))
    for mp in players:
        values = [s.potted_balls for s in mp.potting_sequences.all()]
        mp.sequences = list(mp.potting_sequences.all())
        mp.live_total = sum(values)
        mp.live_best = max([v for v in values if v > 0], default=0)
        mp.century_count = sum(1 for v in values if v >= 100)
    players.sort(key=lambda mp: (-mp.live_total, mp.player.display_name.lower()))
    return players


@login_required
def match_detail(request, match_id):
    match = get_object_or_404(Match.objects.select_related("created_by"), id=match_id)

    if not MatchPlayer.objects.filter(match=match, player=request.user).exists():
        messages.error(request, "You are not a participant in this match.")
        return redirect("match_list")

    is_creator = match.created_by_id == request.user.id

    if request.method == "POST":
        error = None
        if not is_creator:
            error = "Only the match creator can record scores."
        elif not match.is_active:
            error = "This match has finished, so scores can't be changed."

        form = PottingSequenceForm(request.POST)
        if not error and form.is_valid():
            player_id = form.cleaned_data["player_id"]
            if not MatchPlayer.objects.filter(match=match, player_id=player_id).exists():
                error = "That player isn't part of this match."
            else:
                mp, sequence = add_sequence(match, player_id, form.cleaned_data["potted_balls"])
                if _is_ajax(request):
                    return JsonResponse(
                        {
                            "success": True,
                            "player": mp.player.username,
                            "potted_balls": sequence.potted_balls,
                            "sequence_number": sequence.sequence_number,
                            "total_score": mp.total_score,
                        }
                    )
                messages.success(request, f"Added {sequence.potted_balls} for {mp.player.display_name}.")
                return redirect("match_detail", match_id=match.id)
        elif not error:
            error = " ".join(" ".join(errs) for errs in form.errors.values()) or "Invalid entry."

        if _is_ajax(request):
            return JsonResponse({"success": False, "error": error}, status=400)
        messages.error(request, error)
        return redirect("match_detail", match_id=match.id)

    players = _scoreboard(match)
    winner = next((mp for mp in players if mp.is_winner), None)
    any_scores = any(mp.sequences for mp in players)
    top = players[0].live_total if players else 0
    leaders = [mp for mp in players if mp.live_total == top]
    leader_id = leaders[0].id if (match.is_active and any_scores and len(leaders) == 1) else None
    last_entry = (
        PottingSequence.objects.filter(match_player__match=match).select_related("match_player__player").order_by("-id").first()
    )

    context = {
        "match": match,
        "match_players": players,
        "winner": winner,
        "is_draw": (not match.is_active) and winner is None,
        "leader_id": leader_id,
        "is_creator": is_creator,
        "last_entry": last_entry,
        "form": PottingSequenceForm(),
    }
    return render(request, "match_detail.html", context)


@login_required
@require_POST
def match_undo(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    if match.created_by_id != request.user.id:
        messages.error(request, "Only the match creator can undo entries.")
    elif not match.is_active:
        messages.error(request, "This match has finished, so scores can't be changed.")
    else:
        removed = undo_last_sequence(match)
        if removed:
            messages.success(request, f"Removed {removed.potted_balls} from {removed.match_player.player.display_name}.")
        else:
            messages.info(request, "Nothing to undo yet.")
    return redirect("match_detail", match_id=match.id)


@login_required
def match_finish(request, match_id):
    match = get_object_or_404(Match, id=match_id)

    if match.created_by_id != request.user.id:
        messages.error(request, "Only the match creator can finish this match.")
        return redirect("match_detail", match_id=match.id)
    if not match.is_active:
        messages.info(request, "This match has already finished.")
        return redirect("match_detail", match_id=match.id)

    if request.method == "POST":
        winner = finish_match(match)
        if winner:
            messages.success(request, f"Match '{match.title}' finished. Winner: {winner.player.display_name}!")
        else:
            messages.success(request, f"Match '{match.title}' finished in a draw.")
        return redirect("match_detail", match_id=match.id)

    return render(request, "match_finish.html", {"match": match, "match_players": _scoreboard(match)})
