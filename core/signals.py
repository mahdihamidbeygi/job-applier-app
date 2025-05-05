# core/signals.py
import logging

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import (
    Certification,
    Education,
    Project,
    Publication,
    Skill,
    UserProfile,
    WorkExperience,
)

# Import other relevant profile models if needed
from .utils.agents.assistant_agent import AssistantAgent as PrimaryProcessor

logger = logging.getLogger(__name__)

# List of models that should trigger a vector store refresh
PROFILE_RELATED_MODELS = [
    UserProfile,
    WorkExperience,
    Education,
    Project,
    Skill,
    Certification,
    Publication,
]


@receiver(post_save, sender=User)  # Also trigger on User model changes (like email)
@receiver(post_save, sender=UserProfile)
@receiver(post_save, sender=WorkExperience)
@receiver(post_save, sender=Education)
@receiver(post_save, sender=Project)
@receiver(post_save, sender=Skill)
@receiver(post_save, sender=Certification)
@receiver(post_save, sender=Publication)
def refresh_vector_store_on_update(sender, instance, created, **kwargs):
    """
    Signal handler to refresh the RAG vector store when profile-related data changes.
    """
    user_id = None
    model_name = sender.__name__

    try:
        if isinstance(instance, User):
            user_id = instance.id
        elif hasattr(instance, "user"):  # For UserProfile
            user_id = instance.user.id
        elif hasattr(instance, "profile") and hasattr(
            instance.profile, "user"
        ):  # For related models like WorkExperience
            user_id = instance.profile.user.id
        else:
            # Use string formatting to sanitize the log message
            logger.warning(
                "Could not determine user_id for updated %s instance %s", model_name, instance.pk
            )
            return

        if user_id:
            # Use string formatting to sanitize the log message
            logger.info(
                "Detected change in %s for user %s. Triggering vector store refresh.",
                model_name,
                user_id,
            )

            # Option 1: Synchronous Refresh (Simpler, might block request)
            # from .utils.rag import RAGProcessor
            # try:
            #     rag_processor = RAGProcessor(user_id=user_id)
            #     rag_processor.refresh_vectorstore()
            #     logger.info("Successfully refreshed vector store for user %s", user_id)
            # except Exception as e:
            #     logger.error("Error refreshing vector store for user %s: %s", user_id, e)

            # Option 2: Asynchronous Refresh (Recommended for performance)
            from .tasks import refresh_vector_store_async  # Create this task

            refresh_vector_store_async.delay(user_id)
            logger.info("Queued async vector store refresh for user %s", user_id)

    except Exception as e:
        # Use string formatting to sanitize the log message
        logger.error(
            "Error in signal handler refresh_vector_store_on_update for %s: %s", model_name, e
        )
