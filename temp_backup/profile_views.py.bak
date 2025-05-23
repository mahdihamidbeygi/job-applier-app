"""
Profile-related views for the core app.
"""

import json
import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from core.forms import (
    CertificationForm,
    EducationForm,
    ProjectForm,
    PublicationForm,
    SkillForm,
    UserProfileForm,
    WorkExperienceForm,
)
from core.models import (
    Certification,
    Education,
    Project,
    Publication,
    Skill,
    UserProfile,
    WorkExperience,
)
from core.utils.profile_importers import GitHubProfileImporter, LinkedInImporter, ResumeImporter
from core.views.utility_views import parse_pdf_resume

logger = logging.getLogger(__name__)


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
    """Delete an item from the profile"""
    model_map = {
        "work_experience": WorkExperience,
        "project": Project,
        "education": Education,
        "certification": Certification,
        "publication": Publication,
        "skill": Skill,
    }

    if model_name not in model_map:
        messages.error(request, "Invalid model name.")
        return redirect("core:profile")

    model_class = model_map[model_name]

    try:
        item = model_class.objects.get(id=item_id, profile=request.user.userprofile)
        item.delete()
        messages.success(request, f"{model_name.replace('_', ' ').title()} deleted successfully!")
    except model_class.DoesNotExist:
        messages.error(request, f"{model_name.replace('_', ' ').title()} not found.")
    except Exception as e:
        logger.error(f"Error deleting {model_name}: {str(e)}")
        messages.error(request, f"Error deleting {model_name.replace('_', ' ').title()}.")

    return redirect("core:profile")


