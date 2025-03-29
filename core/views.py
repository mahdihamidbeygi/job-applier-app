import io
import logging
import pdfminer.high_level
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from datetime import datetime, date
from django.views.generic import TemplateView
import json
from io import BytesIO
import base64
from reportlab.pdfgen import canvas

from .models import (
    UserProfile, WorkExperience, Project, Education,
    Certification, Publication, Skill
)
from .forms import (
    UserProfileForm, WorkExperienceForm, ProjectForm,
    EducationForm, CertificationForm, PublicationForm, SkillForm
)
from .serializers import (
    UserProfileSerializer, WorkExperienceSerializer, ProjectSerializer,
    EducationSerializer, CertificationSerializer, PublicationSerializer,
    SkillSerializer, ProfileSerializer
)
from .utils.profile_importers import GitHubProfileImporter, ResumeImporter, LinkedInImporter
from .utils.resume_composition import ResumeComposition
from .utils.cover_letter_composition import CoverLetterComposition
from .utils.local_llms import OllamaClient
from .utils.agents import PersonalAgent, PersonalBackground
from .utils.agents.application_agent import ApplicationAgent
from .utils.agents.search_agent import SearchAgent

logger = logging.getLogger(__name__)

def home(request):
    """Home page view"""
    return render(request, 'core/home.html')

