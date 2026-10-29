# Snooker Century

Django app for recording snooker matches, tracking centuries and comparing player stats.

## Local development
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # DEBUG=True, uses a local SQLite file
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
python manage.py test
```

With JavaScript enabled, internal navigation and form submissions use AJAX, so pages update without a full reload.
Forms continue to work with JavaScript disabled.

## Redis cache and sessions
The application loads `.env` during local startup. Set `REDIS_URL` to your Redis connection URL to enable Redis for
the shared cache and sessions (for example `rediss://...` for a TLS-enabled cloud Redis). Optionally set
`REDIS_SESSION_URL` for a separate session Redis endpoint. The leaderboard is cached for up to five minutes and
invalidated when user or player-stat records are saved or deleted. Public landing-page counts and live scoreboard
data are cached for up to one minute and invalidated when users or matches change. Profile-picture responses are
browser-cached for one day; uploaded files use unique names so updated pictures get new URLs.

Without `REDIS_URL`, local development uses in-memory caching and database-backed sessions. For production, use a
secured Redis service with capacity/eviction settings that will not evict active sessions.

## Deploying on Vercel
Set these environment variables in the project settings:

| Variable | Notes |
|---|---|
| `DJANGO_SECRET_KEY` | **Required.** Generate a new one (`python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`). |
| `database_engine`, `database_name`, `database_user`, `database_password`, `database_host` | Postgres settings (as before). Optional: `database_port`, `database_sslmode=require`. |
| `REDIS_URL` | Redis connection URL for cache and sessions. |
| `REDIS_SESSION_URL` | Optional separate Redis URL for sessions. |
| `DEBUG` | Leave unset (False) in production. |

After changing anything in `static/`, run `python manage.py collectstatic --noinput` and commit `staticfiles/`
(Vercel serves them through WhiteNoise).

> **Profile pictures:** The bundled profile picture is served on Vercel. Other files under `media/` remain ignored by
> Git unless explicitly added. Vercel's disk is read-only/ephemeral, so new uploads cannot be stored reliably. For
> persistent uploads, use object storage (S3, Cloudinary, Vercel Blob).
