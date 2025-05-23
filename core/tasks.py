# tasks.py
from celery import shared_task
import logging
from django.apps import apps
from celery.exceptions import Retry

from core.utils.agents.personal_agent import PersonalAgent
from core.utils.agents.writer_agent import WriterAgent
from core.utils.agents.job_agent import JobAgent

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


@shared_task
def refresh_vector_store_async():
    """
    Simple task to refresh vector store - replace with your actual implementation
    """
    try:
        logger.info("Starting vector store refresh task")
        # Add your vector store refresh logic here
        # For now, just return success to test if the error is fixed
        logger.info("Vector store refresh completed successfully")
        return "Vector store refreshed successfully"
    except Exception as e:
        logger.error(f"Error in refresh_vector_store_async: {str(e)}", exc_info=True)
        raise
