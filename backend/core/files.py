"""Views that serve files rather than JSON: uploaded media behind a login,
and the built React app's index.html for client-side routes."""
import posixpath

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.utils._os import safe_join
from django.views.decorators.http import require_safe


def _may_view(user, path):
    if user.role == 'admin':
        return True
    top = path.split('/', 1)[0]
    if top == 'timetables':
        return True
    if top == 'student_photos':
        profile = getattr(user, 'student_profile', None)
        return bool(profile and profile.photo and profile.photo.name == path)
    return False


@require_safe
def protected_media(request, path):
    """Student photos and timetable files are personal or internal, so they
    are only served to signed-in users: admins see everything, students see
    timetables and their own photo. Anything else is a 404, so the response
    doesn't reveal whether someone else's file exists."""
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Sign in to view this file.')

    path = posixpath.normpath(path).lstrip('/')
    if path.startswith('..') or not _may_view(request.user, path):
        raise Http404

    try:
        full_path = safe_join(settings.MEDIA_ROOT, path)
        response = FileResponse(open(full_path, 'rb'))
    except (SuspiciousFileOperation, FileNotFoundError, IsADirectoryError):
        raise Http404
    response['Cache-Control'] = 'private, max-age=3600'
    return response


@require_safe
def spa_index(request):
    """Every non-API URL (/, /login, /student/profile, ...) returns the React
    app; React Router then renders the right page. WhiteNoise serves the
    app's actual files (/assets/*, images) before this view is reached."""
    index = settings.FRONTEND_DIST / 'index.html'
    if not index.is_file():
        return HttpResponse(
            'Frontend build not found. Run `npm run build` in frontend/, or use the Vite dev server.',
            status=404, content_type='text/plain',
        )
    response = HttpResponse(index.read_bytes(), content_type='text/html; charset=utf-8')
    response['Cache-Control'] = 'no-cache'
    return response
