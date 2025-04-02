from django.urls import path
from . import views

urlpatterns = [
    path("", views.player_stats, name="my_stats"),
    path("player/<str:username>/", views.player_stats, name="player_stats"),
    path("vs/<str:username1>/<str:username2>/", views.player_vs_player, name="player_vs_player"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
]