@login_required
def profile(request):
    """User profile view"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if form.is_valid():
            profile = form.save(commit=False)
            
            # Handle resume upload and parsing
            if 'resume' in request.FILES:
                resume_file = request.FILES['resume']
                try:
                    logger.info(f"Attempting to upload file: {resume_file.name}")
                    file_path = f'resumes/{request.user.username}/{resume_file.name}'
                    saved_path = default_storage.save(file_path, resume_file)
                    file_url = default_storage.url(saved_path)
                    logger.info(f"File uploaded successfully. URL: {file_url}")
                    
                    if resume_file.name.endswith('.pdf'):
                        text = parse_pdf_resume(resume_file)
                        profile.parsed_resume_data = {
                            'raw_text': text,
                            'file_url': file_url
                        }
                    
                    messages.success(request, 'Resume uploaded successfully!')
                except Exception as e:
                    logger.error(f"Error uploading file: {str(e)}")
                    messages.error(request, f'Error uploading resume: {str(e)}')
            
            profile.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('core:profile')
    else:
        form = UserProfileForm(instance=request.user.userprofile)
    
    context = {
        'form': form,
        'user_profile': request.user.userprofile,
        'work_experiences': request.user.userprofile.work_experiences.all(),
        'projects': request.user.userprofile.projects.all(),
        'education': request.user.userprofile.education.all(),
        'certifications': request.user.userprofile.certifications.all(),
        'publications': request.user.userprofile.publications.all(),
        'skills': request.user.userprofile.skills.all(),
        'work_experience_form': WorkExperienceForm(),
        'project_form': ProjectForm(),
        'education_form': EducationForm(),
        'certification_form': CertificationForm(),
        'publication_form': PublicationForm(),
        'skill_form': SkillForm(),
    }
    return render(request, 'core/profile.html', context)

@login_required
@require_POST
def add_work_experience(request):
    """Add work experience"""
    form = WorkExperienceForm(request.POST)
    if form.is_valid():
        experience = form.save(commit=False)
        experience.profile = request.user.userprofile
        experience.save()
        messages.success(request, 'Work experience added successfully!')
    else:
        messages.error(request, 'Error adding work experience.')
    return redirect('core:profile')

@login_required
@require_POST
def add_project(request):
    """Add project"""
    form = ProjectForm(request.POST)
    if form.is_valid():
        project = form.save(commit=False)
        project.profile = request.user.userprofile
        project.save()
        messages.success(request, 'Project added successfully!')
    else:
        messages.error(request, 'Error adding project.')
    return redirect('core:profile')

@login_required
@require_POST
def add_education(request):
    """Add education"""
    form = EducationForm(request.POST)
    if form.is_valid():
        education = form.save(commit=False)
        education.profile = request.user.userprofile
        education.save()
        messages.success(request, 'Education added successfully!')
    else:
        messages.error(request, 'Error adding education.')
    return redirect('core:profile')

@login_required
@require_POST
def add_certification(request):
    """Add certification"""
    form = CertificationForm(request.POST)
    if form.is_valid():
        certification = form.save(commit=False)
        certification.profile = request.user.userprofile
        certification.save()
        messages.success(request, 'Certification added successfully!')
    else:
        messages.error(request, 'Error adding certification.')
    return redirect('core:profile')

@login_required
@require_POST
def add_publication(request):
    """Add publication"""
    form = PublicationForm(request.POST)
    if form.is_valid():
        publication = form.save(commit=False)
        publication.profile = request.user.userprofile
        publication.save()
        messages.success(request, 'Publication added successfully!')
    else:
        messages.error(request, 'Error adding publication.')
    return redirect('core:profile')

@login_required
@require_POST
def add_skill(request):
    """Add skill"""
    form = SkillForm(request.POST)
    if form.is_valid():
        skill = form.save(commit=False)
        skill.profile = request.user.userprofile
        skill.save()
        messages.success(request, 'Skill added successfully!')
    else:
        messages.error(request, 'Error adding skill.')
    return redirect('core:profile')

@login_required
def delete_item(request, model_name, item_id):
    """Delete an item from any model"""
    model_map = {
        'work_experience': WorkExperience,
        'project': Project,
        'education': Education,
        'certification': Certification,
        'publication': Publication,
        'skill': Skill,
    }
    
    model = model_map.get(model_name)
    if model:
        item = get_object_or_404(model, id=item_id, profile=request.user.userprofile)
        item.delete()
        messages.success(request, f'{model_name.replace("_", " ").title()} deleted successfully!')
    else:
        messages.error(request, 'Invalid model specified.')
    
    return redirect('core:profile')

def parse_pdf_resume(pdf_file):
    """Parse PDF resume and extract text"""
    text = ''
    pdf_file_obj = io.BytesIO(pdf_file.read())
    
    try:
        text = pdfminer.high_level.extract_text(pdf_file_obj)
    except Exception as e:
        print(f"Error parsing PDF: {str(e)}")
    
    return text

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Account created successfully!')
            return redirect('core:login')
    else:
        form = UserCreationForm()
    return render(request, 'core/register.html', {'form': form})

def test_s3(request):
    """Test S3 connectivity"""
    try:
        test_content = b"This is a test file"
        path = default_storage.save('test.txt', ContentFile(test_content))
        url = default_storage.url(path)
        default_storage.delete(path)
        
        return JsonResponse({
            'status': 'success',
            'message': 'S3 connection successful',
            'test_url': url
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

# API Views
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.profile.user == request.user

class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['city', 'state', 'country']
    search_fields = ['headline', 'professional_summary', 'current_position', 'company']
    ordering_fields = ['years_of_experience', 'created_at', 'updated_at']

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='include_related', type=OpenApiTypes.BOOL, description='Include related data')
        ]
    )
    @action(detail=True, methods=['get'])
    def full_profile(self, request, pk=None):
        profile = self.get_object()
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        profile = self.get_queryset().first()
        if not profile:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        stats = {
            'total_experience': profile.work_experiences.count(),
            'total_projects': profile.projects.count(),
            'total_skills': profile.skills.count(),
            'total_certifications': profile.certifications.count(),
            'total_publications': profile.publications.count(),
        }
        return Response(stats)

class WorkExperienceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkExperienceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['company', 'position', 'location', 'current']
    search_fields = ['company', 'position', 'description', 'technologies']
    ordering_fields = ['start_date', 'end_date', 'created_at']

    def get_queryset(self):
        return WorkExperience.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=['get'])
    def current_position(self, request):
        current = self.get_queryset().filter(current=True).first()
        if not current:
            return Response({'error': 'No current position found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(current)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_company(self, request):
        company = request.query_params.get('company')
        if not company:
            return Response({'error': 'Company parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        experiences = self.get_queryset().filter(company__icontains=company)
        serializer = self.get_serializer(experiences, many=True)
        return Response(serializer.data)

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['technologies']
    search_fields = ['title', 'description', 'technologies']
    ordering_fields = ['start_date', 'end_date', 'created_at']

    def get_queryset(self):
        return Project.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=['get'])
    def by_technology(self, request):
        technology = request.query_params.get('technology')
        if not technology:
            return Response({'error': 'Technology parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        projects = self.get_queryset().filter(technologies__icontains=technology)
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)

class EducationViewSet(viewsets.ModelViewSet):
    serializer_class = EducationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['institution', 'degree', 'field_of_study', 'current']
    search_fields = ['institution', 'degree', 'field_of_study', 'achievements']
    ordering_fields = ['start_date', 'end_date', 'gpa', 'created_at']

    def get_queryset(self):
        return Education.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=['get'])
    def by_institution(self, request):
        institution = request.query_params.get('institution')
        if not institution:
            return Response({'error': 'Institution parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        education = self.get_queryset().filter(institution__icontains=institution)
        serializer = self.get_serializer(education, many=True)
        return Response(serializer.data)

class CertificationViewSet(viewsets.ModelViewSet):
    serializer_class = CertificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['issuer']
    search_fields = ['name', 'issuer', 'credential_id']
    ordering_fields = ['issue_date', 'expiry_date', 'created_at']

    def get_queryset(self):
        return Certification.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=['get'])
    def by_issuer(self, request):
        issuer = request.query_params.get('issuer')
        if not issuer:
            return Response({'error': 'Issuer parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        certifications = self.get_queryset().filter(issuer__icontains=issuer)
        serializer = self.get_serializer(certifications, many=True)
        return Response(serializer.data)

class PublicationViewSet(viewsets.ModelViewSet):
    serializer_class = PublicationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['publisher', 'journal']
    search_fields = ['title', 'authors', 'abstract', 'doi']
    ordering_fields = ['publication_date', 'created_at']

    def get_queryset(self):
        return Publication.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=['get'])
    def by_publisher(self, request):
        publisher = request.query_params.get('publisher')
        if not publisher:
            return Response({'error': 'Publisher parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        publications = self.get_queryset().filter(publisher__icontains=publisher)
        serializer = self.get_serializer(publications, many=True)
        return Response(serializer.data)

class SkillViewSet(viewsets.ModelViewSet):
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'proficiency']
    search_fields = ['name', 'category']
    ordering_fields = ['proficiency', 'created_at']

    def get_queryset(self):
        return Skill.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category = request.query_params.get('category')
        if not category:
            return Response({'error': 'Category parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        skills = self.get_queryset().filter(category=category)
        serializer = self.get_serializer(skills, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_proficiency(self, request):
        proficiency = request.query_params.get('proficiency')
        if not proficiency:
            return Response({'error': 'Proficiency parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        skills = self.get_queryset().filter(proficiency=proficiency)
        serializer = self.get_serializer(skills, many=True)
        return Response(serializer.data)

@require_http_methods(["POST"])
def import_github_profile(request):
    """Import profile data from GitHub."""
    try:
        data = json.loads(request.body)
        github_username = data.get('github_username')
        
        if not github_username:
            return JsonResponse({'error': 'GitHub username is required'}, status=400)
        
        importer = GitHubProfileImporter(github_username)
        profile_data = json.loads(importer.import_profile())
        
        # Save work experiences
        for exp in profile_data.get('work_experiences', []):
            WorkExperience.objects.create(
                profile=request.user.userprofile,
                company=exp['company'],
                position=exp['position'],
                start_date=exp['start_date'],
                end_date=exp['end_date'],
                description=exp['description'],
                technologies=exp['technologies']
            )
        
        # Save skills
        for skill in profile_data.get('skills', []):
            Skill.objects.create(
                profile=request.user.userprofile,
                name=skill['name'],
                category=skill['category'],
                proficiency=skill['proficiency']
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Profile imported successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
def import_resume(request):
    """Import profile data from uploaded resume."""
    try:
        if 'resume' not in request.FILES:
            return JsonResponse({'error': 'No resume file uploaded'}, status=400)
        
        resume_file = request.FILES['resume']
        importer = ResumeImporter(resume_file)
        profile_data = importer.parse_resume()
        
        # Save the raw text and personal info to the user's profile
        user_profile = request.user.userprofile
        user_profile.parsed_resume_data = profile_data
        
        # Update personal information
        personal_info = profile_data.get('personal_info', {})
        user_profile.phone = personal_info.get('phone', '')
        user_profile.address = personal_info.get('address', '')
        user_profile.city = personal_info.get('city', '')
        user_profile.state = personal_info.get('state', '')
        user_profile.country = personal_info.get('country', '')
        user_profile.postal_code = personal_info.get('postal_code', '')
        user_profile.website = personal_info.get('website', '')
        user_profile.linkedin = personal_info.get('linkedin', '')
        user_profile.github = personal_info.get('github', '')
        
        # Update professional summary if available
        if personal_info.get('name'):
            user_profile.headline = personal_info['name']
        
        user_profile.save()
        
        # Save work experiences
        for exp in profile_data.get('work_experiences', []):
            # Skip if no start date
            if not exp.get('start_date'):
                continue
                
            try:
                # Parse dates if they're strings
                start_date = exp.get('start_date')
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                
                end_date = exp.get('end_date')
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                WorkExperience.objects.create(
                    profile=request.user.userprofile,
                    company=exp.get('company', ''),
                    position=exp.get('position', ''),
                    start_date=start_date,
                    end_date=end_date,
                    current=exp.get('current', False),
                    description=exp.get('description', ''),
                    technologies=exp.get('technologies', [])
                )
            except (ValueError, TypeError):
                # Skip this experience if date parsing fails
                continue
        
        # Save education
        for edu in profile_data.get('education', []):
            try:
                # Parse GPA if it exists and is numeric
                gpa_str = edu.get('gpa')
                gpa = None
                if gpa_str:
                    try:
                        gpa = float(gpa_str)
                        # Ensure GPA is within valid range (0-4.0)
                        if gpa < 0 or gpa > 4.0:
                            gpa = None
                    except (ValueError, TypeError):
                        gpa = None

                # Parse dates
                start_date = edu.get('start_date')
                if isinstance(start_date, str):
                    try:
                        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    except ValueError:
                        start_date = None

                end_date = edu.get('end_date')
                if isinstance(end_date, str):
                    try:
                        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                    except ValueError:
                        end_date = None

                Education.objects.create(
                    profile=request.user.userprofile,
                    institution=edu.get('institution', ''),
                    degree=edu.get('degree', ''),
                    field_of_study=edu.get('field_of_study', ''),
                    start_date=start_date,
                    end_date=end_date,
                    gpa=gpa,
                    achievements=edu.get('achievements', [])
                )
            except Exception as e:
                # Log the error but continue processing other education entries
                logger.error(f"Error creating education entry: {str(e)}")
                continue
        
        # Save skills
        for skill in profile_data.get('skills', []):
            Skill.objects.create(
                profile=request.user.userprofile,
                name=skill.get('name', ''),
                category=skill.get('category', ''),
                proficiency=skill.get('proficiency', 3)
            )
        
        # Save certifications
        for cert in profile_data.get('certifications', []):
            Certification.objects.create(
                profile=request.user.userprofile,
                name=cert.get('name', ''),
                issuer=cert.get('issuer', ''),
                issue_date=cert.get('issue_date'),
                expiry_date=cert.get('expiry_date'),
                credential_id=cert.get('credential_id')
            )
        
        # Save projects
        for proj in profile_data.get('projects', []):
            Project.objects.create(
                profile=request.user.userprofile,
                title=proj.get('title', ''),
                description=proj.get('description', ''),
                start_date=proj.get('start_date'),
                end_date=proj.get('end_date'),
                technologies=proj.get('technologies', [])
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Profile imported successfully',
            'data': profile_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
def import_linkedin_profile(request):
    """Import profile data from LinkedIn."""
    try:
        data = json.loads(request.body)
        linkedin_url = data.get('linkedin_url')
        
        if not linkedin_url:
            return JsonResponse({'error': 'LinkedIn URL is required'}, status=400)
        
        importer = LinkedInImporter(linkedin_url)
        profile_data = json.loads(importer.parse_profile())
        
        # Save work experiences
        for exp in profile_data.get('work_experiences', []):
            WorkExperience.objects.create(
                profile=request.user.userprofile,
                company=exp['company'],
                position=exp['position'],
                start_date=exp['start_date'],
                end_date=exp['end_date'],
                description=exp['description'],
                technologies=exp['technologies']
            )
        
        # Save education
        for edu in profile_data.get('education', []):
            Education.objects.create(
                profile=request.user.userprofile,
                institution=edu['institution'],
                degree=edu['degree'],
                field_of_study=edu['field_of_study'],
                start_date=edu['start_date'],
                end_date=edu['end_date'],
                gpa=edu.get('gpa'),
                achievements=edu.get('achievements', [])
            )
        
        # Save skills
        for skill in profile_data.get('skills', []):
            Skill.objects.create(
                profile=request.user.userprofile,
                name=skill['name'],
                category=skill['category'],
                proficiency=skill['proficiency']
            )
        
        # Save certifications
        for cert in profile_data.get('certifications', []):
            Certification.objects.create(
                profile=request.user.userprofile,
                name=cert['name'],
                issuer=cert['issuer'],
                issue_date=cert['issue_date'],
                expiry_date=cert.get('expiry_date'),
                credential_id=cert.get('credential_id')
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Profile imported successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
@login_required
def bulk_delete_records(request):
    """Handle bulk deletion of resume records."""
    try:
        data = json.loads(request.body)
        record_type = data.get('record_type')
        record_ids = data.get('record_ids', [])
        
        if not record_type or not record_ids:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        # Map record types to their models
        model_map = {
            'work_experience': WorkExperience,
            'education': Education,
            'project': Project,
            'certification': Certification,
            'publication': Publication,
            'skill': Skill
        }
        
        if record_type not in model_map:
            return JsonResponse({'error': 'Invalid record type'}, status=400)
        
        model = model_map[record_type]
        deleted_count = model.objects.filter(
            profile=request.user.userprofile,
            id__in=record_ids
        ).delete()[0]
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully deleted {deleted_count} records',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        logger.error(f"Error in bulk delete: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
@login_required
def edit_record(request, record_type, record_id):
    """Handle editing of a record."""
    try:
        data = json.loads(request.body)
        
        # Map record types to their models
        model_map = {
            'work_experience': WorkExperience,
            'education': Education,
            'project': Project,
            'certification': Certification,
            'publication': Publication,
            'skill': Skill
        }
        
        if record_type not in model_map:
            return JsonResponse({'error': 'Invalid record type'}, status=400)
        
        model = model_map[record_type]
        record = model.objects.filter(
            profile=request.user.userprofile,
            id=record_id
        ).first()
        
        if not record:
            return JsonResponse({'error': 'Record not found'}, status=404)
        
        # Update record fields
        for field, value in data.items():
            if hasattr(record, field):
                if field in ['start_date', 'end_date', 'issue_date', 'expiry_date', 'publication_date']:
                    try:
                        value = datetime.strptime(value, '%b %Y').date()
                    except ValueError:
                        continue
                elif field == 'technologies':
                    value = value.split(',') if value else []
                setattr(record, field, value)
        
        record.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Record updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in edit record: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_profile_stats(request):
    """Get current profile statistics"""
    profile = request.user.userprofile
    stats = {
        'work_experience': profile.work_experiences.count(),
        'projects': profile.projects.count(),
        'skills': profile.skills.count(),
        'certifications': profile.certifications.count(),
        'years_of_experience': profile.years_of_experience
    }
    return JsonResponse(stats)

@method_decorator(login_required, name='dispatch')
class ManualSubmissionView(TemplateView):
    template_name = 'core/manual_submission.html'

@login_required
@require_http_methods(["POST"])
def generate_documents(request):
    try:
        data = json.loads(request.body)
        job_description = data.get('job_description')
        document_type = data.get('document_type')
        
        if not job_description or not document_type:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
            
        if document_type not in ['resume', 'cover_letter']:
            return JsonResponse({'error': 'Invalid document type'}, status=400)
            
        # Create a buffer to store the PDF
        buffer = BytesIO()
        
        try:
            if document_type == 'resume': 
                # Create resume composition with user data
                resume = ResumeComposition(request.user.userprofile)
                # Build the resume
                resume.build(buffer, job_description)
                
                # Get the value of the BytesIO buffer and write it to the response
                pdf = buffer.getvalue()
                buffer.close()
                
                # Create response
                response = HttpResponse(pdf, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{request.user.username}_resume_{date.today().strftime("%Y%m%d")}.pdf"'
                return response
                
            elif document_type == 'cover_letter':
                # Create cover letter using CoverLetterComposition
                cover_letter_composer = CoverLetterComposition(request.user.userprofile, job_description)
                buffer = cover_letter_composer.build()
                cover_letter_bytes = buffer.getvalue()
                buffer.close()
                
                # Encode cover letter bytes in base64
                response_data = {
                    'documents': {
                        'cover_letter': base64.b64encode(cover_letter_bytes).decode('utf-8')
                    }
                }
                
                return JsonResponse(response_data)
        except Exception as e:
            logger.error(f"Error generating {document_type}: {str(e)}")
            return JsonResponse({'error': f'Error generating {document_type}: {str(e)}'}, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in generate_documents: {str(e)}")
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)

@require_http_methods(["POST"])
@login_required
def generate_answers(request):
    """Generate answers for application questions using Ollama."""
    try:
        data = json.loads(request.body)
        job_description = data.get('job_description')
        questions = data.get('questions')

        if not job_description or not questions:
            return JsonResponse({'error': 'Job description and questions are required'}, status=400)

        # Get user profile information
        user_profile = request.user.userprofile
        
        # Format user's background information
        work_experiences = []
        if user_profile.work_experiences.exists():
            for exp in user_profile.work_experiences.all():
                work_experiences.append({
                    'company': exp.company,
                    'position': exp.position,
                    'start_date': exp.start_date.strftime('%Y-%m-%d') if exp.start_date else None,
                    'end_date': exp.end_date.strftime('%Y-%m-%d') if exp.end_date else None,
                    'current': exp.current,
                    'description': exp.description,
                    'technologies': exp.technologies
                })

        skills = []
        if user_profile.skills.exists():
            for skill in user_profile.skills.all():
                skills.append({
                    'name': skill.name,
                    'category': skill.category,
                    'proficiency': skill.proficiency
                })

        projects = []
        if user_profile.projects.exists():
            for proj in user_profile.projects.all():
                projects.append({
                    'title': proj.title,
                    'description': proj.description,
                    'technologies': proj.technologies,
                    'start_date': proj.start_date.strftime('%Y-%m-%d') if proj.start_date else None,
                    'end_date': proj.end_date.strftime('%Y-%m-%d') if proj.end_date else None
                })

        # Create prompt for Ollama
        prompt = f"""you are excellent at writing cover letters and resumes.
        Based on the following job description and candidate's background, provide a brief answer (2-3 sentences) in JSON format to the question.

