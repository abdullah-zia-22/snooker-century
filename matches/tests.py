from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from stats.models import PlayerStats, PlayerVsPlayerStats

from .models import Match, MatchPlayer, PottingSequence
from .services import add_sequence, finish_match

PASSWORD = "S3cure-pass-Word!"


def make_user(username, **extra):
    return User.objects.create_user(username=username, password=PASSWORD, first_name=username.title(), **extra)


class MatchFlowTests(TestCase):
    def setUp(self):
        self.alice, self.bob, self.cara = make_user("alice"), make_user("bob"), make_user("cara")
        self.client.login(username="alice", password=PASSWORD)

    def create_match(self, players=None):
        players = players or [self.bob]
        response = self.client.post(reverse("match_create"), {"title": "Frame", "location": "Club", "notes": "", "players": [p.id for p in players]})
        match = Match.objects.get(title="Frame")
        self.assertRedirects(response, reverse("match_detail", args=[match.id]))
        return match

    def test_create_adds_creator_and_players(self):
        match = self.create_match()
        self.assertEqual(set(match.players.values_list("player__username", flat=True)), {"alice", "bob"})

    def test_create_requires_at_least_one_opponent(self):
        response = self.client.post(reverse("match_create"), {"title": "Solo", "players": []})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Match.objects.exists())

    def test_admins_and_inactive_users_are_not_selectable(self):
        make_user("boss", is_admin=True)
        make_user("ghost", is_active=False)
        names = set(self.client.get(reverse("match_create")).context["form"].fields["players"].queryset.values_list("username", flat=True))
        self.assertEqual(names, {"bob", "cara"})

    def test_scoring_and_highest_break_are_correct(self):
        match = self.create_match()
        for points in (20, 45, 10):
            self.client.post(reverse("match_detail", args=[match.id]), {"player_id": self.alice.id, "potted_balls": points})
        mp = MatchPlayer.objects.get(match=match, player=self.alice)
        self.assertEqual(mp.total_score, 75)
        self.assertEqual(mp.highest_break, 45)  # was previously the sum of the last two entries (55)

    def test_ajax_score_submission_returns_updated_score_data(self):
        match = self.create_match()
        response = self.client.post(
            reverse("match_detail", args=[match.id]),
            {"player_id": self.alice.id, "potted_balls": 42},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "success": True,
                "player": "alice",
                "potted_balls": 42,
                "sequence_number": 1,
                "total_score": 42,
            },
        )

    def test_ajax_score_submission_returns_validation_error(self):
        match = self.create_match()
        response = self.client.post(
            reverse("match_detail", args=[match.id]),
            {"player_id": self.alice.id, "potted_balls": 148},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"success": False, "error": "Score cannot exceed 147 (the maximum break)."})
        self.assertFalse(PottingSequence.objects.exists())

    def test_negative_entries_reduce_total_but_not_highest_break(self):
        match = self.create_match()
        add_sequence(match, self.alice.id, 30)
        add_sequence(match, self.alice.id, -4)
        mp = MatchPlayer.objects.get(match=match, player=self.alice)
        self.assertEqual((mp.total_score, mp.highest_break), (26, 30))

    def test_out_of_range_scores_rejected(self):
        match = self.create_match()
        response = self.client.post(reverse("match_detail", args=[match.id]), {"player_id": self.alice.id, "potted_balls": 148})
        self.assertRedirects(response, reverse("match_detail", args=[match.id]))
        self.assertFalse(PottingSequence.objects.exists())

    def test_only_creator_can_record_scores(self):
        match = self.create_match()
        self.client.logout()
        self.client.login(username="bob", password=PASSWORD)
        self.client.post(reverse("match_detail", args=[match.id]), {"player_id": self.bob.id, "potted_balls": 50})
        self.assertFalse(PottingSequence.objects.exists())

    def test_cannot_score_for_someone_outside_the_match(self):
        match = self.create_match()
        self.client.post(reverse("match_detail", args=[match.id]), {"player_id": self.cara.id, "potted_balls": 50})
        self.assertFalse(PottingSequence.objects.exists())

    def test_non_participant_is_redirected(self):
        match = self.create_match()
        self.client.logout()
        self.client.login(username="cara", password=PASSWORD)
        self.assertRedirects(self.client.get(reverse("match_detail", args=[match.id])), reverse("match_list"))

    def test_undo_removes_latest_entry_and_recalculates(self):
        match = self.create_match()
        add_sequence(match, self.alice.id, 40)
        add_sequence(match, self.bob.id, 12)
        self.client.post(reverse("match_undo", args=[match.id]))
        self.assertEqual(PottingSequence.objects.count(), 1)
        self.assertEqual(MatchPlayer.objects.get(match=match, player=self.bob).total_score, 0)
        self.assertEqual(self.client.get(reverse("match_undo", args=[match.id])).status_code, 405)

    def test_finish_declares_winner_locks_scores_and_updates_stats(self):
        match = self.create_match()
        add_sequence(match, self.alice.id, 104)
        add_sequence(match, self.bob.id, 30)
        response = self.client.post(reverse("match_finish", args=[match.id]))
        self.assertRedirects(response, reverse("match_detail", args=[match.id]))

        match.refresh_from_db()
        self.assertFalse(match.is_active)
        self.assertTrue(MatchPlayer.objects.get(match=match, player=self.alice).is_winner)
        self.assertFalse(MatchPlayer.objects.get(match=match, player=self.bob).is_winner)

        a = PlayerStats.objects.get(player=self.alice)
        self.assertEqual((a.total_matches, a.wins, a.highest_break, a.total_centuries), (1, 1, 104, 1))
        h2h = PlayerVsPlayerStats.get_for(self.alice, self.bob)
        self.assertEqual((h2h.total_matches, h2h.player1_wins, h2h.player2_wins), (1, 1, 0))

        # Locked afterwards
        self.client.post(reverse("match_detail", args=[match.id]), {"player_id": self.bob.id, "potted_balls": 99})
        self.assertEqual(PottingSequence.objects.count(), 2)
        # Cannot be finished twice
        self.client.post(reverse("match_finish", args=[match.id]))
        self.assertEqual(PlayerStats.objects.get(player=self.alice).total_matches, 1)

    def test_tie_is_a_draw_with_no_winner(self):
        match = self.create_match()
        add_sequence(match, self.alice.id, 50)
        add_sequence(match, self.bob.id, 50)
        self.assertIsNone(finish_match(match))
        self.assertFalse(MatchPlayer.objects.filter(match=match, is_winner=True).exists())
        self.assertEqual(PlayerStats.objects.get(player=self.alice).wins, 0)
        self.assertEqual(PlayerVsPlayerStats.get_for(self.alice, self.bob).draws, 1)

    def test_only_creator_can_finish(self):
        match = self.create_match()
        self.client.logout()
        self.client.login(username="bob", password=PASSWORD)
        self.client.post(reverse("match_finish", args=[match.id]))
        match.refresh_from_db()
        self.assertTrue(match.is_active)

    def test_match_list_is_newest_first_and_filterable(self):
        old = self.create_match()
        add_sequence(old, self.alice.id, 5)
        finish_match(old)
        self.client.post(reverse("match_create"), {"title": "Second", "players": [self.bob.id]})
        rows = self.client.get(reverse("match_list")).context["rows"]
        self.assertEqual([r["match"].title for r in rows], ["Second", "Frame"])
        live = self.client.get(reverse("match_list"), {"status": "live"}).context["rows"]
        self.assertEqual([r["match"].title for r in live], ["Second"])
        self.assertEqual(rows[1]["result"], "won")
