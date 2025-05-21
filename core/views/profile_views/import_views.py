"""
Views for importing profile data from various sources.
"""

import json
import logging
from datetime import datetime

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import Certification, Education, Project, Publication, Skill, WorkExperience
from core.utils.profile_importers import GitHubProfileImporter, LinkedInImporter, ResumeImporter
from core.views.utility_views import parse_pdf_resume

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def import_github_profile(request) -> JsonResponse:
    """Import GitHub profile data"""
    try:
        print("Request.method:", request.method)
        # Extract GitHub username from URL or direct input
        data = json.loads(request.body)
        github_input = data.get("github_url", "")
        print("GitHub input:", github_input)
        if not github_input:
            return JsonResponse({"error": "No GitHub URL provided"}, status=400)

        # Handle full GitHub URLs or just usernames
        if "/" in github_input:
            # Extract username from URL
            parts = github_input.rstrip("/").split("/")
            username = parts[-1]
            if username == "github.com" and len(parts) >= 3:
                username = parts[-2]
        else:
            username = github_input

        # Create importer and get data
        importer = GitHubProfileImporter(username)
        github_data = importer.import_profile()

        if not github_data:
            return JsonResponse({"error": "Failed to fetch GitHub profile"}, status=400)

        # Parse the JSON string
        github_data_json = json.loads(github_data)

        # Update user profile with GitHub data
        profile = request.user.userprofile
        profile.github_url = f"https://github.com/{username}"
        profile.github_data = github_data_json
        profile.last_github_refresh = timezone.now()

        # Extract bio/profile info
        if github_data_json.get("name") and not profile.name:
            profile.name = github_data_json.get("name")

        if github_data_json.get("bio") and not profile.professional_summary:
            profile.professional_summary = github_data_json.get("bio")

        if github_data_json.get("company") and not profile.company:
            profile.company = github_data_json.get("company")

        # Save profile updates
        profile.save()

        # Transform repositories into projects
        projects = importer.transform_repos_to_projects(
            github_data_json.get("repositories", []), profile
        )

        # Save projects
        for project_data in projects:
            # Check if project already exists (based on GitHub URL)
            existing_project = Project.objects.filter(
                profile=profile, github_url=project_data["github_url"]
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

        return JsonResponse(
            {
                "success": True,
                "message": f"Successfully imported GitHub profile for {username}. Added {len(projects)} projects.",
            }
        )

    except Exception as e:
        logger.error(f"Error importing GitHub profile: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
def import_resume(request):
    """Import resume data"""
    try:
        if "resume" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        resume_file = request.FILES["resume"]
        if not resume_file.name.endswith((".pdf", ".docx")):
            return JsonResponse(
                {"error": "Invalid file format. Please upload a PDF or DOCX file."}, status=400
            )

        # Parse resume
        importer = ResumeImporter(request.user.userprofile)

        if resume_file.name.endswith(".pdf"):
            resume_text = parse_pdf_resume(resume_file)
            result = importer.parse_resume_text(resume_text)
        else:
            # For non-PDF files, use the ResumeImporter directly
            result = importer.parse_resume_file(resume_file)

        if not result:
            return JsonResponse({"error": "Failed to parse resume"}, status=400)

        # Update user profile
        profile = request.user.userprofile

        # Apply basic info
        if result.get("name") and not profile.name:
            profile.name = result.get("name")

        if result.get("email"):
            profile.user.email = result.get("email")
            profile.user.save()

        if result.get("phone") and not profile.phone:
            profile.phone = result.get("phone")

        if result.get("location"):
            location = result.get("location", {})
            if location.get("city") and not profile.city:
                profile.city = location.get("city")
            if location.get("state") and not profile.state:
                profile.state = location.get("state")
            if location.get("country") and not profile.country:
                profile.country = location.get("country")

        if result.get("summary") and not profile.professional_summary:
            profile.professional_summary = result.get("summary")

        # Save profile
        profile.save()

        # Import work experiences
        experiences_added = 0
        for exp_data in result.get("work_experience", []):
            # Check if the experience already exists (based on company and position)
            existing_exp = WorkExperience.objects.filter(
                profile=profile,
                company__iexact=exp_data.get("company", ""),
                position__iexact=exp_data.get("position", ""),
            ).first()

            if not existing_exp:
                # Convert date strings to date objects
                start_date = datetime.strptime(
                    exp_data.get("start_date", "2000-01-01"), "%Y-%m-%d"
                ).date()
                end_date = None
                if exp_data.get("end_date"):
                    end_date = datetime.strptime(exp_data.get("end_date"), "%Y-%m-%d").date()

                # Create new experience
                WorkExperience.objects.create(
                    profile=profile,
                    company=exp_data.get("company", ""),
                    position=exp_data.get("position", ""),
                    start_date=start_date,
                    end_date=end_date,
                    current=exp_data.get("current", False),
                    description=exp_data.get("description", ""),
                )
                experiences_added += 1

        # Import education
        education_added = 0
        for edu_data in result.get("education", []):
            # Check if education already exists
            existing_edu = Education.objects.filter(
                profile=profile,
                institution__iexact=edu_data.get("institution", ""),
                degree__iexact=edu_data.get("degree", ""),
            ).first()

            if not existing_edu:
                # Convert date strings to date objects
                start_date = None
                end_date = None
                if edu_data.get("start_date"):
                    start_date = datetime.strptime(edu_data.get("start_date"), "%Y-%m-%d").date()
                if edu_data.get("end_date"):
                    end_date = datetime.strptime(edu_data.get("end_date"), "%Y-%m-%d").date()

                # Create new education
                Education.objects.create(
                    profile=profile,
                    institution=edu_data.get("institution", ""),
                    degree=edu_data.get("degree", ""),
                    field_of_study=edu_data.get("field_of_study", ""),
                    start_date=start_date,
                    end_date=end_date,
                    current=edu_data.get("current", False),
                )
                education_added += 1

        # Import skills
        skills_added = 0
        for skill_data in result.get("skills", []):
            skill_name = skill_data.get("name", "")
            if not skill_name:
                continue

            # Check if skill already exists
            existing_skill = Skill.objects.filter(
                profile=profile,
                name__iexact=skill_name,
            ).first()

            if not existing_skill:
                # Create new skill
                Skill.objects.create(
                    profile=profile,
                    name=skill_name,
                    category=skill_data.get("category", "other"),
                    proficiency=skill_data.get("proficiency", 3),
                )
                skills_added += 1

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"Successfully imported resume data. Added {experiences_added} work experiences, "
                    f"{education_added} education entries, and {skills_added} skills."
                ),
            }
        )

    except Exception as e:
        logger.error(f"Error importing resume: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
def import_linkedin_profile(request):
    """Import LinkedIn profile data"""
    try:
        if "linkedin_data" not in request.POST:
            return JsonResponse({"error": "No LinkedIn data provided"}, status=400)

        data = json.loads(request.body)
        linkedin_data = data.get("linkedin_data", "")

        if not linkedin_data:
            return JsonResponse({"error": "Empty LinkedIn data"}, status=400)

        # Parse the data
        try:
            data = json.loads(linkedin_data)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid LinkedIn data format"}, status=400)

        # Import the data
        importer = LinkedInImporter(request.user.userprofile)
        result = importer.parse_linkedin_data(data)

        if not result:
            return JsonResponse({"error": "Failed to parse LinkedIn data"}, status=400)

        # Update user profile
        profile = request.user.userprofile

        # Apply basic info
        if data.get("name") and not profile.name:
            profile.name = data.get("name")

        if data.get("headline") and not profile.headline:
            profile.headline = data.get("headline")

        if data.get("summary") and not profile.professional_summary:
            profile.professional_summary = data.get("summary")

        if data.get("location"):
            location = data.get("location", {})
            if not profile.city and location.get("city"):
                profile.city = location.get("city")
            if not profile.state and location.get("region"):
                profile.state = location.get("region")
            if not profile.country and location.get("country"):
                profile.country = location.get("country")

        if data.get("phoneNumbers") and not profile.phone:
            phone_numbers = data.get("phoneNumbers", [])
            if phone_numbers and len(phone_numbers) > 0:
                profile.phone = phone_numbers[0]

        # Update LinkedIn URL
        if data.get("url") and not profile.linkedin_url:
            profile.linkedin_url = data.get("url")

        # Current position
        positions = data.get("positions", [])
        if positions and len(positions) > 0:
            current_position = positions[0]
            if current_position.get("title") and not profile.current_position:
                profile.current_position = current_position.get("title")
            if current_position.get("company") and not profile.company:
                profile.company = current_position.get("company")

        # Save profile
        profile.save()

        # Import work experiences
        experiences_added = 0
        for position in positions:
            # Check if the experience already exists
            existing_exp = WorkExperience.objects.filter(
                profile=profile,
                company__iexact=position.get("company", ""),
                position__iexact=position.get("title", ""),
            ).first()

            if not existing_exp:
                # Convert date strings to date objects
                start_date = datetime.strptime(
                    position.get("startDate", "2000-01-01"), "%Y-%m-%d"
                ).date()
                end_date = None
                if position.get("endDate"):
                    end_date = datetime.strptime(position.get("endDate"), "%Y-%m-%d").date()

                # Create new experience
                WorkExperience.objects.create(
                    profile=profile,
                    company=position.get("company", ""),
                    position=position.get("title", ""),
                    location=position.get("location", ""),
                    start_date=start_date,
                    end_date=end_date,
                    current=position.get("current", False),
                    description=position.get("description", ""),
                )
                experiences_added += 1

        # Import education
        education_added = 0
        for edu in data.get("education", []):
            # Check if education already exists
            existing_edu = Education.objects.filter(
                profile=profile,
                institution__iexact=edu.get("school", ""),
                degree__iexact=edu.get("degree", ""),
            ).first()

            if not existing_edu:
                # Convert date strings to date objects
                start_date = None
                end_date = None
                if edu.get("startDate"):
                    start_date = datetime.strptime(edu.get("startDate"), "%Y-%m-%d").date()
                if edu.get("endDate"):
                    end_date = datetime.strptime(edu.get("endDate"), "%Y-%m-%d").date()

                # Create new education
                Education.objects.create(
                    profile=profile,
                    institution=edu.get("school", ""),
                    degree=edu.get("degree", ""),
                    field_of_study=edu.get("fieldOfStudy", ""),
                    start_date=start_date,
                    end_date=end_date,
                    current=edu.get("current", False),
                )
                education_added += 1

        # Import skills
        skills_added = 0
        for skill in data.get("skills", []):
            skill_name = skill.get("name", "")
            if not skill_name:
                continue

            # Check if skill already exists
            existing_skill = Skill.objects.filter(
                profile=profile,
                name__iexact=skill_name,
            ).first()

            if not existing_skill:
                # Create new skill
                Skill.objects.create(
                    profile=profile,
                    name=skill_name,
                    category="other",  # Default category
                    proficiency=3,  # Default middle proficiency
                )
                skills_added += 1

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"Successfully imported LinkedIn data. Added {experiences_added} work experiences, "
                    f"{education_added} education entries, and {skills_added} skills."
                ),
            }
        )

    except Exception as e:
        logger.error(f"Error importing LinkedIn profile: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
