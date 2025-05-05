"""
Schema API views.
"""

from django.http import JsonResponse, HttpResponseNotFound
from django.apps import apps
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.models.base import TimestampMixin


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def model_schema(request: Request, model_name: str) -> Response:
    """
    Get JSON schema for a specific model.

    Args:
        request: The HTTP request
        model_name: The name of the model to get schema for

    Returns:
        JSON response with the model schema
    """
    # Try to find the model
    for app_config in apps.get_app_configs():
        try:
            model = apps.get_model(app_config.label, model_name)

            # Use TimestampMixin's schema generation for any model
            schema = TimestampMixin._generate_basic_schema(model)
            return Response(schema)

        except LookupError:
            continue

    return Response({"error": f"Model '{model_name}' not found"}, status=404)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def app_models_schemas(request: Request, app_name: str = "core") -> Response:
    """
    Get JSON schemas for all models in an app.

    Args:
        request: The HTTP request
        app_name: The name of the app to get schemas for (default: 'core')

    Returns:
        JSON response with all model schemas
    """
    try:
        # Get all models' schemas for the specified app
        exclude = request.query_params.get("exclude", "").split(",")
        exclude = [model_name for model_name in exclude if model_name]

        include_abstract = request.query_params.get("include_abstract", "false").lower() == "true"

        schemas = TimestampMixin.get_app_schemas(
            app_label=app_name, exclude_models=exclude, include_abstract=include_abstract
        )

        return Response(schemas)
    except LookupError:
        return Response({"error": f"App '{app_name}' not found"}, status=404)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def all_models_schemas(request: Request) -> Response:
    """
    Get JSON schemas for all models in all apps.

    Args:
        request: The HTTP request

    Returns:
        JSON response with all model schemas grouped by app
    """
    result = {}

    for app_config in apps.get_app_configs():
        try:
            app_label = app_config.label
            # Skip Django's built-in apps unless explicitly requested
            if app_label.startswith("django.") and not request.query_params.get(
                "include_django", False
            ):
                continue

            # Get schemas for this app
            app_schemas = TimestampMixin.get_app_schemas(app_label=app_label)

            if app_schemas:  # Only include apps with models
                result[app_label] = app_schemas
        except Exception as e:
            # Skip apps with errors
            print(f"Error getting schemas for app {app_config.label}: {str(e)}")
            continue

    return Response(result)
