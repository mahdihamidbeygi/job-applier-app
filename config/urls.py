from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('job_applier.core.urls')),
    path('users/', include('job_applier.users.urls')),
    path('profiles/', include('job_applier.profiles.urls')),
    path('jobs/', include('job_applier.jobs.urls')),
    path('applications/', include('job_applier.applications.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('social_django.urls', namespace='social')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path('__debug__/', include('debug_toolbar.urls'))] 