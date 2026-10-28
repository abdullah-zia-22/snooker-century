from django.conf import settings
from django.db import models
from django.db.models import Max


class PlayerStats(models.Model):
    """Cached statistics for a player (only finished matches count)."""

    player = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stats")
    total_matches = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    highest_break = models.IntegerField(default=0)
    total_centuries = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stats for {self.player.username}"

    @property
    def win_rate(self):
        return round(100 * self.wins / self.total_matches) if self.total_matches else 0

    def update_stats(self):
        """Recalculate from finished matches. A century is any single break of 100+."""
        from matches.models import MatchPlayer, PottingSequence

        finished = MatchPlayer.objects.filter(player=self.player, match__is_active=False)
        sequences = PottingSequence.objects.filter(match_player__in=finished)

        self.total_matches = finished.count()
        self.wins = finished.filter(is_winner=True).count()
        self.highest_break = max(sequences.aggregate(best=Max("potted_balls"))["best"] or 0, 0)
        self.total_centuries = sequences.filter(potted_balls__gte=100).count()
        self.save()


class PlayerVsPlayerStats(models.Model):
    """Head-to-head record. player1 always has the lower user id (see get_for)."""

    player1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stats_as_player1")
    player2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stats_as_player2")
    player1_wins = models.IntegerField(default=0)
    player2_wins = models.IntegerField(default=0)
    total_matches = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.player1.username} vs {self.player2.username}"

    class Meta:
        unique_together = ["player1", "player2"]
        verbose_name = "Player vs Player Stats"
        verbose_name_plural = "Player vs Player Stats"

    @property
    def draws(self):
        return max(self.total_matches - self.player1_wins - self.player2_wins, 0)

    @classmethod
    def get_for(cls, user_a, user_b):
        """Fetch (or create) the single record for a pair, whatever order the users are given in."""
        first, second = (user_a, user_b) if user_a.id < user_b.id else (user_b, user_a)
        record, _ = cls.objects.get_or_create(player1=first, player2=second)
        return record

    def update_stats(self):
        """Recalculate this record in place from finished matches both players took part in."""
        from matches.models import Match, MatchPlayer

        shared = (
            Match.objects.filter(is_active=False, players__player=self.player1)
            .filter(players__player=self.player2)
            .distinct()
        )
        rows = MatchPlayer.objects.filter(match__in=shared, player__in=[self.player1_id, self.player2_id], is_winner=True)

        self.total_matches = shared.count()
        self.player1_wins = rows.filter(player_id=self.player1_id).count()
        self.player2_wins = rows.filter(player_id=self.player2_id).count()
        self.save()
