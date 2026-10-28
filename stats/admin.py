from django.contrib import admin

from .models import PlayerStats, PlayerVsPlayerStats


@admin.register(PlayerStats)
class PlayerStatsAdmin(admin.ModelAdmin):
    list_display = ("player", "total_matches", "wins", "highest_break", "total_centuries", "last_updated")
    search_fields = ("player__username",)


@admin.register(PlayerVsPlayerStats)
class PlayerVsPlayerStatsAdmin(admin.ModelAdmin):
    list_display = ("player1", "player2", "player1_wins", "player2_wins", "total_matches")
