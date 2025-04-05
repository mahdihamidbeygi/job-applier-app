import base64
import io
import json
import logging
from datetime import date, datetime
from io import BytesIO

import pdfminer.high_level
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import (
    HttpResponse,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import TemplateView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from core.forms import (
    CertificationForm,
    EducationForm,
    JobPlatformPreferenceForm,
    ProjectForm,
    PublicationForm,
    SkillForm,
    UserProfileForm,
    WorkExperienceForm,
)
from core.models import (
    Certification,
    Education,
    JobListing,
    JobPlatformPreference,
    Project,
    Publication,
    Skill,
    UserProfile,
    WorkExperience,
)
from core.serializers import (
    CertificationSerializer,
    EducationSerializer,
    ProfileSerializer,
    ProjectSerializer,
    PublicationSerializer,
    SkillSerializer,
    UserProfileSerializer,
    WorkExperienceSerializer,
)
from core.tasks import generate_documents_async
from core.utils.agents.application_agent import ApplicationAgent
from core.utils.agents.personal_agent import PersonalAgent, PersonalBackground
from core.utils.agents.search_agent import SearchAgent
from core.utils.cover_letter_composition import CoverLetterComposition
from core.utils.local_llms import OllamaClient
from core.utils.profile_importers import GitHubProfileImporter, LinkedInImporter, ResumeImporter
from core.utils.resume_composition import ResumeComposition

logger = logging.getLogger(__name__)

__all__ = [
    "home",
    "profile",
    "register",
    "test_s3",
    "jobs_page",
    "job_detail",
    "job_apply",
    "generate_job_documents",
    "get_job_documents",
    "apply_to_job",
    "search_jobs",
    "job_platform_preferences",
    "remove_job",
    "deduplicate_skills",
]


def home(request):
    """Home page view"""
    return render(request, "core/home.html")


@login_required
def profile(request):
    """User profile view"""
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=request.user.userprofile)
        if form.is_valid():
            profile = form.save(commit=False)

            # Handle resume upload and parsing
            if "resume" in request.FILES:
                resume_file = request.FILES["resume"]
                try:
                    logger.info(f"Attempting to upload file: {resume_file.name}")
                    file_path = f"resumes/{request.user.username}/{resume_file.name}"
                    saved_path = default_storage.save(file_path, resume_file)
                    file_url = default_storage.url(saved_path)
                    logger.info(f"File uploaded successfully. URL: {file_url}")

                    if resume_file.name.endswith(".pdf"):
                        text = parse_pdf_resume(resume_file)
                        profile.parsed_resume_data = {"raw_text": text, "file_url": file_url}

                    messages.success(request, "Resume uploaded successfully!")
                except Exception as e:
                    logger.error(f"Error uploading file: {str(e)}")
                    messages.error(request, f"Error uploading resume: {str(e)}")

            profile.save()
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("core:profile")
    else:
        form = UserProfileForm(instance=request.user.userprofile)

    # Get GitHub data if it exists and needs to be refreshed
    github_data = request.user.userprofile.github_data
    if request.user.userprofile.github_url:
        if not github_data:
            # Extract username from GitHub URL
            github_url = request.user.userprofile.github_url
            github_username = github_url.split("/")[-1]
            if github_username == "github.com":
                github_username = github_url.split("/")[-2]

            # Import GitHub profile
            importer = GitHubProfileImporter(github_username)
            github_data = json.loads(importer.import_profile(github_username))
            
            # Transform repositories into projects
            projects = importer.transform_repos_to_projects(
                github_data.get("repositories", []),
                request.user.userprofile
            )

            # Save projects
            for project_data in projects:
                # Check if project already exists (based on GitHub URL)
                existing_project = Project.objects.filter(
                    profile=request.user.userprofile,
                    github_url=project_data['github_url']
                ).first()
                
                if existing_project:
                    # Update existing project
                    for key, value in project_data.items():
                        if key != 'profile':  # Skip updating the profile reference
                            setattr(existing_project, key, value)
                    existing_project.save()
                else:
                    # Create new project
                    Project.objects.create(**project_data)
            
            # Update last refresh time
            request.user.userprofile.github_data = github_data
            request.user.userprofile.last_github_refresh = timezone.now()
            request.user.userprofile.save()

    context = {
        "form": form,
        "user_profile": request.user.userprofile,
        "work_experiences": request.user.userprofile.work_experiences.all(),
        "projects": request.user.userprofile.projects.all(),
        "education": request.user.userprofile.education.all(),
        "certifications": request.user.userprofile.certifications.all(),
        "publications": request.user.userprofile.publications.all(),
        "skills": request.user.userprofile.skills.all(),
        "work_experience_form": WorkExperienceForm(),
        "project_form": ProjectForm(),
        "education_form": EducationForm(),
        "certification_form": CertificationForm(),
        "publication_form": PublicationForm(),
        "skill_form": SkillForm(),
        "github_data": github_data,
    }
    return render(request, "core/profile.html", context)


@login_required
@require_POST
def add_work_experience(request):
    """Add work experience"""
    form = WorkExperienceForm(request.POST)
    if form.is_valid():
        experience = form.save(commit=False)
        experience.profile = request.user.userprofile
        experience.save()
        messages.success(request, "Work experience added successfully!")
    else:
        messages.error(request, "Error adding work experience.")
    return redirect("core:profile")


