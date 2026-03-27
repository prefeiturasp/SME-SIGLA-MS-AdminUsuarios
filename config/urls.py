from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView
from usuarios.views import SwaggerFromFileView


def healthcheck(_request):
    return JsonResponse({"status": "ok"})


_core_urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('usuarios.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SwaggerFromFileView.as_view(url_name='schema'), name='swagger-ui'),
    path('', healthcheck, name='healthcheck'),
]

_static_urlpatterns = (
    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
)

if getattr(settings, 'DJANGO_ENVIRONMENT', 'local') != 'local':
    _ms_prefix = (getattr(settings, 'MS_PATH', '') or '/ms-admin-usuarios').strip('/')
    urlpatterns = [
        path(f'{_ms_prefix}/', include(_core_urlpatterns + _static_urlpatterns)),
    ]
else:
    urlpatterns = _core_urlpatterns + _static_urlpatterns
