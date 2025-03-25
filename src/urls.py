from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from src.jobs import views as job_views
from src.applications import views as application_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Job posting URLs
    path('jobs/', job_views.job_list, name='job_list'),
    path('jobs/create/', job_views.job_create, name='job_create'),
    path('jobs/<slug:slug>/', job_views.job_detail, name='job_detail'),
    path('jobs/<slug:slug>/edit/', job_views.job_edit, name='job_edit'),
    path('jobs/<slug:slug>/delete/', job_views.job_delete, name='job_delete'),

    # Job application URLs
    path('applications/', application_views.application_list, name='application_list'),
    path('applications/<int:pk>/', application_views.application_detail, name='application_detail'),
    path('applications/<int:pk>/edit/', application_views.application_edit, name='application_edit'),
    path('jobs/<slug:job_slug>/apply/', application_views.application_create, name='application_create'),
    path('applications/<int:application_pk>/documents/add/', application_views.document_create, name='document_create'),
    path('documents/<int:pk>/delete/', application_views.document_delete, name='document_delete'),

    # Authentication URLs
    path('accounts/', include('src.accounts.urls', namespace='accounts')),
    path('', include('social_django.urls', namespace='social')),

    # Home page
    path('', job_views.job_list, name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
