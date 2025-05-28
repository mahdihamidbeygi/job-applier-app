"""
Views for importing profile data from various sources.
"""

from typing import Optional
import json
import logging
from datetime import datetime

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import Certification, Education, Project, Publication, Skill, WorkExperience
from core.utils.profile_importers import GitHubProfileImporter, LinkedInImporter, ResumeImporter

logger = logging.getLogger(__name__)


def parse_flexible_date(
    date_str: Optional[str], field_name: str = "date"
) -> Optional[datetime.date]:
    """
    Parses a date string that can be in YYYY-MM-DD, YYYY-MM, or YYYY format.
    Returns a date object or None if parsing fails or input is None.
    """
    if not date_str:
        return None
    try:
        if len(date_str) == 10:  # YYYY-MM-DD
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        elif len(date_str) == 7:  # YYYY-MM
            # Assume the 1st of the month
            return datetime.strptime(date_str + "-01", "%Y-%m-%d").date()
        elif len(date_str) == 4:  # YYYY
            # Assume January 1st
            return datetime.strptime(date_str + "-01-01", "%Y-%m-%d").date()
        else:
            logger.warning(
                f"Date string '{date_str}' for field '{field_name}' has an unsupported format/length."
            )
            return None
    except ValueError:
        logger.warning(f"Could not parse {field_name}: '{date_str}'. Invalid date format.")
        return None


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
def import_resume(request) -> JsonResponse:
    """Import resume data"""
    try:
        if "resume" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        resume_file = request.FILES["resume"]

        try:
            # resume_file is an UploadedFile object (e.g., InMemoryUploadedFile)
            with ResumeImporter(resume_file) as importer:  # Use as context manager
                result = importer.parse_resume()
        except Exception as e:  # Catch exceptions from ResumeImporter init or parse
            logger.error(f"Error during resume import process: {str(e)}")  # This logs the error
            return JsonResponse({"error": f"Failed to process resume: {str(e)}"}, status=500)

        if not result:
            return JsonResponse({"error": "Failed to parse resume"}, status=400)

        # Update user profile
        profile = request.user.userprofile

        # Apply personal_info
        personal_info = result.get("basic_info", {})
        profile_updated = False

        if personal_info.get("name") and not profile.name:
            profile.name = personal_info.get("name")
            profile_updated = True

        if personal_info.get("title") and not profile.title:
            profile.title = personal_info.get("title")
            profile_updated = True

        if personal_info.get("email"):
            if profile.user.email != personal_info.get("email"):
                profile.user.email = personal_info.get("email")
                profile.user.save(update_fields=["email"])
                # No need to set profile_updated = True here, as user is saved separately

        if personal_info.get("phone") and not profile.phone:
            profile.phone = personal_info.get("phone")
            profile_updated = True

        if personal_info.get("address") and not profile.address:
            profile.address = personal_info.get("address", None)
            profile_updated = True
        if personal_info.get("city") and not profile.city:
            profile.city = personal_info.get("city", None)
            profile_updated = True
        if personal_info.get("state") and not profile.state:
            profile.state = personal_info.get("state", None)
            profile_updated = True
        if personal_info.get("country") and not profile.country:
            profile.country = personal_info.get("country", None)
            profile_updated = True
        if personal_info.get("postal_code") and not profile.postal_code:
            profile.postal_code = personal_info.get("postal_code")
            profile_updated = True

        # Assuming professional_summary is part of basic_info as per your LLM prompt
        if personal_info.get("professional_summary") and not profile.professional_summary:
            profile.professional_summary = personal_info.get("professional_summary")
            profile_updated = True

        # Add other fields from UserProfile that might be in basic_info
        if personal_info.get("website") and not profile.website:
            profile.website = personal_info.get("website")
            profile_updated = True
        # Note: github_url and linkedin_url are typically handled by their specific importers
        # but if the resume contains them and they are not set, we can update.
        if personal_info.get("github_url") and not profile.github_url:
            profile.github_url = personal_info.get("github_url")
            profile_updated = True
        if personal_info.get("linkedin_url") and not profile.linkedin_url:
            profile.linkedin_url = personal_info.get("linkedin_url")
            profile_updated = True

        if personal_info.get("headline") and not profile.headline:
            profile.headline = personal_info.get("headline")
            profile_updated = True
        if personal_info.get("current_position") and not profile.current_position:
            profile.current_position = personal_info.get("current_position")
            profile_updated = True
        if personal_info.get("company") and not profile.company:
            profile.company = personal_info.get("company")
            profile_updated = True

        # Save profile
        if profile_updated:
            profile.save()

        # Import work experiences
        experiences_added = 0
        for exp_data in result.get("work_experiences", []):
            # Check if the experience already exists (based on company and position)
            existing_exp = WorkExperience.objects.filter(
                profile=profile,
                company__iexact=exp_data.get("company", None),
                position__iexact=exp_data.get("position", None),
            ).first()

            if not existing_exp:
                start_date = parse_flexible_date(
                    exp_data.get("start_date"), "work experience start_date"
                )
                # Default start_date if not provided or unparseable, as per original logic
                if start_date is None and not exp_data.get("start_date"):
                    start_date = datetime.strptime("2000-01-01", "%Y-%m-%d").date()

                end_date = parse_flexible_date(exp_data.get("end_date"), "work experience end_date")

                # Create new experience
                WorkExperience.objects.create(
                    profile=profile,
                    company=exp_data.get("company", None),
                    position=exp_data.get("position", None),
                    location=exp_data.get("location", None),
                    start_date=start_date,
                    end_date=end_date,
                    current=exp_data.get("current", False),
                    description=exp_data.get("description", None),
                    achievements=exp_data.get("achievements", None),
                    technologies=exp_data.get("technologies", None),
                    # 'order' field has a default and is usually not set by LLM
                )
                experiences_added += 1

        # Import education
        education_added = 0
        for edu_data in result.get("education", []):
            # Check if education already exists
            existing_edu = Education.objects.filter(
                profile=profile,
                institution__iexact=edu_data.get("institution", None),
                degree__iexact=edu_data.get("degree", None),
            ).first()

            if not existing_edu:
                start_date = parse_flexible_date(edu_data.get("start_date"), "education start_date")
                end_date = parse_flexible_date(edu_data.get("end_date"), "education end_date")

                # Create new education
                Education.objects.create(
                    profile=profile,
                    institution=edu_data.get("institution", None),
                    degree=edu_data.get("degree", None),
                    field_of_study=edu_data.get("field_of_study", None),
                    start_date=start_date,
                    end_date=end_date,
                    current=edu_data.get("current", False),
                )
                education_added += 1

        # Import projects
        project_added = 0
        for project_data in result.get("projects", []):
            project_title = project_data.get("title", None)
            if not project_title:
                continue

            # Check if project already exists (e.g., by title)
            existing_project = Project.objects.filter(
                profile=profile,
                title__iexact=project_title,
            ).first()

            if not existing_project:
                start_date = parse_flexible_date(
                    project_data.get("start_date"), "project start_date"
                )
                end_date = parse_flexible_date(project_data.get("end_date"), "project end_date")

                Project.objects.create(
                    profile=profile,
                    title=project_title,
                    description=project_data.get("description", None),
                    technologies=project_data.get("technologies", None),
                    start_date=start_date,
                    end_date=end_date,
                    current=project_data.get("current", False),
                    github_url=project_data.get("github_url", None),
                    live_url=project_data.get("live_url", None),
                )
                project_added += 1

        # Import certifications
        certification_added = 0
        for cert_data in result.get("certifications", []):
            cert_name = cert_data.get("name", "")
            if not cert_name:  # Skips if name is None or empty string
                continue

            # Prepare issuer for comparison and saving
            issuer_val = cert_data.get("issuer")
            issuer_to_save = issuer_val if issuer_val is not None else ""

            # Check if certification already exists using prepared values
            existing_cert = Certification.objects.filter(
                profile=profile,
                name__iexact=cert_name,
                issuer__iexact=issuer_to_save,
            ).first()

            if not existing_cert:
                issue_date = parse_flexible_date(
                    cert_data.get("issue_date"), "certification issue_date"
                )
                expiry_date = parse_flexible_date(
                    cert_data.get("expiry_date"), "certification expiry_date"
                )

                # Prepare credential_id for saving, ensuring it's not None
                credential_id_val = cert_data.get("credential_id")
                credential_id_to_save = credential_id_val if credential_id_val is not None else ""

                # Prepare credential_url for saving, ensuring it's not None
                credential_url_val = cert_data.get("credential_url")
                credential_url_to_save = (
                    credential_url_val if credential_url_val is not None else ""
                )

                Certification.objects.create(
                    profile=profile,
                    name=cert_name,
                    issuer=issuer_to_save,  # Use the prepared value
                    issue_date=issue_date,
                    expiry_date=expiry_date,
                    credential_id=credential_id_to_save,  # Use the prepared value
                    credential_url=credential_url_to_save,  # Use the prepared value
                )
                certification_added += 1

        # Import publications
        publication_added = 0
        for pub_data in result.get("publications", []):
            pub_title = pub_data.get("title", "")
            if not pub_title:
                continue

            # Check if publication already exists
            existing_pub = Publication.objects.filter(
                profile=profile,
                title__iexact=pub_title,
                # authors__iexact=pub_data.get("authors", ""), # Authors can be tricky for exact match
            ).first()

            if not existing_pub:
                publication_date = parse_flexible_date(
                    pub_data.get("publication_date"), "publication_date"
                )

                Publication.objects.create(
                    profile=profile,
                    title=pub_title,
                    authors=pub_data.get("authors", None),
                    publication_date=publication_date,
                    publisher=pub_data.get("publisher", None),
                    journal=pub_data.get("journal", None),
                    doi=pub_data.get("doi", None),
                    url=pub_data.get("url", None),
                    abstract=pub_data.get("abstract", None),
                )
                publication_added += 1

        # Import skills
        skills_added = 0
        for skill_data in result.get("skills", []):
            skill_name = skill_data.get("name", None)
            if not skill_name:
                continue

            # Check if skill already exists
            existing_skill = Skill.objects.filter(
                profile=profile,
                name__iexact=skill_name,
            ).first()

            if not existing_skill:
                # Prepare proficiency, ensuring it's not None
                proficiency_val = skill_data.get("proficiency")
                proficiency_to_save = (
                    proficiency_val if proficiency_val is not None else 3
                )  # Default to 3 if None

                # Create new skill
                Skill.objects.create(
                    profile=profile,
                    name=skill_name,
                    category=skill_data.get("category", "other"),
                    proficiency=proficiency_to_save,
                )
                skills_added += 1

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"Successfully imported resume data. Added: "
                    f"{experiences_added} work experiences, {education_added} education entries, "
                    f"{project_added} projects, {certification_added} certifications, "
                    f"{publication_added} publications, and {skills_added} skills."
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
