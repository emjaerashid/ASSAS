#!/bin/bash
# Set up or update ASSAS on PythonAnywhere. Run it in a PythonAnywhere Bash
# console from anywhere:
#
#   bash ~/ASSAS/deploy/pythonanywhere/setup.sh
#
# It is safe to re-run: after `git pull` it updates packages, applies
# migrations, refreshes static files and reloads the site.
#
# Optional overrides (export before running):
#   PA_DOMAIN   site address  (default: $USER.pythonanywhere.com;
#                              EU accounts: $USER.eu.pythonanywhere.com)
#   PA_PYTHON   interpreter   (default: newest of python3.13 / python3.12)
#   PA_WSGI_DIR WSGI file dir (default: /var/www)
#   PA_SEED_DEMO=1  load the sample faculty, subjects and students (first run)
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BACKEND="$APP_DIR/backend"
FRONTEND="$APP_DIR/frontend"
DOMAIN="${PA_DOMAIN:-${USER}.pythonanywhere.com}"
VENV="$HOME/.virtualenvs/assas"
WSGI_FILE="${PA_WSGI_DIR:-/var/www}/$(echo "$DOMAIN" | tr '.' '_')_wsgi.py"

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

# --- 1. Python 3.12+ (Django 6 needs it) -------------------------------------
step "Checking Python"
PYTHON="${PA_PYTHON:-}"
if [ -z "$PYTHON" ]; then
    for candidate in python3.13 python3.12; do
        if command -v "$candidate" >/dev/null 2>&1; then PYTHON="$candidate"; break; fi
    done
fi
if [ -z "$PYTHON" ] || ! "$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null; then
    echo "Python 3.12 or newer is required but wasn't found."
    echo "On the Account page, switch your system image to the newest one, then re-run this script."
    exit 1
fi
PY_VERSION="$("$PYTHON" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
echo "Using $PYTHON ($PY_VERSION) for $DOMAIN"

# --- 2. Virtualenv + packages ------------------------------------------------
step "Installing Python packages into $VENV"
if [ -x "$VENV/bin/python" ] && [ "$("$VENV/bin/python" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')" != "$PY_VERSION" ]; then
    echo "Existing virtualenv uses a different Python; recreating it."
    rm -rf "$VENV"
fi
[ -x "$VENV/bin/python" ] || "$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --disable-pip-version-check --upgrade pip
"$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$BACKEND/requirements.txt"

# --- 3. Built frontend -------------------------------------------------------
step "Checking the built frontend"
# Free accounts can't reliably build it here, so it's built locally and
# uploaded as dist.zip (to the home directory or frontend/).
for zip in "$HOME/dist.zip" "$FRONTEND/dist.zip"; do
    if [ -f "$zip" ]; then
        rm -rf "$FRONTEND/dist"
        unzip -q -o "$zip" -d "$FRONTEND"
        rm -f "$zip"
        echo "Unpacked $zip"
    fi
done
if [ -f "$FRONTEND/dist/index.html" ]; then
    echo "Frontend build found."
else
    echo "WARNING: $FRONTEND/dist/index.html is missing - the site will show 'Frontend build not found'."
    echo "Build it on your computer (cd frontend && npm run build && zip -r dist.zip dist),"
    echo "upload dist.zip to your home directory on the Files tab, then re-run this script."
fi

# --- 4. Production settings (backend/.env, gitignored) ------------------------
step "Production settings"
if [ -f "$BACKEND/.env" ]; then
    echo "Keeping existing $BACKEND/.env"
else
    SECRET_KEY="$("$VENV/bin/python" -c 'import secrets; print(secrets.token_urlsafe(50))')"
    cat > "$BACKEND/.env" <<ENV
# Production settings for $DOMAIN (gitignored). Created by setup.sh.
DJANGO_SECRET_KEY=$SECRET_KEY
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$DOMAIN
DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMAIN
# PythonAnywhere terminates HTTPS and forwards X-Forwarded-Proto.
DJANGO_BEHIND_PROXY=True
DJANGO_HSTS_SECONDS=3600
ENV
    chmod 600 "$BACKEND/.env"
    echo "Created $BACKEND/.env with a new secret key."
fi

# --- 5. Database, static files, checks ---------------------------------------
cd "$BACKEND"
step "Applying database migrations"
"$VENV/bin/python" manage.py migrate --noinput
step "Collecting static files"
"$VENV/bin/python" manage.py collectstatic --noinput | tail -1
step "Running Django's deployment checks"
"$VENV/bin/python" manage.py check --deploy --fail-level ERROR

# --- 6. Optional sample data ---------------------------------------------------
if [ "${PA_SEED_DEMO:-0}" = "1" ]; then
    step "Loading sample demo data"
    "$VENV/bin/python" manage.py seed_data --allow-production
    # seed_data's ADMIN001 starts with the public password ADMIN001.
    if [ -t 0 ]; then
        echo "Choose a new password for ADMIN001 (the default 'ADMIN001' is public):"
        "$VENV/bin/python" manage.py changepassword ADMIN001
    else
        echo "IMPORTANT: change ADMIN001's public default password now:"
        echo "  cd $BACKEND && $VENV/bin/python manage.py changepassword ADMIN001"
    fi
fi

# --- 7. First administrator ---------------------------------------------------
ADMINS="$("$VENV/bin/python" manage.py shell -c "from core.models import User; print(User.objects.filter(role='admin').count())" 2>/dev/null | tail -1)"
if [ "${ADMINS:-0}" = "0" ]; then
    step "Creating the first administrator"
    if [ -t 0 ]; then
        echo "Pick a Student ID (e.g. ADMIN001) and a strong password; you'll type it in the IC/Passport field when signing in."
        "$VENV/bin/python" manage.py createsuperuser
    else
        echo "No admin yet. Run: cd $BACKEND && $VENV/bin/python manage.py createsuperuser"
    fi
fi

# --- 8. WSGI file + reload ----------------------------------------------------
step "Web app"
if [ -f "$WSGI_FILE" ]; then
    [ -f "$WSGI_FILE.orig" ] || cp "$WSGI_FILE" "$WSGI_FILE.orig"
    cat > "$WSGI_FILE" <<PYWSGI
# ASSAS on PythonAnywhere - written by deploy/pythonanywhere/setup.sh
import os
import sys

path = '$BACKEND'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'assas_backend.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
PYWSGI
    touch "$WSGI_FILE"   # touching the WSGI file reloads the site
    echo "Updated $WSGI_FILE and reloaded the site."
    echo
    echo "Done: https://$DOMAIN"
else
    echo "The web app doesn't exist yet. On the Web tab:"
    echo "  1. Add a new web app -> Next -> Manual configuration -> Python $PY_VERSION"
    echo "  2. Then re-run:  bash $APP_DIR/deploy/pythonanywhere/setup.sh"
fi

cat <<NOTE

On the Web tab, make sure these are set (then click Reload once):
  Source code:  $BACKEND
  Virtualenv:   $VENV
  Static files: URL /static/  ->  $BACKEND/staticfiles
                (no mapping for /media/ - photos must stay behind sign-in)
  Security:     Force HTTPS = on
NOTE
