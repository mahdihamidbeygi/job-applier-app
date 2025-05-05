import logging
from typing import Tuple

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db import transaction

from core.models import ChatConversation, JobListing
from core.models.misc import LangGraphCheckpoint
from core.utils.agents.assistant_agent import AssistantAgent  # Or RAGProcessor if you use that

logger = logging.getLogger(__name__)
User = get_user_model()


@transaction.atomic
def clear_all_user_data(user_id: int) -> Tuple[bool, str]:
    """
    Deletes all JobListing and ChatConversation data for a given user,
    including associated files, LangGraph checkpoints, and refreshes the vector store.

    Args:
        user_id: The ID of the user whose data should be cleared.

    Returns:
        A tuple containing:
        - bool: True if successful, False otherwise.
        - str: A status message.
    """
    try:
        # 1. Verify User Exists
        try:
            user = User.objects.get(id=user_id)
            logger.info(f"Starting data cleanup for user: {user.username} (ID: {user_id})")
        except User.DoesNotExist:
            return False, f"User with ID {user_id} not found."

        # 2. Get Job Listings and Associated Files
        jobs_to_delete = JobListing.objects.filter(user_id=user_id)
        job_count = jobs_to_delete.count()
        files_to_delete = []
        for job in jobs_to_delete:
            if job.tailored_resume and job.tailored_resume.name:
                files_to_delete.append(job.tailored_resume.name)
            if job.tailored_cover_letter and job.tailored_cover_letter.name:
                files_to_delete.append(job.tailored_cover_letter.name)

        # 3. Get Conversation IDs for Checkpoint Deletion
        conversations_to_delete = ChatConversation.objects.filter(user_id=user_id)
        conversation_count = conversations_to_delete.count()
        # Convert IDs to strings as thread_id in LangGraphCheckpoint is likely a string
        conversation_ids_str = [str(conv.id) for conv in conversations_to_delete]

        # 4. Delete Associated Files from Storage
        deleted_files_count = 0
        for file_path in files_to_delete:
            try:
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
                    deleted_files_count += 1
                    logger.debug(f"Deleted file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete file {file_path}: {e}")

        # 5. Delete JobListing Records
        deleted_jobs_count, _ = jobs_to_delete.delete()
        logger.info(f"Deleted {deleted_jobs_count} JobListing records.")

        # 6. Delete ChatConversation Records (and associated ChatMessages via cascade)
        deleted_convos_count, _ = conversations_to_delete.delete()
        logger.info(f"Deleted {deleted_convos_count} ChatConversation records.")

        # 7. Delete LangGraph Checkpoints
        checkpoints_to_delete = LangGraphCheckpoint.objects.filter(
            thread_id__in=conversation_ids_str
        )
        checkpoint_count = checkpoints_to_delete.count()
        deleted_checkpoints_count, _ = checkpoints_to_delete.delete()
        logger.info(f"Deleted {deleted_checkpoints_count} LangGraphCheckpoint records.")

        # 8. Refresh Vector Store
        # Instantiate the processor used (AgenticRAGProcessor seems more current)
        # This will rebuild the vector store based on the now-empty DB records
        try:
            rag_processor = AssistantAgent(user_id=user_id)
            refreshed = rag_processor.refresh_vectorstore()
            if refreshed:
                logger.info("Successfully refreshed vector store.")
            else:
                logger.warning("Failed to refresh vector store after cleanup.")
        except Exception as e:
            logger.error(f"Error refreshing vector store for user {user_id}: {e}")
            # Continue even if vector store refresh fails, DB is clean

        success_message = (
            f"Successfully cleared data for user {user_id}: "
            f"{deleted_jobs_count}/{job_count} jobs, "
            f"{deleted_convos_count}/{conversation_count} conversations, "
            f"{deleted_checkpoints_count}/{checkpoint_count} checkpoints, "
            f"{deleted_files_count}/{len(files_to_delete)} files."
        )
        logger.info(success_message)
        return True, success_message

    except Exception as e:
        logger.exception(f"Error during data cleanup for user {user_id}: {e}")
        # Transaction will be rolled back automatically due to the exception
        return False, f"An error occurred during cleanup: {e}"
