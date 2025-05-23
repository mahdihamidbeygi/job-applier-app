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
        # Extract GitHub username from URL or direct input
        data = json.loads(request.body)
        github_input = data.get("github_url", "")

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
        data = json.loads(request.body)
        linkedin_data = data.get("linkedin_data", {})
        linkedin_url = data.get("linkedin_url", "")

        # Validate input data
        if not linkedin_url:
            return JsonResponse({"error": "No URL provided"}, status=400)

        # If we have a URL but no data, attempt to use the importer
        if linkedin_url and not linkedin_data:
            importer = LinkedInImporter(linkedin_url=linkedin_url)
            result = importer.parse_linkedin_data()

            if not result:
                return JsonResponse({"error": "Failed to parse LinkedIn data from URL"}, status=400)

            linkedin_data = result

        # If we still don't have data, return error
        if not linkedin_data:
            return JsonResponse({"error": "No valid LinkedIn data found"}, status=400)

        # Update user profile
        profile = request.user.userprofile

        # Apply basic info with better error handling
        if linkedin_data.get("name") and not profile.name:
            profile.name = linkedin_data.get("name").strip()

        if linkedin_data.get("headline") and not profile.headline:
            profile.headline = linkedin_data.get("headline").strip()

        if linkedin_data.get("summary") and not profile.professional_summary:
            profile.professional_summary = linkedin_data.get("summary").strip()

        # Handle location data more robustly
        location_data = linkedin_data.get("location", {})
        if isinstance(location_data, dict):
            if location_data.get("city") and not profile.city:
                profile.city = location_data.get("city").strip()
            if location_data.get("region") and not profile.state:
                profile.state = location_data.get("region").strip()
            if location_data.get("country") and not profile.country:
                profile.country = location_data.get("country").strip()
        elif isinstance(location_data, str) and location_data.strip():
            # If location is a string, try to parse it
            if not profile.city:
                profile.city = location_data.strip()

        # Handle phone numbers
        phone_numbers = linkedin_data.get("phoneNumbers", [])
        if (
            phone_numbers
            and isinstance(phone_numbers, list)
            and len(phone_numbers) > 0
            and not profile.phone
        ):
            # Take the first phone number and clean it
            phone = phone_numbers[0] if isinstance(phone_numbers[0], str) else str(phone_numbers[0])
            profile.phone = phone.strip()

        # Update LinkedIn URL with validation
        provided_url = linkedin_data.get("url") or linkedin_url
        if provided_url and not profile.linkedin_url:
            # Ensure the URL is properly formatted
            if not provided_url.startswith("http"):
                provided_url = f"https://linkedin.com/in/{provided_url.lstrip('/')}"
            profile.linkedin_url = provided_url

        # Handle current position from positions array
        positions = linkedin_data.get("positions", [])
        if positions and isinstance(positions, list) and len(positions) > 0:
            current_position = positions[0]
            if isinstance(current_position, dict):
                if current_position.get("title") and not profile.current_position:
                    profile.current_position = current_position.get("title").strip()
                if current_position.get("company") and not profile.company:
                    profile.company = current_position.get("company").strip()

        # Save profile changes
        profile.save()

        # Import work experiences with better date handling
        experiences_added = 0
        for position in positions:
            if not isinstance(position, dict):
                continue

            company = position.get("company", "").strip()
            title = position.get("title", "").strip()

            if not company or not title:
                continue

            # Check if the experience already exists
            existing_exp = WorkExperience.objects.filter(
                profile=profile,
                company__iexact=company,
                position__iexact=title,
            ).first()

            if not existing_exp:
                try:
                    # Handle date parsing more robustly
                    start_date = None
                    end_date = None

                    start_date_str = position.get("startDate")
                    if start_date_str:
                        try:
                            if isinstance(start_date_str, str):
                                # Handle different date formats
                                if len(start_date_str) == 4:  # Just year
                                    start_date = datetime.strptime(
                                        f"{start_date_str}-01-01", "%Y-%m-%d"
                                    ).date()
                                elif len(start_date_str) == 7:  # Year-month
                                    start_date = datetime.strptime(
                                        f"{start_date_str}-01", "%Y-%m-%d"
                                    ).date()
                                else:  # Full date
                                    start_date = datetime.strptime(
                                        start_date_str, "%Y-%m-%d"
                                    ).date()
                        except ValueError:
                            logger.warning(f"Could not parse start date: {start_date_str}")

                    end_date_str = position.get("endDate")
                    if end_date_str:
                        try:
                            if isinstance(end_date_str, str):
                                # Handle different date formats
                                if len(end_date_str) == 4:  # Just year
                                    end_date = datetime.strptime(
                                        f"{end_date_str}-12-31", "%Y-%m-%d"
                                    ).date()
                                elif len(end_date_str) == 7:  # Year-month
                                    end_date = datetime.strptime(
                                        f"{end_date_str}-01", "%Y-%m-%d"
                                    ).date()
                                else:  # Full date
                                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            logger.warning(f"Could not parse end date: {end_date_str}")

                    # Create new work experience
                    WorkExperience.objects.create(
                        profile=profile,
                        company=company,
                        position=title,
                        location=position.get("location", "").strip(),
                        start_date=start_date,
                        end_date=end_date,
                        current=position.get("current", False),
                        description=position.get("description", "").strip(),
                    )
                    experiences_added += 1

                except Exception as e:
                    logger.warning(
                        f"Could not create work experience for {company} - {title}: {str(e)}"
                    )
                    continue

        # Import education with better error handling
        education_added = 0
        education_data = linkedin_data.get("education", [])
        if isinstance(education_data, list):
            for edu in education_data:
                if not isinstance(edu, dict):
                    continue

                institution = edu.get("school", "").strip()
                degree = edu.get("degree", "").strip()

                if not institution:
                    continue

                # Check if education already exists
                existing_edu = Education.objects.filter(
                    profile=profile,
                    institution__iexact=institution,
                    degree__iexact=degree,
                ).first()

                if not existing_edu:
                    try:
                        # Handle education date parsing
                        start_date = None
                        end_date = None

                        start_date_str = edu.get("startDate")
                        if start_date_str:
                            try:
                                if isinstance(start_date_str, str):
                                    if len(start_date_str) == 4:  # Just year
                                        start_date = datetime.strptime(
                                            f"{start_date_str}-09-01", "%Y-%m-%d"
                                        ).date()
                                    else:
                                        start_date = datetime.strptime(
                                            start_date_str, "%Y-%m-%d"
                                        ).date()
                            except ValueError:
                                logger.warning(
                                    f"Could not parse education start date: {start_date_str}"
                                )

                        end_date_str = edu.get("endDate")
                        if end_date_str:
                            try:
                                if isinstance(end_date_str, str):
                                    if len(end_date_str) == 4:  # Just year
                                        end_date = datetime.strptime(
                                            f"{end_date_str}-06-30", "%Y-%m-%d"
                                        ).date()
                                    else:
                                        end_date = datetime.strptime(
                                            end_date_str, "%Y-%m-%d"
                                        ).date()
                            except ValueError:
                                logger.warning(
                                    f"Could not parse education end date: {end_date_str}"
                                )

                        # Create new education entry
                        Education.objects.create(
                            profile=profile,
                            institution=institution,
                            degree=degree,
                            field_of_study=edu.get("fieldOfStudy", "").strip(),
                            start_date=start_date,
                            end_date=end_date,
                            current=edu.get("current", False),
                            description=edu.get("description", "").strip(),
                        )
                        education_added += 1

                    except Exception as e:
                        logger.warning(
                            f"Could not create education entry for {institution}: {str(e)}"
                        )
                        continue

        # Import skills with categorization
        skills_added = 0
        skills_data = linkedin_data.get("skills", [])
        if isinstance(skills_data, list):
            for skill in skills_data:
                if isinstance(skill, dict):
                    skill_name = skill.get("name", "").strip()
                elif isinstance(skill, str):
                    skill_name = skill.strip()
                else:
                    continue

                if not skill_name:
                    continue

                # Check if skill already exists
                existing_skill = Skill.objects.filter(
                    profile=profile,
                    name__iexact=skill_name,
                ).first()

                if not existing_skill:
                    try:
                        # Try to categorize the skill
                        category = "other"  # Default category

                        # Simple skill categorization
                        skill_lower = skill_name.lower()
                        if any(
                            tech in skill_lower
                            for tech in [
                                "python",
                                "java",
                                "javascript",
                                "react",
                                "node",
                                "sql",
                                "html",
                                "css",
                                "git",
                            ]
                        ):
                            category = "technical"
                        elif any(
                            lang in skill_lower
                            for lang in ["spanish", "french", "german", "chinese", "language"]
                        ):
                            category = "language"
                        elif any(
                            soft in skill_lower
                            for tech in [
                                "leadership",
                                "communication",
                                "management",
                                "teamwork",
                                "problem solving",
                            ]
                        ):
                            category = "soft"

                        # Create new skill
                        Skill.objects.create(
                            profile=profile,
                            name=skill_name,
                            category=category,
                            proficiency=(
                                skill.get("proficiency", 3) if isinstance(skill, dict) else 3
                            ),
                        )
                        skills_added += 1

                    except Exception as e:
                        logger.warning(f"Could not create skill {skill_name}: {str(e)}")
                        continue

        # Import certifications if available
        certifications_added = 0
        certifications_data = linkedin_data.get("certifications", [])
        if isinstance(certifications_data, list):
            for cert in certifications_data:
                if not isinstance(cert, dict):
                    continue

                name = cert.get("name", "").strip()
                issuer = cert.get("issuer", "").strip()

                if not name:
                    continue

                # Check if certification already exists
                existing_cert = Certification.objects.filter(
                    profile=profile,
                    name__iexact=name,
                    issuing_authority__iexact=issuer,
                ).first()

                if not existing_cert:
                    try:
                        # Handle certification date
                        issue_date = None
                        expiry_date = None

                        issue_date_str = cert.get("issueDate")
                        if issue_date_str:
                            try:
                                issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d").date()
                            except ValueError:
                                logger.warning(
                                    f"Could not parse certification issue date: {issue_date_str}"
                                )

                        expiry_date_str = cert.get("expiryDate")
                        if expiry_date_str:
                            try:
                                expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
                            except ValueError:
                                logger.warning(
                                    f"Could not parse certification expiry date: {expiry_date_str}"
                                )

                        # Create new certification
                        Certification.objects.create(
                            profile=profile,
                            name=name,
                            issuing_authority=issuer,
                            issue_date=issue_date,
                            expiry_date=expiry_date,
                            credential_id=cert.get("credentialId", "").strip(),
                            credential_url=cert.get("credentialUrl", "").strip(),
                        )
                        certifications_added += 1

                    except Exception as e:
                        logger.warning(f"Could not create certification {name}: {str(e)}")
                        continue

        # Store the raw LinkedIn data for future reference
        profile.linkedin_data = linkedin_data
        profile.last_linkedin_refresh = timezone.now()
        profile.save()

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"Successfully imported LinkedIn data. Added {experiences_added} work experiences, "
                    f"{education_added} education entries, {skills_added} skills, and {certifications_added} certifications."
                ),
                "stats": {
                    "experiences_added": experiences_added,
                    "education_added": education_added,
                    "skills_added": skills_added,
                    "certifications_added": certifications_added,
                },
            }
        )

    except json.JSONDecodeError:
        logger.error("Invalid JSON data provided")
        return JsonResponse({"error": "Invalid JSON data provided"}, status=400)
    except Exception as e:
        logger.error(f"Error importing LinkedIn profile: {str(e)}")
        return JsonResponse({"error": f"Failed to import LinkedIn profile: {str(e)}"}, status=500)