@require_http_methods(["POST"])
def import_github_profile(request):
    """Import a GitHub profile"""
    try:
        github_url = request.POST.get("github_url")

        if not github_url:
            return JsonResponse({"error": "GitHub URL is required"}, status=400)

        # Extract username from GitHub URL
        github_username = github_url.split("/")[-1]
        if github_username == "github.com":
            github_username = github_url.split("/")[-2]

        # Import GitHub profile
        importer = GitHubProfileImporter(github_username)
        github_data = importer.import_profile(github_username)

        if not github_data:
            return JsonResponse({"error": "Failed to import GitHub profile"}, status=400)

        # Parse repos into projects
        github_data = json.loads(github_data)
        projects = importer.transform_repos_to_projects(
            github_data.get("repositories", []), request.user.userprofile
        )

        # Save GitHub URL to profile
        request.user.userprofile.github_url = github_url
        request.user.userprofile.github_data = github_data
        request.user.userprofile.last_github_refresh = timezone.now()
        request.user.userprofile.save()

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

        return JsonResponse({"success": True, "projects_created": len(projects)})
    except Exception as e:
        logger.error(f"Error importing GitHub profile: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
def import_resume(request):
    """Import a resume file"""
    if "resume" not in request.FILES:
        return JsonResponse({"error": "No resume file provided"}, status=400)

    resume_file = request.FILES["resume"]

    try:
        # Upload resume file
        logger.info(f"Attempting to upload file: {resume_file.name}")
        file_path = f"resumes/{request.user.username}/{resume_file.name}"
        saved_path = default_storage.save(file_path, resume_file)
        file_url = default_storage.url(saved_path)
        logger.info(f"File uploaded successfully. URL: {file_url}")

        # Parse resume
        resume_importer = ResumeImporter()

        if resume_file.name.endswith(".pdf"):
            text = parse_pdf_resume(resume_file)
            profile_data = resume_importer.import_from_text(text)

            # Update user profile
            profile = request.user.userprofile
            profile.parsed_resume_data = {"raw_text": text, "file_url": file_url}

            # Update fields if they're empty
            if "summary" in profile_data and not profile.professional_summary:
                profile.professional_summary = profile_data.get("summary")

            if "contact" in profile_data:
                contact = profile_data.get("contact", {})
                if "name" in contact and not profile.name:
                    profile.name = contact.get("name")
                if "email" in contact and not profile.email:
                    profile.email = contact.get("email")
                if "phone" in contact and not profile.phone:
                    profile.phone = contact.get("phone")
                if "location" in contact and not profile.address:
                    profile.address = contact.get("location")
                if "linkedin" in contact and not profile.linkedin_url:
                    profile.linkedin_url = contact.get("linkedin")
                if "github" in contact and not profile.github_url:
                    profile.github_url = contact.get("github")
                if "website" in contact and not profile.website:
                    profile.website = contact.get("website")

            profile.save()

            # Import work experiences
            if "work_experience" in profile_data:
                for exp_data in profile_data.get("work_experience", []):
                    # Skip if already exists
                    existing = WorkExperience.objects.filter(
                        profile=profile,
                        company=exp_data.get("company"),
                        position=exp_data.get("title", ""),
                    ).first()

                    if not existing:
                        # Parse dates
                        start_date = None
                        end_date = None
                        try:
                            if "start_date" in exp_data and exp_data["start_date"]:
                                start_date = datetime.strptime(
                                    exp_data["start_date"], "%Y-%m-%d"
                                ).date()
                            if "end_date" in exp_data and exp_data["end_date"]:
                                end_date = datetime.strptime(
                                    exp_data["end_date"], "%Y-%m-%d"
                                ).date()
                        except ValueError:
                            logger.warning(f"Invalid date format in work experience: {exp_data}")

                        # Create work experience
                        WorkExperience.objects.create(
                            profile=profile,
                            company=exp_data.get("company", ""),
                            position=exp_data.get("title", ""),
                            description=exp_data.get("description", ""),
                            start_date=start_date or timezone.now().date(),
                            end_date=end_date,
                            current=not end_date,
                        )

            # Import education
            if "education" in profile_data:
                for edu_data in profile_data.get("education", []):
                    # Skip if already exists
                    existing = Education.objects.filter(
                        profile=profile,
                        institution=edu_data.get("institution", ""),
                        degree=edu_data.get("degree", ""),
                    ).first()

                    if not existing:
                        # Parse dates
                        start_date = None
                        end_date = None
                        try:
                            if "start_date" in edu_data and edu_data["start_date"]:
                                start_date = datetime.strptime(
                                    edu_data["start_date"], "%Y-%m-%d"
                                ).date()
                            if "end_date" in edu_data and edu_data["end_date"]:
                                end_date = datetime.strptime(
                                    edu_data["end_date"], "%Y-%m-%d"
                                ).date()
                        except ValueError:
                            logger.warning(f"Invalid date format in education: {edu_data}")

                        # Create education
                        Education.objects.create(
                            profile=profile,
                            institution=edu_data.get("institution", ""),
                            degree=edu_data.get("degree", ""),
                            field_of_study=edu_data.get("field_of_study", ""),
                            start_date=start_date,
                            end_date=end_date,
                            current=not end_date,
                        )

            # Import skills
            if "skills" in profile_data:
                for skill_name in profile_data.get("skills", []):
                    # Skip if already exists
                    existing = Skill.objects.filter(
                        profile=profile,
                        name__iexact=skill_name,
                    ).first()

                    if not existing:
                        # Create skill
                        Skill.objects.create(
                            profile=profile,
                            name=skill_name,
                            category="other",  # Default category
                            proficiency=3,  # Default proficiency
                        )

            return JsonResponse(
                {
                    "success": True,
                    "file_url": file_url,
                    "profile_data": profile_data,
                }
            )
        else:
            return JsonResponse({"error": "Only PDF files are supported at this time"}, status=400)
    except Exception as e:
        logger.error(f"Error importing resume: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
def import_linkedin_profile(request):
    """Import a LinkedIn profile"""
    try:
        linkedin_url = request.POST.get("linkedin_url")

        if not linkedin_url:
            return JsonResponse({"error": "LinkedIn URL is required"}, status=400)

        # Extract username from LinkedIn URL
        linkedin_username = linkedin_url.split("/in/")[-1].split("/")[0]

        # Import LinkedIn profile
        importer = LinkedInImporter()
        profile_data = importer.import_from_file(request.FILES.get("linkedin_file"))

        if not profile_data:
            return JsonResponse({"error": "Failed to import LinkedIn profile"}, status=400)

        # Update user profile
        profile = request.user.userprofile
        profile.linkedin_url = linkedin_url

        # Update fields if they're empty
        if "summary" in profile_data and not profile.professional_summary:
            profile.professional_summary = profile_data.get("summary")

        if "contact" in profile_data:
            contact = profile_data.get("contact", {})
            if "name" in contact and not profile.name:
                profile.name = contact.get("name")
            if "headline" in contact and not profile.headline:
                profile.headline = contact.get("headline")

        profile.save()

        # Import work experiences
        if "experience" in profile_data:
            for exp_data in profile_data.get("experience", []):
                # Skip if already exists
                existing = WorkExperience.objects.filter(
                    profile=profile,
                    company=exp_data.get("company_name"),
                    position=exp_data.get("title", ""),
                ).first()

                if not existing:
                    # Create work experience
                    WorkExperience.objects.create(
                        profile=profile,
                        company=exp_data.get("company_name", ""),
                        position=exp_data.get("title", ""),
                        description=exp_data.get("description", ""),
                        location=exp_data.get("location", ""),
                        start_date=exp_data.get("starts_at", {}).get("day", 1),
                        end_date=exp_data.get("ends_at", {}).get("day", None),
                        current=bool(not exp_data.get("ends_at")),
                    )

        # Import education
        if "education" in profile_data:
            for edu_data in profile_data.get("education", []):
                # Skip if already exists
                existing = Education.objects.filter(
                    profile=profile,
                    institution=edu_data.get("school_name", ""),
                    degree=edu_data.get("degree_name", ""),
                ).first()

                if not existing:
                    # Create education
                    Education.objects.create(
                        profile=profile,
                        institution=edu_data.get("school_name", ""),
                        degree=edu_data.get("degree_name", ""),
                        field_of_study=edu_data.get("field_of_study", ""),
                        start_date=edu_data.get("starts_at", {}).get("day", None),
                        end_date=edu_data.get("ends_at", {}).get("day", None),
                        current=bool(not edu_data.get("ends_at")),
                    )

        # Import skills
        if "skills" in profile_data:
            for skill_data in profile_data.get("skills", []):
                # Skip if already exists
                existing = Skill.objects.filter(
                    profile=profile,
                    name__iexact=skill_data.get("name", ""),
                ).first()

                if not existing:
                    # Create skill
                    Skill.objects.create(
                        profile=profile,
                        name=skill_data.get("name", ""),
                        category="other",  # Default category
                        proficiency=3,  # Default proficiency
                    )

        return JsonResponse(
            {
                "success": True,
                "profile_data": profile_data,
            }
        )
    except Exception as e:
        logger.error(f"Error importing LinkedIn profile: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def bulk_delete_records(request):
    """Bulk delete records from the profile"""
    try:
        data = json.loads(request.body)
        record_type = data.get("record_type")
        record_ids = data.get("record_ids", [])

        if not record_type or not record_ids:
            return JsonResponse(
                {"error": "Record type and at least one record ID are required"}, status=400
            )

        model_map = {
            "work_experience": WorkExperience,
            "project": Project,
            "education": Education,
            "certification": Certification,
            "publication": Publication,
            "skill": Skill,
        }

        if record_type not in model_map:
            return JsonResponse({"error": "Invalid record type"}, status=400)

        model_class = model_map[record_type]

        # Delete records
        deleted = model_class.objects.filter(
            profile=request.user.userprofile, id__in=record_ids
        ).delete()

        return JsonResponse(
            {
                "success": True,
                "deleted_count": deleted[0],
                "message": f"{deleted[0]} {record_type.replace('_', ' ')}(s) deleted successfully",
            }
        )
    except Exception as e:
        logger.error(f"Error in bulk_delete_records: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def edit_record(request, record_type, record_id):
    """Edit a record in the profile"""
    model_map = {
        "work_experience": (WorkExperience, WorkExperienceForm),
        "project": (Project, ProjectForm),
        "education": (Education, EducationForm),
        "certification": (Certification, CertificationForm),
        "publication": (Publication, PublicationForm),
        "skill": (Skill, SkillForm),
        "profile": (UserProfile, UserProfileForm),
    }

    if record_type not in model_map:
        return JsonResponse({"error": "Invalid record type"}, status=400)

    model_class, form_class = model_map[record_type]

    try:
        if record_type == "profile":
            # For profile, we don't need the record_id as it's the user's profile
            record = request.user.userprofile
        else:
            record = get_object_or_404(model_class, id=record_id, profile=request.user.userprofile)

        form = form_class(request.POST, instance=record)

        if form.is_valid():
            form.save()
            return JsonResponse(
                {
                    "success": True,
                    "message": f"{record_type.replace('_', ' ').title()} updated successfully",
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    except Exception as e:
        logger.error(f"Error editing {record_type}: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def edit_profile(request):
    """Edit user profile basic information"""
    try:
        profile = request.user.userprofile
        form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            form.save()
            return JsonResponse(
                {
                    "success": True,
                    "message": "Profile updated successfully",
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    except Exception as e:
        logger.error(f"Error editing profile: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def get_profile_stats(request):
    """Get profile statistics"""
    profile = request.user.userprofile
    stats = {
        "work_experience_count": profile.work_experiences.count(),
        "education_count": profile.education.count(),
        "skills_count": profile.skills.count(),
        "projects_count": profile.projects.count(),
        "certifications_count": profile.certifications.count(),
        "publications_count": profile.publications.count(),
        "years_of_experience": profile.years_of_experience,
    }
    return JsonResponse(stats)


@login_required
def deduplicate_skills(request):
    """Deduplicate skills by merging similar ones"""
    profile = request.user.userprofile
    skills = profile.skills.all()

    # Find duplicates (case-insensitive)
    seen_skills = {}
    duplicates = []

    for skill in skills:
        skill_name_lower = skill.name.lower()
        if skill_name_lower in seen_skills:
            duplicates.append((seen_skills[skill_name_lower], skill))
        else:
            seen_skills[skill_name_lower] = skill

    # Merge duplicates - keep the higher proficiency one
    merged_count = 0
    for original, duplicate in duplicates:
        # Keep the one with higher proficiency or the original if equal
        if duplicate.proficiency > original.proficiency:
            original.proficiency = duplicate.proficiency
            original.save()

        # Delete the duplicate
        duplicate.delete()
        merged_count += 1

    messages.success(request, f"Deduplication complete! Merged {merged_count} duplicate skills.")
    return redirect("core:profile")
