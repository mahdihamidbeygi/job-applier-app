"""
Form processing utilities for handling complex form submissions and field processing.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from django.http import HttpRequest

logger = logging.getLogger(__name__)


def extract_field_data(request: HttpRequest, content_type_json: bool = False) -> Dict[str, Any]:
    """
    Extract form data from a request, handling both JSON and form-encoded data.

    Args:
        request: The HTTP request
        content_type_json: Whether to force JSON content type processing

    Returns:
        Dict containing the extracted form data
    """
    if content_type_json or request.content_type == "application/json":
        try:
            return json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {str(e)}")
            return {}
    else:
        return request.POST.dict()


def process_form_fields(
    form_fields: List[Dict[str, Any]], field_processor: Any, skip_filled: bool = True
) -> Dict[str, Any]:
    """
    Process form fields using the provided field processor.

    Args:
        form_fields: List of field definitions
        field_processor: Object with methods to process different field types
        skip_filled: Whether to skip fields that already have values

    Returns:
        Dictionary mapping field IDs to their values
    """
    field_values = {}

    for field in form_fields:
        field_id = field.get("id")
        field_type = field.get("type")
        field_label = field.get("label")
        field_options = field.get("options", [])

        # Skip if required field information is missing
        if not field_id or not field_type or not field_label:
            continue

        # Skip if field is already filled and skip_filled is True
        if skip_filled and field.get("value"):
            field_values[field_id] = field.get("value")
            continue

        # Process field based on its type
        value = ""
        try:
            if field_type in ["text", "textarea", "email", "password", "tel", "url", "number"]:
                value = field_processor.fill_text_field(field_label)
            elif field_type in ["select", "radio"]:
                value = field_processor.select_option(field_label, field_options)
            elif field_type == "checkbox":
                value = field_processor.select_checkboxes(field_label, field_options)
            elif field_type == "date":
                value = field_processor.fill_date_field(field_label)
            elif field_type == "file":
                # Skip file fields as they typically need special handling
                continue
            else:
                # For unsupported field types, try the generic method if available
                if hasattr(field_processor, "fill_generic_field"):
                    value = field_processor.fill_generic_field(field_label, field_type)
        except Exception as e:
            logger.error(f"Error processing field {field_id} ({field_type}): {str(e)}")
            value = ""

        field_values[field_id] = value

    return field_values
