from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

from core.models import (
    UserProfile,
    WorkExperience,
    Education,
    Project,
    Certification,
    Publication,
    Skill,
    JobListing,
    ChatMessage,  # Assuming ChatMessage changes might also warrant a refresh
)
from core.tasks import refresh_vector_store_async

logger = logging.getLogger(__name__)


def get_user_id_from_instance(instance):
    """
    Helper function to extract user_id from various model instances.
    """
    if hasattr(instance, "user_id") and instance.user_id is not None:
        return instance.user_id
    if hasattr(instance, "user") and hasattr(
        instance.user, "id"
    ):  # e.g., UserProfile instance itself
        return instance.user.id
    if hasattr(instance, "profile") and hasattr(
        instance.profile, "user_id"
    ):  # e.g., WorkExperience, Education etc.
        return instance.profile.user_id
    logger.debug(
        f"Could not directly find user_id or profile.user_id on instance of {type(instance)}"
    )
    return None


def refresh_vector_store_on_update(sender, instance, **kwargs):
    """
    Signal handler to trigger vector store refresh when monitored models change.
    """
    user_id = get_user_id_from_instance(instance)

    if user_id:
        try:
            created = kwargs.get("created", False)  # For post_save
            action = "created/updated" if kwargs.get("signal") == post_save else "deleted"
            if (
                kwargs.get("signal") == post_save
                and not created
                and not kwargs.get("update_fields")
            ):
                action = "updated (full save)"

            logger.info(
                f"Signal received: {sender.__name__} instance (ID: {instance.pk}) was {action}. "
                f"Queueing vector store refresh for user_id: {user_id}."
            )
            refresh_vector_store_async.delay(user_id=user_id)
        except Exception as e:
            logger.error(
                f"Error queueing vector store refresh for user_id {user_id} "
                f"triggered by {sender.__name__} (ID: {instance.pk}): {e}",
                exc_info=True,
            )
    else:
        logger.warning(
            f"Could not determine user_id from instance of {sender.__name__} (ID: {instance.pk}). "
            f"Vector store refresh not queued."
        )
