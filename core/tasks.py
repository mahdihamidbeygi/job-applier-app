import logging

from core.models import JobListing, UserProfile
from core.utils.agents.personal_agent import PersonalAgent, PersonalBackground
from job_applier.celery_config import app

from .utils.agents.assistant_agent import AssistantAgent as PrimaryProcessor

logger = logging.getLogger(__name__)


@app.task
# import html  # Used for HTML-escaping user input to prevent log injection
def refresh_vector_store_async(user_id: int):
    """
    Asynchronously refresh the RAG vector store for a user using the primary processor.
    """
    logger.info(f"Starting async vector store refresh for user {html.escape(str(user_id))}")
    try:
        processor = PrimaryProcessor(user_id=user_id)  # Use the chosen processor
        success = processor.refresh_vectorstore()
        if success:
            logger.info(f"Successfully refreshed vector store for user {html.escape(str(user_id))}")
        else:
            logger.error(f"Failed to refresh vector store for user {html.escape(str(user_id))}")
    except Exception as e:
        logger.exception(
            f"Error during async vector store refresh for user {html.escape(str(user_id))}: {e}"
        )
        raise
