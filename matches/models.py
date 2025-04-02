from django.db import models
from django.conf import settings

class Match(models.Model):
    """
    Model for snooker matches
    """
    title = models.CharField(max_length=255)
    date = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_matches')
    
    def __str__(self):
        return f"{self.title} - {self.date.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = "Match"
        verbose_name_plural = "Matches"
        ordering = ['-date']
        
class MatchPlayer(models.Model):
    """
    Model for players in a match
    """
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='players')
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='matches')
    total_score = models.IntegerField(default=0)
    highest_break = models.IntegerField(default=0)
    is_winner = models.BooleanField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.player.username} in {self.match.title}"
    
    class Meta:
        unique_together = ['match', 'player']
        
class PottingSequence(models.Model):
    """
    Model for tracking potting sequences in a match
    """
    match_player = models.ForeignKey(MatchPlayer, on_delete=models.CASCADE, related_name='potting_sequences')
    potted_balls = models.IntegerField()
    sequence_number = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.match_player.player.username} - {self.potted_balls} balls - Sequence {self.sequence_number}"
    
    class Meta:
        ordering = ['match_player', 'sequence_number']
