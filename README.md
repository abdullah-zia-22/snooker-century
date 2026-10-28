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
python manage.py test       # 42 tests
```

## Deploying on Vercel
Set these environment variables in the project settings:

| Variable | Notes |
|---|---|
| `DJANGO_SECRET_KEY` | **Required.** Generate a new one (`python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`). |
| `database_engine`, `database_name`, `database_user`, `database_password`, `database_host` | Postgres settings (as before). Optional: `database_port`, `database_sslmode=require`. |
| `DEBUG` | Leave unset (False) in production. |

After changing anything in `static/`, run `python manage.py collectstatic --noinput` and commit `staticfiles/`
(Vercel serves them through WhiteNoise).

> **Profile pictures:** The bundled profile picture is served on Vercel. Other files under `media/` remain ignored by
> Git unless explicitly added. Vercel's disk is read-only/ephemeral, so new uploads cannot be stored reliably. For
> persistent uploads, use object storage (S3, Cloudinary, Vercel Blob).
