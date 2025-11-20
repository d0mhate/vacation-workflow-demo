from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import path, include


def serve_spa(request):
    index_path = Path(settings.BASE_DIR) / 'static' / 'index.html'
    if index_path.exists():
        return FileResponse(open(index_path, 'rb'))
    raise Http404("index.html not found")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('vacation_app.urls')),
    path('', serve_spa),
]
