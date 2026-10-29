from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from matches.models import Match, MatchPlayer
from matches.services import add_sequence, finish_match

from .cache import LEADERBOARD_CACHE_KEY
from .models import PlayerStats, PlayerVsPlayerStats

PASSWORD = "S3cure-pass-Word!"


def make_user(username, **extra):
    return User.objects.create_user(username=username, password=PASSWORD, first_name=username.title(), **extra)


def play(creator, others, scores, finish=True):
    match = Match.objects.create(title="m", created_by=creator)
    for user in [creator, *others]:
        MatchPlayer.objects.create(match=match, player=user)
    for user, points in scores:
        add_sequence(match, user.id, points)
    if finish:
        finish_match(match)
    return match


class StatsTests(TestCase):
    def setUp(self):
        self.alice, self.bob = make_user("alice"), make_user("bob")

    def test_only_finished_matches_count(self):
        play(self.alice, [self.bob], [(self.alice, 110)], finish=False)
        stats, _ = PlayerStats.objects.get_or_create(player=self.alice)
        stats.update_stats()
        self.assertEqual((stats.total_matches, stats.total_centuries), (0, 0))

    def test_every_century_counts_not_just_one_per_match(self):
        play(self.alice, [self.bob], [(self.alice, 100), (self.alice, 120), (self.alice, 30), (self.bob, 5)])
        stats = PlayerStats.objects.get(player=self.alice)
        self.assertEqual(stats.total_centuries, 2)
        self.assertEqual(stats.highest_break, 120)
        self.assertEqual(stats.win_rate, 100)

    def test_head_to_head_is_normalised_and_never_duplicated(self):
        play(self.alice, [self.bob], [(self.alice, 10)])
        play(self.bob, [self.alice], [(self.bob, 10)])
        self.assertEqual(PlayerVsPlayerStats.objects.count(), 1)
        record = PlayerVsPlayerStats.get_for(self.bob, self.alice)
        self.assertLess(record.player1_id, record.player2_id)
        self.assertEqual((record.total_matches, record.player1_wins, record.player2_wins), (2, 1, 1))

    def test_head_to_head_view_shows_fresh_numbers_in_url_order(self):
        play(self.alice, [self.bob], [(self.alice, 10)])
        self.client.login(username="alice", password=PASSWORD)
        PlayerVsPlayerStats.objects.update(player1_wins=0, player2_wins=0, total_matches=0)  # simulate stale row
        response = self.client.get(reverse("player_vs_player", args=["bob", "alice"]))
        self.assertEqual((response.context["wins1"], response.context["wins2"]), (0, 1))
        self.assertEqual(response.context["stats"].total_matches, 1)
        self.assertEqual(PlayerVsPlayerStats.objects.count(), 1)

    def test_versus_yourself_redirects(self):
        self.client.login(username="alice", password=PASSWORD)
        response = self.client.get(reverse("player_vs_player", args=["alice", "alice"]))
        self.assertRedirects(response, reverse("player_stats", args=["alice"]), fetch_redirect_response=False)

    def test_stats_pages_render_for_player_with_no_matches(self):
        self.client.login(username="alice", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("my_stats")).status_code, 200)
        self.assertEqual(self.client.get(reverse("player_stats", args=["bob"])).status_code, 200)
        self.assertEqual(self.client.get(reverse("player_vs_player", args=["alice", "bob"])).status_code, 200)


class LeaderboardTests(TestCase):
    def setUp(self):
        cache.delete(LEADERBOARD_CACHE_KEY)

    def test_excludes_admins_and_inactive_and_includes_new_players(self):
        alice, bob = make_user("alice"), make_user("bob")
        make_user("boss", is_admin=True)
        make_user("root", is_superuser=True)
        make_user("ghost", is_active=False)
        newbie = make_user("newbie")  # never opened a stats page
        play(alice, [bob], [(alice, 10)])

        self.client.login(username="alice", password=PASSWORD)
        stats = self.client.get(reverse("leaderboard")).context["stats"]
        names = [s.player.username for s in stats]
        self.assertEqual(names[0], "alice")
        self.assertCountEqual(names, ["alice", "bob", newbie.username])

    def test_stats_save_invalidates_cached_leaderboard(self):
        alice = make_user("alice")
        self.client.login(username="alice", password=PASSWORD)

        first_response = self.client.get(reverse("leaderboard"))
        self.assertIsNotNone(cache.get(LEADERBOARD_CACHE_KEY))
        self.assertEqual(first_response.context["stats"][0].wins, 0)

        stats = PlayerStats.objects.get(player=alice)
        stats.wins = 3
        stats.save()

        refreshed_response = self.client.get(reverse("leaderboard"))
        self.assertEqual(refreshed_response.context["stats"][0].wins, 3)

    def test_requires_login(self):
        self.assertEqual(self.client.get(reverse("leaderboard")).status_code, 302)