Job Description:
{job_description}

Candidate Information:
- Name: {user_profile.user.get_full_name() or user_profile.user.username}
- Professional Summary: {user_profile.professional_summary or 'Not provided'}
- Current Position: {user_profile.current_position or 'Not specified'}
- Years of Experience: {user_profile.years_of_experience or 'Not specified'}

Work Experience:
{json.dumps(work_experiences, indent=2)}

Skills:
{json.dumps(skills, indent=2)}

Projects:
{json.dumps(projects, indent=2)}

Application Questions:
{questions}

Please provide a brief paragraph (2-3 sentences) in JSON format to each question. 
if there are multiple questions, please provide a JSON object for all questions.
the main key is "response" and the value is only string of the questions and answers just like example. 
E.X.: {{"response": "Question1 : answer1,\n Question2 : answer2"}} """

        # Initialize Ollama client and generate answers
        ollama_client = OllamaClient(model="phi4:latest", temperature=0.0)
        answers = ollama_client.generate(prompt)

        return JsonResponse({'answers': answers})

    except Exception as e:
        logger.error(f"Error generating answers: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def process_job_application(request):
    try:
        data = json.loads(request.body)
        job_description = data.get('job_description')
        questions = data.get('questions', [])
        document_type = data.get('document_type', 'all')  # 'resume', 'cover_letter', or 'all'
        
        if not job_description:
            return JsonResponse({'error': 'Missing job description'}, status=400)
        
        # Initialize agents
        personal_agent = PersonalAgent(request.user.id)
        
        # Load user background
        background = PersonalBackground(
            profile=request.user.userprofile.__dict__,
            work_experience=list(request.user.userprofile.work_experiences.values()),
            education=list(request.user.userprofile.education.values()),
            skills=list(request.user.userprofile.skills.values()),
            projects=list(request.user.userprofile.projects.values()),
            github_data={
                'repositories': [],
                'contributions': 0,
                'languages': []
            },
            achievements=[],  # We'll add this field to the model later
            interests=[]     # We'll add this field to the model later
        )
        personal_agent.load_background(background)
        
        # Initialize application agent
        application_agent = ApplicationAgent(request.user.id, personal_agent)
        
        # Initialize search agent for job analysis
        search_agent = SearchAgent(request.user.id, personal_agent)
        
        # Analyze job fit
        job_analysis = search_agent.analyze_job_fit({
            'description': job_description
        })
        
        response_data = {
            'job_analysis': json.loads(job_analysis),
            'documents': {},
            'answers': []
        }

        # Generate requested documents
        if document_type in ['resume', 'all']:
            resume_buffer = BytesIO()
            resume = ResumeComposition(personal_agent)
            resume.build(resume_buffer, job_description)
            resume_bytes = resume_buffer.getvalue()
            resume_buffer.close()
            # Encode resume bytes in base64
            response_data['documents']['resume'] = base64.b64encode(resume_bytes).decode('utf-8')
        
        if document_type in ['cover_letter', 'all']:
            # Create cover letter using CoverLetterComposition
            cover_letter_composer = CoverLetterComposition(request.user.userprofile, job_description)
            buffer = cover_letter_composer.build()
            cover_letter_bytes = buffer.getvalue()
            buffer.close()
            
            # Encode cover letter bytes in base64
            response_data['documents']['cover_letter'] = base64.b64encode(cover_letter_bytes).decode('utf-8')
        
        # Handle application questions if provided
        if questions:
            answers = application_agent.handle_screening_questions(questions, job_description)
            response_data['answers'] = answers
        
        # Add interview preparation if requested
        if data.get('include_interview_prep', False):
            interview_prep = application_agent.prepare_interview_responses(job_description)
            response_data['interview_prep'] = json.loads(interview_prep)
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error processing job application: {str(e)}")
        return JsonResponse({'error': f'Error processing application: {str(e)}'}, status=500)
