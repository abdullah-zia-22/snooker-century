from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from .models import Match, MatchPlayer, PottingSequence
from .forms import MatchForm, PottingSequenceForm
from accounts.models import User
from stats.models import PlayerStats, PlayerVsPlayerStats
from django.db.models import Max

@login_required
def match_list(request):
    """View for listing all matches"""
    user_matches = MatchPlayer.objects.filter(player=request.user).select_related('match')
    matches = [mp.match for mp in user_matches]
    return render(request, 'match_list.html', {'matches': matches})

@login_required
def match_create(request):
    """View for creating a new match"""
    if request.method == 'POST':
        form = MatchForm(request.POST, user=request.user)
        if form.is_valid():
            match = form.save(commit=False)
            match.created_by = request.user
            match.save()
            
            # Add players to the match, including the creator
            players = list(form.cleaned_data.get('players'))
            
            # Make sure creator is also a player
            if request.user not in players:
                players.append(request.user)
                
            for player in players:
                MatchPlayer.objects.create(match=match, player=player)
            
            messages.success(request, f"Match '{match.title}' created successfully!")
            return redirect('match_detail', match_id=match.id)
    else:
        form = MatchForm(user=request.user)
    return render(request, 'match_form.html', {'form': form})

@login_required
def match_detail(request, match_id):
    """View for match details and potting input"""
    match = get_object_or_404(Match, id=match_id)
    
    # Ensure user is a participant in this match
    try:
        user_match_player = MatchPlayer.objects.get(match=match, player=request.user)
    except MatchPlayer.DoesNotExist:
        messages.error(request, "You are not a participant in this match.")
        return redirect('match_list')
    
    match_players = match.players.all().select_related('player')
    
    # Get potting sequences for each player
    for mp in match_players:
        mp.sequences = PottingSequence.objects.filter(match_player=mp).order_by('sequence_number')
        mp.total_score = mp.sequences.aggregate(total=Sum('potted_balls'))['total'] or 0
        mp.highest_break = mp.sequences.aggregate(max_break=Max('potted_balls'))['max_break'] or 0
    
    # For adding new potting sequence
    if request.method == 'POST':
        form = PottingSequenceForm(request.POST)
        if form.is_valid():
            potting_sequence = form.save(commit=False)
            
            # Get the player and their latest sequence number
            player_id = form.cleaned_data.get('player_id')
            match_player = get_object_or_404(MatchPlayer, match=match, player_id=player_id)
            
            latest_sequence = PottingSequence.objects.filter(match_player=match_player).order_by('-sequence_number').first()
            sequence_number = (latest_sequence.sequence_number + 1) if latest_sequence else 1
            
            potting_sequence.match_player = match_player
            potting_sequence.sequence_number = sequence_number
            potting_sequence.save()
            
            # Update the player's highest break if needed
            current_break = sum(ps.potted_balls for ps in PottingSequence.objects.filter(
                match_player=match_player, 
                sequence_number__gte=latest_sequence.sequence_number if latest_sequence else 1
            ))
            
            if current_break > match_player.highest_break:
                match_player.highest_break = current_break
                match_player.save()
            
            # If this is an AJAX request, return JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'player': match_player.player.username,
                    'potted_balls': potting_sequence.potted_balls,
                    'sequence_number': potting_sequence.sequence_number,
                    'total_score': match_player.total_score + potting_sequence.potted_balls
                })
                
            return redirect('match_detail', match_id=match.id)
    else:
        form = PottingSequenceForm()
    
    if not match.is_active:
        highest_scoring_player = max(match_players, key=lambda mp: mp.total_score)
    else:
        highest_scoring_player=None
        
    context = {
        'match': match,
        'match_players': match_players,
        'form': form,
        "highest_scoring_player":highest_scoring_player
    }
    
    return render(request, 'match_detail.html', context)

@login_required
def match_finish(request, match_id):
    """View for finishing a match and declaring winners"""
    match = get_object_or_404(Match, id=match_id)
    
    # Only the creator can finish the match
    if match.created_by != request.user:
        messages.error(request, "Only the match creator can finish this match.")
        return redirect('match_detail', match_id=match.id)
    
    if request.method == 'POST':
        # Calculate total scores for each player
        match_players = MatchPlayer.objects.filter(match=match).select_related('player')
        highest_score = None
        winner = None
        
        for mp in match_players:
            total_score = PottingSequence.objects.filter(match_player=mp).aggregate(total=Sum('potted_balls'))['total'] or 0
            if highest_score is None or total_score > highest_score:
                highest_score = total_score
                winner = mp
        
        if winner:
            winner.is_winner = True
            winner.save()
            # Set all other players as not winners
            MatchPlayer.objects.filter(match=match).exclude(id=winner.id).update(is_winner=False)
        
        match.is_active = False
        match.save()
        
        # Update stats for all players
        for mp in match_players:
            stats, _ = PlayerStats.objects.get_or_create(player=mp.player)
            stats.update_stats()
        
        # Update head-to-head stats (fixed to avoid duplicates)
        player_list = [mp.player for mp in match_players]
        for i, player1 in enumerate(player_list):
            for player2 in player_list[i+1:]:
                # Ensure consistent ordering of player1 and player2
                player1_id, player2_id = sorted([player1.id, player2.id])
                ordered_player1 = get_object_or_404(User, id=player1_id)
                ordered_player2 = get_object_or_404(User, id=player2_id)
                
                stats, _ = PlayerVsPlayerStats.objects.get_or_create(
                    player1=ordered_player1,
                    player2=ordered_player2
                )
                stats.update_stats()
        
        messages.success(request, f"Match '{match.title}' has been finished. Winner: {winner.player.username}.")
        return redirect('match_list')
    
    match_players = match.players.all().select_related('player')
    for mp in match_players:
        mp.total_score = PottingSequence.objects.filter(match_player=mp).aggregate(total=Sum('potted_balls'))['total'] or 0
    return render(request, 'match_finish.html', {'match': match, 'match_players': match_players})
