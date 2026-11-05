# syntax=docker/dockerfile:1

# ---- 1. Build the React app ----
FROM node:22.12.0-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2. Django + gunicorn, serving the API, the built app and static files ----
FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_FRONTEND_DIST=/app/frontend_dist \
    DJANGO_STATIC_ROOT=/app/staticfiles \
    DJANGO_DB_PATH=/data/db.sqlite3 \
    DJANGO_MEDIA_ROOT=/data/media

WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /frontend/dist /app/frontend_dist

# Static files are collected at build time; the throwaway key only exists
# for this step (settings refuse to load without one).
RUN DJANGO_SECRET_KEY=build-only-not-secret python manage.py collectstatic --noinput \
    && python -m whitenoise.compress /app/frontend_dist \
    && chmod +x docker-entrypoint.sh

# The database and uploads live on a volume so they survive redeploys.
RUN useradd --system --uid 1000 --home /app assas && mkdir -p /data && chown assas /data
USER assas
VOLUME ["/data"]
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
