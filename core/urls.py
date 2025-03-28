from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from . import views

app_name = 'core'

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'profiles', views.UserProfileViewSet, basename='profile')
router.register(r'work-experiences', views.WorkExperienceViewSet, basename='work-experience')
router.register(r'projects', views.ProjectViewSet, basename='project')
router.register(r'education', views.EducationViewSet, basename='education')
router.register(r'certifications', views.CertificationViewSet, basename='certification')
router.register(r'publications', views.PublicationViewSet, basename='publication')
router.register(r'skills', views.SkillViewSet, basename='skill')

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('profile/stats/', views.get_profile_stats, name='profile_stats'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='core:home'), name='logout'),
    path('register/', views.register, name='register'),
    path('test-s3/', views.test_s3, name='test_s3'),
    
    # Add new items
    path('profile/add-work-experience/', views.add_work_experience, name='add_work_experience'),
    path('profile/add-project/', views.add_project, name='add_project'),
    path('profile/add-education/', views.add_education, name='add_education'),
    path('profile/add-certification/', views.add_certification, name='add_certification'),
    path('profile/add-publication/', views.add_publication, name='add_publication'),
    path('profile/add-skill/', views.add_skill, name='add_skill'),
    
    # Delete items
    path('profile/delete/<str:model_name>/<int:item_id>/', views.delete_item, name='delete_item'),
    
    # Profile import URLs
    path('profile/import/github/', views.import_github_profile, name='import_github_profile'),
    path('profile/import/resume/', views.import_resume, name='import_resume'),
    path('profile/import/linkedin/', views.import_linkedin_profile, name='import_linkedin_profile'),
    
    # API endpoints
    path('api/', include(router.urls)),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='core:schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='core:schema'), name='redoc'),
    path('import-resume/', views.import_resume, name='import_resume'),
    path('bulk-delete-records/', views.bulk_delete_records, name='bulk_delete_records'),
    path('profile/edit/<str:record_type>/<int:record_id>/', views.edit_record, name='edit_record'),
    path('manual-submission/', views.ManualSubmissionView.as_view(), name='manual_submission'),
    path('api/generate-documents/', views.generate_documents, name='generate_documents'),
    path('api/generate-answers/', views.generate_answers, name='generate_answers'),
] 