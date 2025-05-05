"""
Utilities for safe database operations.
"""

import logging

logger = logging.getLogger(__name__)


def safe_get_or_none(model_class, **kwargs):
    """
    Safely get a model instance or return None.

    Args:
        model_class: Django model class
        **kwargs: Lookup parameters

    Returns:
        Model instance or None if not found or error
    """
    try:
        return model_class.objects.get(**kwargs)
    except model_class.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error retrieving {model_class.__name__}: {str(e)}")
        return None


def safe_create(model_class, **kwargs):
    """
    Safely create a model instance.

    Args:
        model_class: Django model class
        **kwargs: Fields to set on the new instance

    Returns:
        Tuple of (object, created)
        object: Model instance or None if error
        created: Boolean - True if created, False if error
    """
    try:
        instance = model_class(**kwargs)
        instance.save()
        return instance, True
    except Exception as e:
        logger.error(f"Error creating {model_class.__name__}: {str(e)}")
        return None, False


def safe_update(instance, **kwargs):
    """
    Safely update a model instance.

    Args:
        instance: Model instance to update
        **kwargs: Fields to update

    Returns:
        Tuple of (object, updated)
        object: Updated instance or original instance if error
        updated: Boolean - True if updated, False if error
    """
    if not instance:
        return None, False

    try:
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance, True
    except Exception as e:
        logger.error(f"Error updating {instance.__class__.__name__} (id={instance.id}): {str(e)}")
        return instance, False


def safe_delete(instance):
    """
    Safely delete a model instance.

    Args:
        instance: Model instance to delete

    Returns:
        Boolean: True if deleted, False if error
    """
    if not instance:
        return False

    try:
        instance.delete()
        return True
    except Exception as e:
        logger.error(f"Error deleting {instance.__class__.__name__} (id={instance.id}): {str(e)}")
        return False


def safe_filter(model_class, **kwargs):
    """
    Safely filter model instances.

    Args:
        model_class: Django model class
        **kwargs: Filter parameters

    Returns:
        QuerySet or empty QuerySet if error
    """
    try:
        return model_class.objects.filter(**kwargs)
    except Exception as e:
        logger.error(f"Error filtering {model_class.__name__}: {str(e)}")
        return model_class.objects.none()


def safe_bulk_create(model_class, objects_list):
    """
    Safely bulk create model instances.

    Args:
        model_class: Django model class
        objects_list: List of model instances to create

    Returns:
        List of created instances or empty list if error
    """
    if not objects_list:
        return []

    try:
        return model_class.objects.bulk_create(objects_list)
    except Exception as e:
        logger.error(f"Error bulk creating {model_class.__name__}: {str(e)}")
        return []
