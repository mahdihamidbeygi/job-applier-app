# tasks.py
from celery import shared_task
import logging
from django.apps import apps

from core.utils.agents.personal_agent import PersonalAgent
from core.utils.agents.writer_agent import WriterAgent
from core.utils.agents.job_agent import JobAgent
from core.utils.agents.assistant_agent import AssistantAgent
from core.utils.profile_importers import GitHubProfileImporter
from core.models.profile import UserProfile, Project
from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_resume_for_job_task(self, user_id: int, job_listing_id: int):
    """
    Celery task to generate a tailored resume for a given job listing.
    """
    try:
        # Get model dynamically to avoid circular imports
        JobListing = apps.get_model("core", "JobListing")

        logger.info(
            f"Celery task: Starting resume generation for user_id: {user_id}, job_listing_id: {job_listing_id}"
        )

        # Check if job listing exists (no user_id filter since JobListing doesn't have it)
        job_listing = JobListing.objects.filter(id=job_listing_id).first()
        if not job_listing:
            logger.warning(
                f"Celery task: JobListing with id {job_listing_id} not found. Skipping resume generation."
            )
            return f"JobListing {job_listing_id} not found."

        if job_listing.tailored_resume:
            logger.info(
                f"Celery task: JobListing with id {job_listing_id} already has a tailored resume. Skipping."
            )
            return f"JobListing {job_listing_id} already has resume."

        # Initialize agents
        personal_agent = PersonalAgent(user_id=user_id)
        job_agent = JobAgent(user_id=user_id, job_id=job_listing_id)
        writer_agent = WriterAgent(
            user_id=user_id,
            personal_agent=personal_agent,
            job_agent=job_agent,
        )

        # Generate resume
        writer_agent.generate_resume()

        logger.info(
            f"Celery task: Resume generation process completed for job_listing_id: {job_listing_id}"
        )
        return f"Resume generated for JobListing {job_listing_id}."

    except Exception as e:
        logger.error(
            f"Celery task: Error generating resume for user_id: {user_id}, job_listing_id: {job_listing_id}. Error: {str(e)}",
            exc_info=True,
        )
        # Check if we should retry
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (2**self.request.retries))  # Exponential backoff
        else:
            logger.error(f"Task failed after {self.max_retries} retries")
            raise


# @shared_task(bind=True, max_retries=3, default_retry_delay=60 * 5)  # Retry after 5 mins
# def refresh_vector_store_async(self, user_id: int):
#     """
#     Celery task to refresh the vector store for a given user.
#     """
#     try:
#         logger.info(f"Task refresh_vector_store_async started for user_id: {user_id}")
#         agent = AssistantAgent(user_id=user_id)
#         refreshed = agent.refresh_vectorstore()  # This method must exist on AssistantAgent

#         if refreshed:
#             logger.info(f"Successfully refreshed vector store for user_id: {user_id}")
#         else:
#             logger.warning(
#                 f"Vector store refresh may not have completed successfully for user_id: {user_id}"
#             )
#         return f"Vector store refresh process completed for user {user_id}."
#     except Exception as exc:
#         logger.error(f"Error refreshing vector store for user_id {user_id}: {exc}", exc_info=True)
#         raise self.retry(exc=exc)


@shared_task(
    bind=True, max_retries=3, default_retry_delay=5 * 60
)  # Retry up to 3 times, with 5 min delay
def process_github_profile_import(self, user_id):
    """
    Celery task to import GitHub profile data for a given user.
    """
    try:
        userprofile: UserProfile = UserProfile.objects.get(id=user_id)
        logger.info(f"Starting GitHub profile import for user_id: {user_id}")

        github_url: str = userprofile.github_url
        github_username = github_url.split("/")[-1]
        if github_username == "github.com":
            github_username: str = github_url.split("/")[-2]

        # Import GitHub profile
        importer = GitHubProfileImporter(github_username)
        github_data = importer.import_profile()

        # Transform repositories into projects
        projects = importer.transform_repos_to_projects(
            github_data.get("repositories", []), userprofile
        )

        # Save projects
        for project_data in projects:
            # Check if project already exists (based on GitHub URL)
            existing_project: Project | None = Project.objects.filter(
                profile=userprofile, github_url=project_data["github_url"]
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
        userprofile.github_data = github_data
        userprofile.last_github_refresh = timezone.now()
        userprofile.save()
        logger.info(
            f"Successfully imported GitHub profile for user_id: {user_id}. Data snippet: {str(github_data)[:200]}..."
        )
        return f"GitHub profile import successful for user_id: {user_id}"
    except User.DoesNotExist:
        logger.warning(
            f"User with id {user_id} not found for GitHub profile import. Task will not retry."
        )
        return f"User with id {user_id} not found."
    except Exception as exc:
        logger.error(
            f"Error during GitHub profile import for user_id {user_id}: {exc}", exc_info=True
        )
        # Retry the task if it's not a User.DoesNotExist error and retries are left
        raise self.retry(exc=exc)
