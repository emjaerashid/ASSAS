from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from core.files import protected_media, spa_index

urlpatterns = [
    path('api/', include('core.urls')),
    re_path(r'^media/(?P<path>.+)$', protected_media, name='protected-media'),
]

if settings.ENABLE_DJANGO_ADMIN:
    urlpatterns.append(path('django-admin/', admin.site.urls))

# Anything else is a client-side route of the React app.
urlpatterns.append(re_path(r'^(?!api/|media/|static/|django-admin/).*$', spa_index, name='spa'))
