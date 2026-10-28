import tempfile
from pathlib import Path

from django.contrib.messages import get_messages
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from matches.models import Match, MatchPlayer
from matches.services import add_sequence, finish_match
from stats.models import PlayerStats

from .models import User

PASSWORD = "S3cure-pass-Word!"


def make_user(username, **extra):
    extra.setdefault("first_name", username.title())
    extra.setdefault("last_name", "Player")
    extra.setdefault("email", f"{username}@example.com")
    return User.objects.create_user(username=username, password=PASSWORD, **extra)


class ProfilePictureServingTests(SimpleTestCase):
    def test_bundled_profile_picture_is_served_when_debug_is_disabled(self):
        with tempfile.TemporaryDirectory() as media_root:
            picture = Path(media_root) / "profile_pics" / "avatar.jpeg"
            picture.parent.mkdir()
            picture.write_bytes(b"profile image")

            with override_settings(DEBUG=False, MEDIA_ROOT=media_root):
                response = self.client.get(
                    reverse("profile_picture", kwargs={"filename": picture.name})
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"profile image")

    def test_missing_profile_picture_returns_404(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(DEBUG=False, MEDIA_ROOT=media_root):
                response = self.client.get(
                    reverse("profile_picture", kwargs={"filename": "missing.jpeg"})
                )

            self.assertEqual(response.status_code, 404)


class PublicPagesTests(TestCase):
    def test_landing_page_counts_finished_centuries_and_players(self):
        a, b = make_user("alice"), make_user("bob")
        make_user("boss", is_admin=True)  # admins are not "players"
        match = Match.objects.create(title="m", created_by=a)
        MatchPlayer.objects.bulk_create([MatchPlayer(match=match, player=a), MatchPlayer(match=match, player=b)])
        add_sequence(match, a.id, 101)
        add_sequence(match, a.id, 120)
        finish_match(match)

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["player_count"], 2)
        self.assertEqual(response.context["match_count"], 1)
        self.assertEqual(response.context["century_count"], 2)
        self.assertIsNone(response.context["live_match"])

    def test_landing_page_shows_latest_live_match_scores(self):
        a, b = make_user("alice"), make_user("bob")
        match = Match.objects.create(title="Friday final", created_by=a)
        MatchPlayer.objects.bulk_create(
            [MatchPlayer(match=match, player=a), MatchPlayer(match=match, player=b)]
        )
        add_sequence(match, a.id, 35)
        add_sequence(match, a.id, 42)
        add_sequence(match, b.id, 20)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.context["live_match"], match)
        self.assertEqual(
            [
                (player.player.display_name, player.live_total, player.live_best)
                for player in response.context["live_players"]
            ],
            [("Alice Player", 77, 42), ("Bob Player", 20, 20)],
        )
        self.assertContains(response, "Friday final")
        self.assertContains(response, "77")
        self.assertNotContains(response, "Example scoreboard")

    def test_landing_redirects_logged_in_users_consistently(self):
        make_user("staffer", is_staff=True)  # staff flag alone must NOT send you to the admin portal
        self.client.login(username="staffer", password=PASSWORD)
        self.assertRedirects(self.client.get(reverse("home")), reverse("dashboard"), fetch_redirect_response=False)
        make_user("boss", is_admin=True)
        self.client.login(username="boss", password=PASSWORD)
        self.assertRedirects(self.client.get(reverse("home")), reverse("admin_dashboard"), fetch_redirect_response=False)


class SignUpTests(TestCase):
    data = {
        "username": "newbie", "email": "new@example.com", "first_name": "New", "last_name": "Bie",
        "password1": PASSWORD, "password2": PASSWORD, "bio": "hello",
    }

    def test_sign_up_creates_user(self):
        response = self.client.post(reverse("sign_up"), self.data)
        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="newbie")
        self.assertEqual(user.bio, "hello")
        self.assertEqual(user.first_name, "New")

    def test_duplicate_email_rejected_case_insensitively(self):
        make_user("existing", email="NEW@example.com")
        response = self.client.post(reverse("sign_up"), self.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="newbie").exists())

    def test_errors_not_duplicated_in_messages(self):
        response = self.client.post(reverse("sign_up"), {**self.data, "password2": "different"})
        self.assertEqual(len(list(get_messages(response.wsgi_request))), 1)

    def test_logged_in_user_is_redirected_away(self):
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("sign_up")).status_code, 302)


