# What changed

## Design / UX
- New design system (`static/css/app.css`) in the logo's navy / red / white, with light + dark themes (auto + toggle).
- Mobile-first: bottom tab bar with a big "New match" button, stacked-card tables on phones, 48px+ tap targets,
  safe-area support, no horizontal overflow at 360px.
- One shared `templates/base.html` (nav with real links, global flash messages, account menu, footer).
- Score pad rebuilt for phones: tap a player, type points, quick-value chips, **undo last entry**, locked once finished.
- Leaderboard podium, win-rate ring, avatars (initials fallback), head-to-head bar, empty states, pagination.
- Forms: consistent fields with inline errors, show/hide password, autocomplete attributes, double-submit protection.

## Bugs fixed
1. Font Awesome never loaded (`YOUR_KIT_ID` placeholder) -> all icons were missing. Replaced with Bootstrap Icons.
2. Highest break was computed as the sum of the last two entries; now the true best single break.
3. `MatchPlayer.total_score/highest_break` were never saved; now persisted on every change and at finish.
4. Centuries were counted per match, not per break; now every 100+ break counts.
5. Stats counted unfinished matches; now only finished ones.
6. Ties silently gave the win to whoever was listed first; now a draw (no winner).
7. Any participant could add scores, even after a match ended; now creator only and only while live.
8. Matches could be finished repeatedly; now blocked.
9. Head-to-head: duplicate/reversed rows, stale numbers after refresh, and /vs/you/you/ created a bogus row. Fixed.
10. Match list was unordered; now newest first with Live/Won/Lost/Draw status and filters.
11. Admin pages passed the edited user as `user`, shadowing the logged-in user (Create page showed the admin's picture).
12. Admins could delete themselves or superusers; deleting a match creator wiped other players' matches. Blocked, with
    opponent stats recalculated after a safe delete.
13. Admin list had no pagination (template expected it); added. Admin counts ignored `is_admin`; fixed.
14. Landing page and dashboard disagreed on who is an admin (`is_staff` vs `is_admin`), causing odd redirects.
15. Login ignored `next`, "Remember me" and form errors; `alert-error` isn't a Bootstrap class; sign-up showed every error twice.
16. Missing `default-avatar.png`, template files inside public `/static`, unpinned Chart.js, Unsplash hot-link.
17. Leaderboard included admins/inactive users and omitted brand-new players.
18. Email uniqueness was not enforced.

## Security / config
- Logout is POST-only (was a GET, so any page could log you out).
- `SECRET_KEY` and `DEBUG` come from the environment (hard-coded key and `DEBUG=True` removed);
  `print(DATABASES)` (leaked the DB password into logs) removed; `ALLOWED_HOSTS` wildcard fixed (`.vercel.app`);
  secure cookies + CSRF trusted origins in production; SQLite fallback for local dev.
- Removed the stray root `settings.py`; templates moved from `static/templates` to `templates/`.
- `mydatabase.sqlite` and `media/` are no longer in the project (they contain user data / password hashes).
  Keep your own copies; they're now in `.gitignore`.
- No model changes, so **no new migrations**.
