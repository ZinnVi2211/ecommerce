from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from shops import views as shop_views

urlpatterns = [
    path('admin/dashboard/', shop_views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/dashboard/api/', shop_views.dashboard_api, name='admin_dashboard_api'),
    path('admin/', admin.site.urls),
    path('users/', include(('users.urls', 'users'))),
    path('shops/', include(('shops.urls', 'shops'))),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
