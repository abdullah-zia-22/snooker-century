from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import User
from .models import PlayerStats, PlayerVsPlayerStats
from matches.models import Match, MatchPlayer

@login_required
def player_stats(request, username=None):
    """
    View for showing a player's statistics
    If username is provided, show that player's stats
    Otherwise, show the current user's stats
    """
    if username:
        player = get_object_or_404(User, username=username)
    else:
        player = request.user
        
    # Ensure stats exist
    stats, created = PlayerStats.objects.get_or_create(player=player)
    if created or request.GET.get('refresh_stats'):
        stats.update_stats()
        
    # Get recent matches
    recent_matches = MatchPlayer.objects.filter(player=player).order_by('-match__date')[:10]
    
    # Get head-to-head stats
    player_vs_player_stats = PlayerVsPlayerStats.objects.filter(player1=player) | PlayerVsPlayerStats.objects.filter(player2=player)
    
    context = {
        'player': player,
        'stats': stats,
        'recent_matches': recent_matches,
        'player_vs_player_stats': player_vs_player_stats,
    }
    
    return render(request, 'player_stats.html', context)

@login_required
def player_vs_player(request, username1, username2):
    """
    View for showing head-to-head statistics between two players
    """
    player1 = get_object_or_404(User, username=username1)
    player2 = get_object_or_404(User, username=username2)
    
    # Get or create the stats (and ensure they're in the right order)
    try:
        stats = PlayerVsPlayerStats.objects.get(player1=player1, player2=player2)
    except PlayerVsPlayerStats.DoesNotExist:
        try:
            stats = PlayerVsPlayerStats.objects.get(player1=player2, player2=player1)
            # Swap the view for consistency
            player1, player2 = player2, player1
        except PlayerVsPlayerStats.DoesNotExist:
            # Create new stats if they don't exist
            stats = PlayerVsPlayerStats.objects.create(player1=player1, player2=player2)
            
    # Update stats if requested
    if request.GET.get('refresh_stats'):
        stats.update_stats()
        
    # Get matches where both players participated
    matches = Match.objects.filter(
        players__player=player1
    ).filter(
        players__player=player2
    ).distinct().order_by('-date')
    
    context = {
        'player1': player1,
        'player2': player2,
        'stats': stats,
        'matches': matches,
    }
    
    return render(request, 'player_vs_player.html', context)

@login_required
def leaderboard(request):
    """
    View for showing a leaderboard of all players
    """
    # Get all player stats
    stats = PlayerStats.objects.select_related('player').all().order_by('-wins', '-highest_break')
    
    context = {
        'stats': stats,
    }
    
    return render(request, 'leaderboard.html', context)
