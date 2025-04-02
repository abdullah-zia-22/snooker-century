from django.db import models
from django.conf import settings
from django.db.models import Sum, Avg, Max, Count

class PlayerStats(models.Model):
    """
    Model for storing player statistics
    """
    player = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stats')
    total_matches = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    highest_break = models.IntegerField(default=0)
    total_centuries = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Stats for {self.player.username}"
    
    def update_stats(self):
        """
        Update player statistics based on match history
        """
        from matches.models import MatchPlayer, PottingSequence
        
        # Get all matches the player has participated in
        player_matches = MatchPlayer.objects.filter(player=self.player)
        
        # Total matches
        self.total_matches = player_matches.count()
        
        # Wins
        self.wins = player_matches.filter(is_winner=True).count()
        
        # Highest break
        highest_break = player_matches.aggregate(max_break=Max('highest_break'))
        self.highest_break = highest_break['max_break'] or 0
        
        # Total centuries
        # A century is when a continuous sequence of pots adds up to 100 or more
        # This is simplified and would need refinement in a real app
        self.total_centuries = player_matches.filter(highest_break__gte=100).count()
        
        self.save()

class PlayerVsPlayerStats(models.Model):
    """
    Model for storing head-to-head statistics between players
    """
    player1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stats_as_player1')
    player2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stats_as_player2')
    player1_wins = models.IntegerField(default=0)
    player2_wins = models.IntegerField(default=0)
    total_matches = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.player1.username} vs {self.player2.username}"
    
    class Meta:
        unique_together = ['player1', 'player2']
        verbose_name = "Player vs Player Stats"
        verbose_name_plural = "Player vs Player Stats"
    
    def update_stats(self):
        """
        Update head-to-head statistics based on match history
        """
        from matches.models import Match, MatchPlayer

        # Ensure consistent ordering of player1 and player2
        player1, player2 = sorted([self.player1, self.player2], key=lambda p: p.id)

        # Find the record, creating it if it doesn't exist.
        record, created = type(self).objects.get_or_create(player1=player1, player2=player2)

        # Find all matches where both players participated
        matches_with_both_players = Match.objects.filter(
            players__player=player1
        ).filter(
            players__player=player2
        ).distinct()

        record.total_matches = matches_with_both_players.count()
        record.player1_wins = 0
        record.player2_wins = 0  # Reset before counting

        for match in matches_with_both_players:
            player1_match = MatchPlayer.objects.filter(match=match, player=player1).first()
            player2_match = MatchPlayer.objects.filter(match=match, player=player2).first()

            if player1_match and player1_match.is_winner:
                record.player1_wins += 1
            elif player2_match and player2_match.is_winner:
                record.player2_wins += 1

        record.save()  # Save the updated record