class LoginLogoutTests(TestCase):
    def setUp(self):
        make_user("alice")

    def test_login_success_redirects_to_dashboard(self):
        response = self.client.post(reverse("login"), {"username": "alice", "password": PASSWORD, "remember_me": "on"})
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    def test_login_failure_shows_form_error(self):
        response = self.client.post(reverse("login"), {"username": "alice", "password": "nope"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())

    def test_without_remember_me_session_expires_on_close(self):
        self.client.post(reverse("login"), {"username": "alice", "password": PASSWORD})
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_next_parameter_is_honoured_when_safe_and_ignored_when_not(self):
        url = reverse("login")
        ok = self.client.post(url, {"username": "alice", "password": PASSWORD, "next": reverse("match_list")})
        self.assertRedirects(ok, reverse("match_list"), fetch_redirect_response=False)
        self.client.post(reverse("logout"))
        bad = self.client.post(url, {"username": "alice", "password": PASSWORD, "next": "https://evil.example/"})
        self.assertRedirects(bad, reverse("dashboard"), fetch_redirect_response=False)

    def test_logout_requires_post(self):
        self.client.login(username="alice", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class AdminPortalTests(TestCase):
    def setUp(self):
        self.boss = make_user("boss", is_admin=True)
        self.root = make_user("root", is_superuser=True, is_staff=True)
        self.alice = make_user("alice")
        self.bob = make_user("bob")
        self.client.login(username="boss", password=PASSWORD)

    def test_players_cannot_open_admin_pages(self):
        self.client.logout()
        self.client.login(username="alice", password=PASSWORD)
        for name in ("admin_dashboard", "admin_user_list", "admin_user_create"):
            self.assertRedirects(self.client.get(reverse(name)), reverse("dashboard"), fetch_redirect_response=False)

    def test_admin_dashboard_counts_all_admin_kinds(self):
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.context["admin_users"], 2)  # boss (is_admin) + root (superuser)

    def test_edit_page_does_not_shadow_request_user(self):
        response = self.client.get(reverse("admin_user_edit", args=[self.alice.id]))
        self.assertEqual(response.context["user"], self.boss)
        self.assertEqual(response.context["target_user"], self.alice)

    def test_create_page_does_not_show_someone_elses_picture(self):
        response = self.client.get(reverse("admin_user_create"))
        self.assertNotIn("target_user", response.context)

    def test_admin_can_create_user_and_stats_row(self):
        response = self.client.post(reverse("admin_user_create"), {
            "username": "carol", "email": "c@example.com", "first_name": "Carol", "last_name": "C",
            "password1": PASSWORD, "password2": PASSWORD,
        })
        self.assertRedirects(response, reverse("admin_user_list"))
        self.assertTrue(PlayerStats.objects.filter(player__username="carol").exists())

    def test_cannot_delete_self(self):
        response = self.client.post(reverse("admin_user_delete", args=[self.boss.id]))
        self.assertRedirects(response, reverse("admin_user_list"))
        self.assertTrue(User.objects.filter(id=self.boss.id).exists())

    def test_admin_cannot_touch_superuser(self):
        self.client.post(reverse("admin_user_delete", args=[self.root.id]))
        self.assertTrue(User.objects.filter(id=self.root.id).exists())
        response = self.client.get(reverse("admin_user_edit", args=[self.root.id]))
        self.assertRedirects(response, reverse("admin_user_list"), fetch_redirect_response=False)

    def test_cannot_delete_match_creator_but_can_delete_plain_player(self):
        match = Match.objects.create(title="m", created_by=self.alice)
        MatchPlayer.objects.bulk_create([MatchPlayer(match=match, player=self.alice), MatchPlayer(match=match, player=self.bob)])
        self.client.post(reverse("admin_user_delete", args=[self.alice.id]))
        self.assertTrue(User.objects.filter(id=self.alice.id).exists())
        self.assertTrue(Match.objects.filter(id=match.id).exists())

        self.client.post(reverse("admin_user_delete", args=[self.bob.id]))
        self.assertFalse(User.objects.filter(id=self.bob.id).exists())
        self.assertTrue(Match.objects.filter(id=match.id).exists())

    def test_user_list_filters_and_paginates(self):
        for i in range(15):
            make_user(f"extra{i:02d}")
        page1 = self.client.get(reverse("admin_user_list"))
        self.assertEqual(len(page1.context["users"]), 12)
        page2 = self.client.get(reverse("admin_user_list"), {"page": 2})
        self.assertGreater(len(page2.context["users"]), 0)
        admins = self.client.get(reverse("admin_user_list"), {"status": "admin"})
        self.assertEqual([u.username for u in admins.context["users"]], ["root"])  # excludes the viewer
        found = self.client.get(reverse("admin_user_list"), {"search": "extra03"})
        self.assertEqual(found.context["total_count"], 1)