@login_required
@require_POST
def add_project(request):
    """Add project"""
    form = ProjectForm(request.POST)
    if form.is_valid():
        project = form.save(commit=False)
        project.profile = request.user.userprofile
        project.save()
        messages.success(request, "Project added successfully!")
    else:
        messages.error(request, "Error adding project.")
    return redirect("core:profile")


@login_required
@require_POST
def add_education(request):
    """Add education"""
    form = EducationForm(request.POST)
    if form.is_valid():
        education = form.save(commit=False)
        education.profile = request.user.userprofile
        education.save()
        messages.success(request, "Education added successfully!")
    else:
        messages.error(request, "Error adding education.")
    return redirect("core:profile")


@login_required
@require_POST
def add_certification(request):
    """Add certification"""
    form = CertificationForm(request.POST)
    if form.is_valid():
        certification = form.save(commit=False)
        certification.profile = request.user.userprofile
        certification.save()
        messages.success(request, "Certification added successfully!")
    else:
        messages.error(request, "Error adding certification.")
    return redirect("core:profile")


@login_required
@require_POST
def add_publication(request):
    """Add publication"""
    form = PublicationForm(request.POST)
    if form.is_valid():
        publication = form.save(commit=False)
        publication.profile = request.user.userprofile
        publication.save()
        messages.success(request, "Publication added successfully!")
    else:
        messages.error(request, "Error adding publication.")
    return redirect("core:profile")


@login_required
@require_POST
def add_skill(request):
    """Add skill"""
    form = SkillForm(request.POST)
    if form.is_valid():
        skill = form.save(commit=False)
        skill.profile = request.user.userprofile
        skill.save()
        messages.success(request, "Skill added successfully!")
    else:
        messages.error(request, "Error adding skill.")
    return redirect("core:profile")


@login_required
def delete_item(request, model_name, item_id):
    """Delete an item from any model"""
    model_map = {
        "work_experience": WorkExperience,
        "project": Project,
        "education": Education,
        "certification": Certification,
        "publication": Publication,
        "skill": Skill,
    }

    model = model_map.get(model_name)
    if model:
        item = get_object_or_404(model, id=item_id, profile=request.user.userprofile)
        item.delete()
        messages.success(request, f'{model_name.replace("_", " ").title()} deleted successfully!')
    else:
        messages.error(request, "Invalid model specified.")

    return redirect("core:profile")


def parse_pdf_resume(pdf_file):
    """Parse PDF resume and extract text"""
    text = ""
    pdf_file_obj = io.BytesIO(pdf_file.read())

    try:
        text = pdfminer.high_level.extract_text(pdf_file_obj)
    except Exception as e:
        print(f"Error parsing PDF: {str(e)}")

    return text


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Account created successfully!")
            return redirect("core:login")
    else:
        form = UserCreationForm()
    return render(request, "core/register.html", {"form": form})


def test_s3(request):
    """Test S3 connectivity"""
    try:
        test_content = b"This is a test file"
        path = default_storage.save("test.txt", ContentFile(test_content))
        url = default_storage.url(path)
        default_storage.delete(path)

        return JsonResponse(
            {"status": "success", "message": "S3 connection successful", "test_url": url}
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


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
    filterset_fields = ["city", "state", "country"]
    search_fields = ["headline", "professional_summary", "current_position", "company"]
    ordering_fields = ["years_of_experience", "created_at", "updated_at"]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="include_related", type=OpenApiTypes.BOOL, description="Include related data"
            )
        ]
    )
    @action(detail=True, methods=["get"])
    def full_profile(self, request, pk=None):
        profile = self.get_object()
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        profile = self.get_queryset().first()
        if not profile:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

        stats = {
            "total_experience": profile.work_experiences.count(),
            "total_projects": profile.projects.count(),
            "total_skills": profile.skills.count(),
            "total_certifications": profile.certifications.count(),
            "total_publications": profile.publications.count(),
        }
        return Response(stats)


class WorkExperienceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkExperienceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["company", "position", "location", "current"]
    search_fields = ["company", "position", "description", "technologies"]
    ordering_fields = ["start_date", "end_date", "created_at"]

    def get_queryset(self):
        return WorkExperience.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def current_position(self, request):
        current = self.get_queryset().filter(current=True).first()
        if not current:
            return Response(
                {"error": "No current position found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(current)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_company(self, request):
        company = request.query_params.get("company")
        if not company:
            return Response(
                {"error": "Company parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        experiences = self.get_queryset().filter(company__icontains=company)
        serializer = self.get_serializer(experiences, many=True)
        return Response(serializer.data)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["technologies"]
    search_fields = ["title", "description", "technologies"]
    ordering_fields = ["start_date", "end_date", "created_at"]

    def get_queryset(self):
        return Project.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_technology(self, request):
        technology = request.query_params.get("technology")
        if not technology:
            return Response(
                {"error": "Technology parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        projects = self.get_queryset().filter(technologies__icontains=technology)
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)


class EducationViewSet(viewsets.ModelViewSet):
    serializer_class = EducationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["institution", "degree", "field_of_study", "current"]
    search_fields = ["institution", "degree", "field_of_study", "achievements"]
    ordering_fields = ["start_date", "end_date", "gpa", "created_at"]

    def get_queryset(self):
        return Education.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_institution(self, request):
        institution = request.query_params.get("institution")
        if not institution:
            return Response(
                {"error": "Institution parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        education = self.get_queryset().filter(institution__icontains=institution)
        serializer = self.get_serializer(education, many=True)
        return Response(serializer.data)


class CertificationViewSet(viewsets.ModelViewSet):
    serializer_class = CertificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["issuer"]
    search_fields = ["name", "issuer", "credential_id"]
    ordering_fields = ["issue_date", "expiry_date", "created_at"]

    def get_queryset(self):
        return Certification.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_issuer(self, request):
        issuer = request.query_params.get("issuer")
        if not issuer:
            return Response(
                {"error": "Issuer parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        certifications = self.get_queryset().filter(issuer__icontains=issuer)
        serializer = self.get_serializer(certifications, many=True)
        return Response(serializer.data)


class PublicationViewSet(viewsets.ModelViewSet):
    serializer_class = PublicationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["publisher", "journal"]
    search_fields = ["title", "authors", "abstract", "doi"]
    ordering_fields = ["publication_date", "created_at"]

    def get_queryset(self):
        return Publication.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_publisher(self, request):
        publisher = request.query_params.get("publisher")
        if not publisher:
            return Response(
                {"error": "Publisher parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        publications = self.get_queryset().filter(publisher__icontains=publisher)
        serializer = self.get_serializer(publications, many=True)
        return Response(serializer.data)


class SkillViewSet(viewsets.ModelViewSet):
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "proficiency"]
    search_fields = ["name", "category"]
    ordering_fields = ["proficiency", "created_at"]

    def get_queryset(self):
        return Skill.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_category(self, request):
        category = request.query_params.get("category")
        if not category:
            return Response(
                {"error": "Category parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        skills = self.get_queryset().filter(category=category)
        serializer = self.get_serializer(skills, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_proficiency(self, request):
        proficiency = request.query_params.get("proficiency")
        if not proficiency:
            return Response(
                {"error": "Proficiency parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        skills = self.get_queryset().filter(proficiency=proficiency)
        serializer = self.get_serializer(skills, many=True)
        return Response(serializer.data)


@require_http_methods(["POST"])
def import_github_profile(request):
    """Import profile data from GitHub."""
    try:
        data = json.loads(request.body)
        github_username = data.get("github_username")

        if not github_username:
            return JsonResponse({"error": "GitHub username is required"}, status=400)

        # Extract username from URL if a full URL is provided
        if "github.com" in github_username:
            # Remove any trailing slashes and get the last part of the URL
            github_username = github_username.rstrip("/").split("/")[-1]

        with GitHubProfileImporter(github_username) as importer:
            profile_data = json.loads(importer.import_profile(github_username))

            # Transform repositories into projects
            projects = importer.transform_repos_to_projects(
                profile_data.get("repositories", []),
                request.user.userprofile
            )

            # Save projects
            for project_data in projects:
                # Check if project already exists (based on GitHub URL)
                existing_project = Project.objects.filter(
                    profile=request.user.userprofile,
                    github_url=project_data['github_url']
                ).first()
                
                if existing_project:
                    # Update existing project
                    for key, value in project_data.items():
                        setattr(existing_project, key, value)
                    existing_project.save()
                else:
                    # Create new project
                    Project.objects.create(**project_data)

            # Save work experiences
            for exp in profile_data.get("work_experiences", []):
                WorkExperience.objects.create(
                    profile=request.user.userprofile,
                    company=exp["company"],
                    position=exp["position"],
                    start_date=exp["start_date"],
                    end_date=exp["end_date"],
                    description=exp["description"],
                    technologies=exp["technologies"],
                )

            # Save skills
            for skill in profile_data.get("skills", []):
                # The save method in Skill model will handle duplicates and case normalization
                Skill.objects.create(
                    profile=request.user.userprofile,
                    name=skill["name"],
                    category=skill["category"],
                    proficiency=skill["proficiency"],
                )

            return JsonResponse({"success": True, "message": "Profile imported successfully"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def import_resume(request):
    """Import profile data from uploaded resume."""
    try:
        if "resume" not in request.FILES:
            return JsonResponse({"error": "No resume file uploaded"}, status=400)

        resume_file = request.FILES["resume"]
        importer = ResumeImporter(resume_file)
        profile_data = importer.parse_resume()

        # Save the raw text and personal info to the user's profile
        user_profile = request.user.userprofile
        user_profile.parsed_resume_data = profile_data

        # Update personal information
        personal_info = profile_data.get("personal_info", {})
        user_profile.phone = personal_info.get("phone", "")
        user_profile.address = personal_info.get("address", "")
        user_profile.city = personal_info.get("city", "")
        user_profile.state = personal_info.get("state", "")
        user_profile.country = personal_info.get("country", "")
        user_profile.postal_code = personal_info.get("postal_code", "")
        user_profile.website = personal_info.get("website", "")
        user_profile.linkedin = personal_info.get("linkedin", "")
        user_profile.github = personal_info.get("github", "")

        # Update professional summary if available
        if personal_info.get("name"):
            user_profile.headline = personal_info["name"]

        user_profile.save()

        # Save work experiences
        for exp in profile_data.get("work_experiences", []):
            # Skip if no start date
            if not exp.get("start_date"):
                continue

            try:
                # Parse dates if they're strings
                start_date = exp.get("start_date")
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

                end_date = exp.get("end_date")
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

                WorkExperience.objects.create(
                    profile=request.user.userprofile,
                    company=exp.get("company", ""),
                    position=exp.get("position", ""),
                    start_date=start_date,
                    end_date=end_date,
                    current=exp.get("current", False),
                    description=exp.get("description", ""),
                    technologies=exp.get("technologies", []),
                )
            except (ValueError, TypeError):
                # Skip this experience if date parsing fails
                continue

        # Save education
        for edu in profile_data.get("education", []):
            try:
                # Parse GPA if it exists and is numeric
                gpa_str = edu.get("gpa")
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
                start_date = edu.get("start_date")
                if isinstance(start_date, str):
                    try:
                        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                    except ValueError:
                        start_date = None

                end_date = edu.get("end_date")
                if isinstance(end_date, str):
                    try:
                        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                    except ValueError:
                        end_date = None

                Education.objects.create(
                    profile=request.user.userprofile,
                    institution=edu.get("institution", ""),
                    degree=edu.get("degree", ""),
                    field_of_study=edu.get("field_of_study", ""),
                    start_date=start_date,
                    end_date=end_date,
                    gpa=gpa,
                    achievements=edu.get("achievements", []),
                )
            except Exception as e:
                # Log the error but continue processing other education entries
                logger.error(f"Error creating education entry: {str(e)}")
                continue

        # Save skills
        for skill in profile_data.get("skills", []):
            # The save method in Skill model will handle duplicates and case normalization
            Skill.objects.create(
                profile=request.user.userprofile,
                name=skill.get("name", ""),
                category=skill.get("category", ""),
                proficiency=skill.get("proficiency", 3),
            )

        # Save certifications
        for cert in profile_data.get("certifications", []):
            Certification.objects.create(
                profile=request.user.userprofile,
                name=cert.get("name", ""),
                issuer=cert.get("issuer", ""),
                issue_date=cert.get("issue_date"),
                expiry_date=cert.get("expiry_date"),
                credential_id=cert.get("credential_id"),
            )

        # Save projects
        for proj in profile_data.get("projects", []):
            Project.objects.create(
                profile=request.user.userprofile,
                title=proj.get("title", ""),
                description=proj.get("description", ""),
                start_date=proj.get("start_date"),
                end_date=proj.get("end_date"),
                technologies=proj.get("technologies", []),
            )

        return JsonResponse(
            {"success": True, "message": "Profile imported successfully", "data": profile_data}
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def import_linkedin_profile(request):
    """Import profile data from LinkedIn."""
    try:
        data = json.loads(request.body)
        linkedin_url = data.get("linkedin_url")

        if not linkedin_url:
            return JsonResponse({"error": "LinkedIn URL is required"}, status=400)

        importer = LinkedInImporter(linkedin_url)
        profile_data = json.loads(importer.parse_profile())

        # Save work experiences
        for exp in profile_data.get("work_experiences", []):
            WorkExperience.objects.create(
                profile=request.user.userprofile,
                company=exp["company"],
                position=exp["position"],
                start_date=exp["start_date"],
                end_date=exp["end_date"],
                description=exp["description"],
                technologies=exp["technologies"],
            )

        # Save education
        for edu in profile_data.get("education", []):
            Education.objects.create(
                profile=request.user.userprofile,
                institution=edu["institution"],
                degree=edu["degree"],
                field_of_study=edu["field_of_study"],
                start_date=edu["start_date"],
                end_date=edu["end_date"],
                gpa=edu.get("gpa"),
                achievements=edu.get("achievements", []),
            )

        # Save skills
        for skill in profile_data.get("skills", []):
            # The save method in Skill model will handle duplicates and case normalization
            Skill.objects.create(
                profile=request.user.userprofile,
                name=skill["name"],
                category=skill["category"],
                proficiency=skill["proficiency"],
            )

        # Save certifications
        for cert in profile_data.get("certifications", []):
            Certification.objects.create(
                profile=request.user.userprofile,
                name=cert["name"],
                issuer=cert["issuer"],
                issue_date=cert["issue_date"],
                expiry_date=cert.get("expiry_date"),
                credential_id=cert.get("credential_id"),
            )

        return JsonResponse({"success": True, "message": "Profile imported successfully"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def bulk_delete_records(request):
    """Handle bulk deletion of resume records."""
    try:
        data = json.loads(request.body)
        record_type = data.get("record_type")
        record_ids = data.get("record_ids", [])

        if not record_type or not record_ids:
            return JsonResponse({"error": "Missing required parameters"}, status=400)

        # Map record types to their models
        model_map = {
            "work_experience": WorkExperience,
            "education": Education,
            "project": Project,
            "certification": Certification,
            "publication": Publication,
            "skill": Skill,
        }

        if record_type not in model_map:
            return JsonResponse({"error": "Invalid record type"}, status=400)

        model = model_map[record_type]
        deleted_count = model.objects.filter(
            profile=request.user.userprofile, id__in=record_ids
        ).delete()[0]

        return JsonResponse(
            {
                "success": True,
                "message": f"Successfully deleted {deleted_count} records",
                "deleted_count": deleted_count,
            }
        )

    except Exception as e:
        logger.error(f"Error in bulk delete: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def edit_record(request, record_type, record_id):
    """Handle editing of a record."""
    try:
        data = json.loads(request.body)

        # Map record types to their models
        model_map = {
            "work_experience": WorkExperience,
            "education": Education,
            "project": Project,
            "certification": Certification,
            "publication": Publication,
            "skill": Skill,
        }

        if record_type not in model_map:
            return JsonResponse({"error": "Invalid record type"}, status=400)

        model = model_map[record_type]
        record = model.objects.filter(profile=request.user.userprofile, id=record_id).first()

        if not record:
            return JsonResponse({"error": "Record not found"}, status=404)

        # Update record fields
        for field, value in data.items():
            if hasattr(record, field):
                if field in [
                    "start_date",
                    "end_date",
                    "issue_date",
                    "expiry_date",
                    "publication_date",
                ]:
                    try:
                        value = datetime.strptime(value, "%b %Y").date()
                    except ValueError:
                        continue
                elif field == "technologies":
                    value = value.split(",") if value else []
                setattr(record, field, value)

        record.save()

        return JsonResponse({"success": True, "message": "Record updated successfully"})

    except Exception as e:
        logger.error(f"Error in edit record: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def get_profile_stats(request):
    """Get current profile statistics"""
    profile = request.user.userprofile
    stats = {
        "work_experience": profile.work_experiences.count(),
        "projects": profile.projects.count(),
        "skills": profile.skills.count(),
        "certifications": profile.certifications.count(),
        "years_of_experience": profile.years_of_experience,
    }
    return JsonResponse(stats)


@method_decorator(login_required, name="dispatch")
class ManualSubmissionView(TemplateView):
    template_name = "core/manual_submission.html"


@login_required
@require_http_methods(["POST"])
def generate_documents(request):
    try:
        data = json.loads(request.body)
        job_description = data.get("job_description")
        document_type = data.get("document_type")

        if not job_description or not document_type:
            return HttpResponse(status=400)

        if document_type not in ["resume", "cover_letter"]:
            return HttpResponse(status=400)

        # Create a buffer to store the PDF
        buffer = BytesIO()

        try:
            if document_type == "resume":
                # Create resume composition with user data
                resume = ResumeComposition(request.user.userprofile)
                # Build the resume
                resume.build(buffer, job_description)

                # Get the value of the BytesIO buffer and write it to the response
                pdf = buffer.getvalue()
                buffer.close()

                # Create response
                response = HttpResponse(pdf, content_type="application/pdf")
                response["Content-Disposition"] = (
                    f'attachment; filename="{request.user.username}_resume_{date.today().strftime("%Y%m%d")}.pdf"'
                )
                return response

            elif document_type == "cover_letter":
                # Create cover letter using CoverLetterComposition
                cover_letter_composer = CoverLetterComposition(
                    request.user.userprofile, job_description
                )
                buffer = cover_letter_composer.build()
                cover_letter_bytes = buffer.getvalue()
                buffer.close()

                # Encode cover letter bytes in base64
                response_data = {
                    "documents": {
                        "cover_letter": base64.b64encode(cover_letter_bytes).decode("utf-8")
                    }
                }

                return HttpResponse(json.dumps(response_data), content_type="application/json")
        except Exception as e:
            logger.error(f"Error generating {document_type}: {str(e)}")
            return HttpResponse(status=500)

    except json.JSONDecodeError:
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Unexpected error in generate_documents: {str(e)}")
        return HttpResponse(status=500)


@require_http_methods(["POST"])
@login_required
def generate_answers(request):
    """Generate answers for application questions using Ollama."""
    try:
        data = json.loads(request.body)
        job_description = data.get("job_description")
        questions = data.get("questions")

        if not job_description or not questions:
            return JsonResponse({"error": "Job description and questions are required"}, status=400)

        # Get user profile information
        user_profile = request.user.userprofile

        # Format user's background information
        work_experiences = []
        if user_profile.work_experiences.exists():
            for exp in user_profile.work_experiences.all():
                work_experiences.append(
                    {
                        "company": exp.company,
                        "position": exp.position,
                        "start_date": (
                            exp.start_date.strftime("%Y-%m-%d") if exp.start_date else None
                        ),
                        "end_date": exp.end_date.strftime("%Y-%m-%d") if exp.end_date else None,
                        "current": exp.current,
                        "description": exp.description,
                        "technologies": exp.technologies,
                    }
                )

        skills = []
        if user_profile.skills.exists():
            for skill in user_profile.skills.all():
                skills.append(
                    {
                        "name": skill.name,
                        "category": skill.category,
                        "proficiency": skill.proficiency,
                    }
                )

        projects = []
        if user_profile.projects.exists():
            for proj in user_profile.projects.all():
                projects.append(
                    {
                        "title": proj.title,
                        "description": proj.description,
                        "technologies": proj.technologies,
                        "start_date": (
                            proj.start_date.strftime("%Y-%m-%d") if proj.start_date else None
                        ),
                        "end_date": proj.end_date.strftime("%Y-%m-%d") if proj.end_date else None,
                    }
                )

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

        return JsonResponse({"answers": answers})

    except Exception as e:
        logger.error(f"Error generating answers: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def process_job_application(request):
    try:
        data = json.loads(request.body)
        job_description = data.get("job_description")
        questions = data.get("questions", [])
        document_type = data.get("document_type", "all")  # 'resume', 'cover_letter', or 'all'

        if not job_description:
            return JsonResponse({"error": "Missing job description"}, status=400)

        # Initialize agents
        personal_agent = PersonalAgent(request.user.id)

        # Load user background
        background = PersonalBackground(
            profile=request.user.userprofile.__dict__,
            work_experience=list(request.user.userprofile.work_experiences.values()),
            education=list(request.user.userprofile.education.values()),
            skills=list(request.user.userprofile.skills.values()),
            projects=list(request.user.userprofile.projects.values()),
            github_data=request.user.userprofile.github_data,
            achievements=[],  # We'll add this field to the model later
            interests=[],  # We'll add this field to the model later
        )
        personal_agent.load_background(background)

        # Initialize application agent
        application_agent = ApplicationAgent(request.user.id, personal_agent)
        if document_type is not None:
            # Initialize search agent for job analysis
            search_agent = SearchAgent(request.user.id, personal_agent)

            # Analyze job fit
            job_analysis = search_agent.analyze_job_fit({"description": job_description})

            response_data = {
                "job_analysis": json.loads(job_analysis),
                "documents": {},
                "answers": [],
            }

        # Generate requested documents
        if document_type in ["resume", "all"]:
            resume_buffer = BytesIO()
            resume = ResumeComposition(personal_agent)
            resume.build(resume_buffer, job_description)
            resume_bytes = resume_buffer.getvalue()
            resume_buffer.close()
            # Encode resume bytes in base64
            response_data["documents"]["resume"] = base64.b64encode(resume_bytes).decode("utf-8")

        if document_type in ["cover_letter", "all"]:
            # Create cover letter using CoverLetterComposition
            cover_letter_composer = CoverLetterComposition(
                request.user.userprofile, job_description
            )
            buffer = cover_letter_composer.build()
            cover_letter_bytes = buffer.getvalue()
            buffer.close()

            # Encode cover letter bytes in base64
            response_data["documents"]["cover_letter"] = base64.b64encode(
                cover_letter_bytes
            ).decode("utf-8")

        # Handle application questions if provided
        if questions:
            answers = application_agent.handle_screening_questions(questions, job_description)
            response_data["answers"] = answers

        # Add interview preparation if requested
        if data.get("include_interview_prep", False):
            interview_prep = application_agent.prepare_interview_responses(job_description)
            response_data["interview_prep"] = json.loads(interview_prep)

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        logger.error(f"Error processing job application: {str(e)}")
        return JsonResponse({"error": f"Error processing application: {str(e)}"}, status=500)


@api_view(["POST"])
@permission_classes([AllowAny])  # Temporarily allow any user for testing
def fill_form(request):
    try:
        # Get form data from request
        form_data = json.loads(request.body)

        fields = form_data.get("fields", [])
        job_description = form_data.get("jobDescription", "")

        # Get current user
        user = request.user
        if not user.is_authenticated:
            print("User not authenticated")
            return Response({"error": "User not authenticated"}, status=401)

        # Initialize agents
        personal_agent = PersonalAgent(user.id)
        application_agent = ApplicationAgent(user.id, personal_agent)

        # Load user's background data
        background = load_user_background(user.id)
        personal_agent.load_background(background)

        # Fill form fields
        responses = application_agent.fill_application_form(fields, job_description)
        print("Generated responses:", responses)

        return Response({"success": True, "responses": responses})
    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=500)


def load_user_background(user_id):
    """Load user's background data from your database"""
    # This is a placeholder - implement based on your data model
    user = User.objects.get(id=user_id)
    # Load profile, experience, education, etc. from your models
    # Return PersonalBackground object
    return PersonalBackground(
        profile={},  # Load from your profile model
        work_experience=[],  # Load from your experience model
        education=[],  # Load from your education model
        skills=[],  # Load from your skills model
        projects=[],  # Load from your projects model
        github_data={},  # Load from your GitHub data model
        achievements=[],  # Load from your achievements model
        interests=[],  # Load from your interests model
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def get_token(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response({"error": "Please provide both username and password"}, status=400)

    user = authenticate(username=username, password=password)

    if not user:
        return Response({"error": "Invalid credentials"}, status=401)

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    )


@login_required
def jobs_page(request):
    """View for the jobs page"""
    # Get user's job listings
    job_listings = JobListing.objects.filter(user=request.user).order_by("-posted_date", "-match_score")

    # Get search parameters from request
    role = request.GET.get("role", "")
    location = request.GET.get("location", "")

    # Filter job listings if search parameters are provided
    if role or location:
        if role:
            job_listings = job_listings.filter(title__icontains=role)
        if location:
            job_listings = job_listings.filter(location__icontains=location)

    # Annotate job listings with has_tailored_documents
    job_listings = [
        {
            'id': job.id,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'description': job.description,
            'source': job.source,
            'source_url': job.source_url,
            'posted_date': job.posted_date,
            'match_score': job.match_score,
            'applied': job.applied,
            'has_tailored_documents': job.has_tailored_documents,
        }
        for job in job_listings
    ]

    context = {
        "job_listings": job_listings,
        "role": role,
        "location": location,
    }
    return render(request, "core/jobs.html", context)


@login_required
def search_jobs(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            role = data.get("role")
            location = data.get("location")
            platforms = data.get("platforms", [])  # Get platforms from request

            if not role or not location:
                return JsonResponse({"error": "Role and location are required"}, status=400)

            # Get user profile and their preferences
            user_profile = request.user.userprofile
            try:
                preferences = JobPlatformPreference.objects.get(user_profile=user_profile)
                # If no platforms specified in request, use user's preferences
                if not platforms:
                    platforms = preferences.preferred_platforms
            except JobPlatformPreference.DoesNotExist:
                # Default to LinkedIn if no preferences set
                if not platforms:
                    platforms = ["linkedin"]

            # Initialize agents
            personal_agent = PersonalAgent(request.user.id)
            search_agent = SearchAgent(request.user.id, personal_agent)

            # Search for jobs across all selected platforms
            job_listings = []
            errors = []

            for platform in platforms:
                try:
                    platform_jobs = search_agent.search_jobs(role, location, platform, request)
                    job_listings.extend(platform_jobs)
                except Exception as e:
                    logger.error(f"Error searching {platform}: {str(e)}")
                    errors.append(f"{platform.title()}: {str(e)}")

            if not job_listings and errors:
                # If we have errors and no results, return the error
                error_msg = "Errors occurred while searching: " + "; ".join(errors)
                return JsonResponse({"error": error_msg}, status=500)

            # Process and save job listings
            processed_jobs = []
            for job in job_listings:
                try:
                    # Create or update job listing
                    job_obj, created = JobListing.objects.update_or_create(
                        source_url=job["url"],
                        user=request.user,
                        defaults={
                            "user": request.user,
                            "title": job["title"],
                            "company": job["company"],
                            "location": job["location"],
                            "description": job["description"],
                            "source": job["source"],
                            "posted_date": job.get("posted_date", timezone.now().date()),
                            "salary_range": job.get("salary_range", ""),
                            "job_type": job.get("job_type", ""),
                            "requirements": job.get("requirements", ""),
                            "match_score": job.get("match_score", None),
                        },
                    )
                    processed_jobs.append({
                        "id": job_obj.id,
                        "title": job_obj.title,
                        "company": job_obj.company,
                        "location": job_obj.location,
                        "description": job_obj.description,
                        "source": job_obj.source,
                        "source_url": job_obj.source_url,
                        "posted_date": job_obj.posted_date,
                        "match_score": job_obj.match_score,
                        "applied": job_obj.applied,
                    })
                except Exception as e:
                    logger.error(f"Error processing job: {str(e)}")
                    continue

            return JsonResponse({
                "jobs": processed_jobs,
                "warnings": errors if errors else None
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            logger.error(f"Error in search_jobs: {str(e)}")
            return JsonResponse({"error": "An unexpected error occurred"}, status=500)

    return JsonResponse({"error": "Only POST method is allowed"}, status=405)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_job_documents(request, job_id):
    """Generate tailored resume and cover letter for a specific job"""
    try:
        # Get the job listing
        job_listing = get_object_or_404(JobListing, id=job_id)

        # Initialize agents
        personal_agent = PersonalAgent(request.user.id)

        # Load user background
        background = PersonalBackground(
            profile=request.user.userprofile.__dict__,
            work_experience=list(request.user.userprofile.work_experiences.values()),
            education=list(request.user.userprofile.education.values()),
            skills=list(request.user.userprofile.skills.values()),
            projects=list(request.user.userprofile.projects.values()),
            github_data=request.user.userprofile.github_data,  # We'll implement GitHub data fetching later
            achievements=[],  # We'll add this field to the model later
            interests=[],  # We'll add this field to the model later
        )
        personal_agent.load_background(background)

        # Generate documents
        logger.info(f"Generating documents for job {job_id}")
        success = personal_agent.generate_tailored_documents(job_listing)

        if success:
            return Response(
                {
                    "success": True,
                    "message": "Documents generated successfully",
                    "has_tailored_documents": True,
                    "resume_url": (
                        job_listing.tailored_resume.url if job_listing.tailored_resume else None
                    ),
                    "cover_letter_url": (
                        job_listing.tailored_cover_letter.url
                        if job_listing.tailored_cover_letter
                        else None
                    ),
                }
            )
        else:
            return Response(
                {
                    "success": False,
                    "message": "Failed to generate documents",
                    "has_tailored_documents": False,
                },
                status=500,
            )

    except JobListing.DoesNotExist:
        return Response({"success": False, "message": "Job not found"}, status=404)
    except Exception as e:
        logger.error(f"Error generating documents: {str(e)}")
        return Response(
            {"success": False, "message": f"Error generating documents: {str(e)}"}, status=500
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_job_documents(request, job_id):
    """Get the tailored resume and cover letter for a specific job"""
    try:
        job_listing: JobListing = JobListing.objects.get(id=job_id, user=request.user)

        if not job_listing.tailored_resume or not job_listing.tailored_cover_letter:
            return Response(
                {"message": "Documents not found", "has_tailored_documents": False}, status=404
            )

        # Return URLs to the documents
        return Response(
            {
                "message": "Documents found",
                "has_tailored_documents": True,
                "resume_url": (
                    job_listing.tailored_resume.url if job_listing.tailored_resume else None
                ),
                "cover_letter_url": (
                    job_listing.tailored_cover_letter.url
                    if job_listing.tailored_cover_letter
                    else None
                ),
            }
        )

    except JobListing.DoesNotExist:
        return Response({"message": "Job not found"}, status=404)
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        return Response({"message": "An error occurred while getting documents"}, status=500)


@login_required
@require_http_methods(["POST"])
def apply_to_job(request, job_id) -> JsonResponse:
    """API endpoint to apply to a job"""
    try:
        job: JobListing = JobListing.objects.get(id=job_id)

        # Update job status
        job.applied = True
        job.application_date = datetime.now().date()
        job.application_status = "Applied"
        job.save()

        return JsonResponse(
            {
                "message": "Successfully applied to job",
                "job": {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "application_status": job.application_status,
                },
            }
        )

    except JobListing.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def job_detail(request, job_id) -> HttpResponse:
    """View for individual job details"""
    job: JobListing = get_object_or_404(JobListing, id=job_id)
    context: dict[str, JobListing] = {
        "job": job,
    }
    return render(request, "core/job_detail.html", context)


@login_required
def job_apply(
    request, job_id
) -> HttpResponseRedirect | HttpResponsePermanentRedirect | HttpResponse:
    """View for job application process"""
    job: JobListing = get_object_or_404(JobListing, id=job_id)

    if request.method == "POST":
        try:
            # Update job status
            job.applied = True
            job.application_date = datetime.now().date()
            job.application_status = "Applied"
            job.save()

            messages.success(request, "Successfully applied to job!")
            return redirect("core:job_detail", job_id=job.id)

        except Exception as e:
            messages.error(request, f"Error applying to job: {str(e)}")
            return redirect("core:job_detail", job_id=job.id)

    context: dict[str, JobListing] = {
        "job": job,
    }
    return render(request, "core/job_apply.html", context)


@login_required
def job_platform_preferences(request):
    """View for managing job platform preferences"""
    user_profile = request.user.userprofile
    try:
        preferences = JobPlatformPreference.objects.get(user_profile=user_profile)
    except JobPlatformPreference.DoesNotExist:
        preferences = JobPlatformPreference(user_profile=user_profile)
        preferences.save()

    if request.method == "POST":
        form = JobPlatformPreferenceForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Your job platform preferences have been updated.")
            return redirect("job_search")  # Assuming you have a job search view
    else:
        form = JobPlatformPreferenceForm(instance=preferences)

    return render(
        request,
        "core/job_platform_preferences.html",
        {"form": form, "platforms": JobListing.JOB_SOURCES},
    )


@login_required
@require_POST
def remove_job(request):
    """Remove a job from the frontend display"""
    try:
        data = json.loads(request.body)
        job_id = data.get("job_id")
        
        if not job_id:
            return JsonResponse({"error": "Job ID is required"}, status=400)
            
        # Get the job listing
        job = JobListing.objects.filter(id=job_id).first()
        if not job:
            return JsonResponse({"error": "Job not found"}, status=404)
            
        # Store the job ID in user's session to hide it from future searches
        hidden_jobs = request.session.get("hidden_jobs", [])
        if job_id not in hidden_jobs:
            hidden_jobs.append(job_id)
            request.session["hidden_jobs"] = hidden_jobs
            
        return JsonResponse({"message": "Job removed successfully"})
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        logger.error(f"Error removing job: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def deduplicate_skills(request):
    """Remove duplicate skills for the current user's profile."""
    try:
        # Get all skills for the user
        skills = request.user.userprofile.skills.all()
        
        # Keep track of seen skills (case-insensitive)
        seen_skills = {}
        duplicates_removed = 0
        
        for skill in skills:
            # Create a key using lowercase name and category
            key = (skill.name.lower(), skill.category)
            
            if key in seen_skills:
                # If we've seen this skill before
                existing_skill = seen_skills[key]
                
                # Keep the one with higher proficiency
                if skill.proficiency > existing_skill.proficiency:
                    existing_skill.delete()
                    seen_skills[key] = skill
                else:
                    skill.delete()
                duplicates_removed += 1
            else:
                # First time seeing this skill
                seen_skills[key] = skill
                # Normalize the name to Title Case
                skill.name = skill.name.title()
                skill.save()
        
        if duplicates_removed > 0:
            messages.success(request, f"Successfully removed {duplicates_removed} duplicate skills.")
        else:
            messages.info(request, "No duplicate skills found.")
            
        return redirect('core:profile')
        
    except Exception as e:
        messages.error(request, f"Error removing duplicate skills: {str(e)}")
        return redirect('core:profile')
