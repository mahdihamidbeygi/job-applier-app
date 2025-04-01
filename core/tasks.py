import logging

from celery import shared_task

from core.models import JobListing, UserProfile
from core.utils.agents.personal_agent import PersonalAgent, PersonalBackground

logger = logging.getLogger(__name__)


@shared_task
def generate_documents_async(job_id: int, user_id: int):
    """
    Asynchronously generate tailored documents for a job listing.

    Args:
        job_id (int): The ID of the job listing
        user_id (int): The ID of the user
    """
    try:
        # Get the job listing
        job_listing: JobListing = JobListing.objects.get(id=job_id)
        user_profile: UserProfile = UserProfile.objects.get(user_id=user_id)

        # Initialize agents
        personal_agent = PersonalAgent(user_id)

        # Load user background
        background = PersonalBackground(
            profile=user_profile.__dict__,
            work_experience=list(user_profile.work_experiences.values()),
            education=list(user_profile.education.values()),
            skills=list(user_profile.skills.values()),
            projects=list(user_profile.projects.values()),
            github_data={},  # We'll implement GitHub data fetching later
            achievements=[],  # We'll add this field to the model later
            interests=[],  # We'll add this field to the model later
        )
        personal_agent.load_background(background)

        # Generate documents
        logger.info(f"Generating documents for job {job_id}")
        success: bool = personal_agent.generate_tailored_documents(job_listing)

        if not success:
            logger.error(f"Failed to generate documents for job {job_id}")

    except Exception as e:
        logger.error(f"Error in generate_documents_async task: {str(e)}")
        raise
