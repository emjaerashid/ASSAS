#!/bin/sh
# Container start-up: prepare the data volume, apply migrations, run Django's
# deployment checks, then hand over to gunicorn.
set -e

mkdir -p "$(dirname "${DJANGO_DB_PATH:-/data/db.sqlite3}")" "${DJANGO_MEDIA_ROOT:-/data/media}"

python manage.py migrate --noinput
python manage.py check --deploy --fail-level ERROR

# SQLite allows one writer at a time, so keep the worker count small.
exec gunicorn assas_backend.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout 60 \
    --access-logfile -
