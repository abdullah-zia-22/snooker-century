from django.contrib import admin

from .models import Match, MatchPlayer, PottingSequence


class MatchPlayerInline(admin.TabularInline):
    model = MatchPlayer
    extra = 0


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "location", "is_active", "created_by")
    list_filter = ("is_active",)
    search_fields = ("title", "location")
    inlines = [MatchPlayerInline]


@admin.register(PottingSequence)
class PottingSequenceAdmin(admin.ModelAdmin):
    list_display = ("match_player", "sequence_number", "potted_balls", "timestamp")
