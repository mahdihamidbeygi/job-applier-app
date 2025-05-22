"""
Base profile views for displaying and editing user profiles.
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.forms import (
    CertificationForm,
    EducationForm,
    ProjectForm,
    PublicationForm,
    SkillForm,
    UserProfileForm,
    WorkExperienceForm,
)
from core.models import Project, UserProfile
from core.utils.profile_importers import GitHubProfileImporter
from core.views.utility_views import parse_pdf_resume

logger = logging.getLogger(__name__)


@login_required
def profile(request):
    """User profile view"""
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
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
            github_data_json_str = importer.import_profile()
            github_data = json.loads(github_data_json_str)

            # Transform repositories into projects
            projects = importer.transform_repos_to_projects(
                github_data.get("repositories", []), request.user.userprofile
            )

            # Save projects
            for project_data in projects:
                # Check if project already exists (based on GitHub URL)
                existing_project = Project.objects.filter(
                    profile=request.user.userprofile, github_url=project_data["github_url"]
                ).first()

                if existing_project:
                    # Update existing project
                    for key, value in project_data.items():
                        if key != "profile":  # Skip updating the profile reference
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


@require_http_methods(["POST"])
@login_required
def edit_profile(request):
    """Edit user profile"""
    if request.method == "POST":
        profile_form = UserProfileForm(
            request.POST, request.FILES, instance=request.user.userprofile
        )
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profile updated successfully!")
        else:
            messages.error(request, "Error updating profile.")

    return redirect("core:profile")


@login_required
def get_profile_stats(request):
    """Get profile statistics"""
    profile = request.user.userprofile

    skills_count = profile.skills.count()
    projects_count = profile.projects.count()
    experience_count = profile.work_experiences.count()
    education_count = profile.education.count()
    certifications_count = profile.certifications.count()
    publications_count = profile.publications.count()

    years_experience = profile.years_of_experience

    stats = {
        "skills_count": skills_count,
        "projects_count": projects_count,
        "experience_count": experience_count,
        "education_count": education_count,
        "certifications_count": certifications_count,
        "publications_count": publications_count,
        "years_experience": years_experience,
        "profile_completeness": calculate_profile_completeness(profile),
    }

    return JsonResponse(stats)


def calculate_profile_completeness(profile):
    """Calculate how complete a profile is as a percentage"""
    fields = [
        profile.name,
        profile.title,
        profile.phone,
        profile.city,
        profile.state,
        profile.professional_summary,
        profile.linkedin_url,
        profile.github_url,
    ]

    # Count non-empty fields
    completed_fields = sum(1 for field in fields if field)

    # Count required related objects
    if profile.skills.exists():
        completed_fields += 1
    if profile.work_experiences.exists():
        completed_fields += 1
    if profile.education.exists():
        completed_fields += 1

    # Calculate percentage (out of potential 11 important fields)
    return round((completed_fields / 11) * 100)
