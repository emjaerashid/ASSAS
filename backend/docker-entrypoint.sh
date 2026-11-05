#!/bin/sh
# Container start-up: prepare the data volume, apply migrations, run Django's
# deployment checks, then hand over to gunicorn.
set -e

mkdir -p "$(dirname "${DJANGO_DB_PATH:-/data/db.sqlite3}")" "${DJANGO_MEDIA_ROOT:-/data/media}"

python manage.py migrate --noinput
python manage.py check --deploy --fail-level ERROR

# Hosts without a persistent disk or shell (e.g. Render's free tier) start
# from an empty database every time, so these optionally rebuild it:
#   DJANGO_SEED_DEMO=True          load the sample faculty, subjects and students
#   DJANGO_SUPERUSER_PASSWORD=...  admin password (with the demo: for ADMIN001;
#   DJANGO_SUPERUSER_STUDENT_ID=.. otherwise creates this admin if it's missing)
if [ "${DJANGO_SEED_DEMO:-False}" = "True" ]; then
    if [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
        python manage.py seed_data --allow-production --admin-password "$DJANGO_SUPERUSER_PASSWORD"
    else
        python manage.py seed_data --allow-production
    fi
elif [ -n "${DJANGO_SUPERUSER_STUDENT_ID:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    export DJANGO_SUPERUSER_FULL_NAME="${DJANGO_SUPERUSER_FULL_NAME:-Administrator}"
    python manage.py createsuperuser --noinput 2>/dev/null || echo "Admin $DJANGO_SUPERUSER_STUDENT_ID already exists."
fi

# SQLite allows one writer at a time, so keep the worker count small.
exec gunicorn assas_backend.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout 60 \
    --access-logfile -
