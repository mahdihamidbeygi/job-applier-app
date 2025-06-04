"""
Enhanced utility views for profile management with automatic date conversion.
"""

import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt

from core.forms import (
    CertificationForm,
    EducationForm,
    ProjectForm,
    PublicationForm,
    SkillForm,
    WorkExperienceForm,
)
from core.models import (
    Certification,
    Education,
    Project,
    Publication,
    Skill,
    UserProfile,
    WorkExperience,
)
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.resume_composition import ResumeComposition

logger = logging.getLogger(__name__)


@login_required
def delete_item(request, model_name, item_id):
    """Delete an item from user profile"""
    # Map record types to models
    models = {
        WorkExperience().model_name: WorkExperience,
        Project().model_name: Project,
        Education().model_name: Education,
        Certification().model_name: Certification,
        Publication().model_name: Publication,
        Skill().model_name: Skill,
    }

    if model_name not in models:
        return JsonResponse(
            {"success": False, "error": f"Invalid model type: {model_name}"}, status=400
        )

    model = models[model_name]
    item = get_object_or_404(model, id=item_id, profile=request.user.userprofile)

    try:
        item.delete()
        return JsonResponse(
            {
                "success": True,
                "message": f"{model_name.replace('_', ' ').title()} deleted successfully!",
            }
        )
    except Exception as e:
        logger.error(f"Error deleting {model_name}: {str(e)}")
        return JsonResponse({"success": False, "message": f"Error deleting {model_name}: {str(e)}"})


@require_http_methods(["POST"])
@login_required
def bulk_delete_records(request):
    """Delete multiple records at once"""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    try:
        data = json.loads(request.body)
        record_type = data.get("record_type")
        record_ids = data.get("record_ids", [])

        if not record_type or not record_ids:
            return JsonResponse({"error": "Missing required parameters"}, status=400)

        # Map record types to models
        models = {
            WorkExperience().model_name: WorkExperience,
            Project().model_name: Project,
            Education().model_name: Education,
            Certification().model_name: Certification,
            Publication().model_name: Publication,
            Skill().model_name: Skill,
        }

        if record_type not in models:
            return JsonResponse({"error": f"Invalid record type: {record_type}"}, status=400)

        model = models[record_type]
        deleted_count = 0

        for record_id in record_ids:
            try:
                record = model.objects.get(id=record_id, profile=request.user.userprofile)
                record.delete()
                deleted_count += 1
            except model.DoesNotExist:
                continue

        return JsonResponse(
            {
                "success": True,
                "message": f"Successfully deleted {deleted_count} {record_type} records",
                "deleted_count": deleted_count,
            }
        )
    except Exception as e:
        logger.error(f"Error in bulk delete: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def edit_record(request, record_type, record_id):
    """
    Enhanced edit record function with automatic date conversion support.
    Now works with both form submissions and direct model updates.
    """
    models = {
        WorkExperience().model_name: (WorkExperience, WorkExperienceForm),
        Project().model_name: (Project, ProjectForm),
        Education().model_name: (Education, EducationForm),
        Certification().model_name: (Certification, CertificationForm),
        Publication().model_name: (Publication, PublicationForm),
        Skill().model_name: (Skill, SkillForm),
    }

    if record_type not in models:
        return JsonResponse(
            {"success": False, "error": f"Invalid record type: {record_type}"}, status=400
        )

    model_class, form_class = models[record_type]

    try:
        item = get_object_or_404(model_class, id=record_id, profile=request.user.userprofile)

        # Method 1: Using Django Forms (existing approach - now with smart date fields)
        form = form_class(request.POST, instance=item)
        if form.is_valid():
            form.save()  # The enhanced models will handle date conversion automatically

            # Return the updated item data with properly formatted dates
            updated_data = {
                "success": True,
                "message": f"{record_type.replace('_', ' ').title()} updated successfully!",
                "updated_item": {
                    "id": item.id,
                },
            }

            # Add date fields if they exist
            date_fields = item.get_date_fields() if hasattr(item, "get_date_fields") else []
            for field_name in date_fields:
                if hasattr(item, field_name):
                    field_value = getattr(item, field_name)
                    updated_data["updated_item"][field_name] = (
                        field_value.isoformat() if field_value else None
                    )

            return JsonResponse(updated_data)
        else:
            errors = ""
            for field, field_errors in form.errors.items():
                errors += (
                    f"{field.capitalize()}: "
                    + ", ".join(str(error) for error in field_errors)
                    + "\n"
                )
            return JsonResponse({"success": False, "error": errors}, status=400)

    except Exception as e:
        logger.error(f"Error editing {record_type}: {str(e)}")
        return JsonResponse({"success": False, "error": "An unexpected error occurred"}, status=500)


@require_http_methods(["POST"])
@login_required
@csrf_exempt
def edit_record_direct(request, record_type, record_id):
    """
    Alternative edit method using direct model update with automatic date conversion.
    Useful for API-style updates or when you want to bypass form validation.
    """
    # Map record types to models
    models = {
        WorkExperience().model_name: WorkExperience,
        Project().model_name: Project,
        Education().model_name: Education,
        Certification().model_name: Certification,
        Publication().model_name: Publication,
        Skill().model_name: Skill,
    }

    if record_type not in models:
        return JsonResponse(
            {"success": False, "error": f"Invalid record type: {record_type}"}, status=400
        )

    model_class = models[record_type]

    try:
        item = get_object_or_404(model_class, id=record_id, profile=request.user.userprofile)

        # Handle both JSON and form data
        if request.content_type == "application/json":
            update_data = json.loads(request.body)
        else:
            update_data = request.POST.dict()
            update_data.pop("csrfmiddlewaretoken", None)

        # Method 2: Using the enhanced model's update method with date conversion
        updated_item = model_class.update_from_form_data(item, update_data)

        # Return success response with updated data
        response_data = {
            "success": True,
            "message": f"{record_type.replace('_', ' ').title()} updated successfully!",
            "updated_item": {
                "id": updated_item.id,
            },
        }

        # Add date fields to response
        date_fields = (
            updated_item.get_date_fields() if hasattr(updated_item, "get_date_fields") else []
        )
        for field_name in date_fields:
            if hasattr(updated_item, field_name):
                field_value = getattr(updated_item, field_name)
                response_data["updated_item"][field_name] = (
                    field_value.isoformat() if field_value else None
                )

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in direct edit for {record_type}: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
@csrf_exempt
def create_record(request, record_type):
    """
    Create a new record with automatic date conversion.
    Supports both form data and JSON data.
    """
    # Map record types to models
    models = {
        WorkExperience().model_name: WorkExperience,
        Project().model_name: Project,
        Education().model_name: Education,
        Certification().model_name: Certification,
        Publication().model_name: Publication,
        Skill().model_name: Skill,
    }

    if record_type not in models:
        return JsonResponse(
            {"success": False, "error": f"Invalid record type: {record_type}"}, status=400
        )

    model_class = models[record_type]

    try:
        profile = request.user.userprofile

        # Handle both JSON and form data
        if request.content_type == "application/json":
            form_data = json.loads(request.body)
        else:
            form_data = request.POST.dict()
            form_data.pop("csrfmiddlewaretoken", None)

        # Use the enhanced model's create method with automatic date conversion
        new_item = model_class.create_from_form_data(profile=profile, **form_data)

        # Return success response with created item data
        response_data = {
            "success": True,
            "message": f"{record_type.replace('_', ' ').title()} created successfully!",
            "created_item": {
                "id": new_item.id,
            },
        }

        # Add date fields to response
        date_fields = new_item.get_date_fields() if hasattr(new_item, "get_date_fields") else []
        for field_name in date_fields:
            if hasattr(new_item, field_name):
                field_value = getattr(new_item, field_name)
                response_data["created_item"][field_name] = (
                    field_value.isoformat() if field_value else None
                )

        # Add some common fields for display
        if hasattr(new_item, "company") and hasattr(new_item, "position"):
            response_data["created_item"][
                "display_name"
            ] = f"{new_item.position} at {new_item.company}"
        elif hasattr(new_item, "title"):
            response_data["created_item"]["display_name"] = new_item.title
        elif hasattr(new_item, "name"):
            response_data["created_item"]["display_name"] = new_item.name
        else:
            response_data["created_item"]["display_name"] = str(new_item)

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error creating {record_type}: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
@csrf_exempt
def bulk_create_records(request):
    """
    Create multiple records at once with automatic date conversion.
    Useful for importing data or batch operations.
    """
    try:
        data = json.loads(request.body)
        record_type = data.get("record_type")
        records_data = data.get("records", [])

        if not record_type or not records_data:
            return JsonResponse({"error": "Missing required parameters"}, status=400)

        # Map record types to models
        models = {
            WorkExperience().model_name: WorkExperience,
            Project().model_name: Project,
            Education().model_name: Education,
            Certification().model_name: Certification,
            Publication().model_name: Publication,
            Skill().model_name: Skill,
        }

        if record_type not in models:
            return JsonResponse({"error": f"Invalid record type: {record_type}"}, status=400)

        model_class = models[record_type]
        profile = request.user.userprofile
        created_items = []
        errors = []

        for i, record_data in enumerate(records_data):
            try:
                # Use the enhanced model's create method with date conversion
                new_item = model_class.create_from_form_data(profile=profile, **record_data)

                created_item_data = {"id": new_item.id, "index": i}

                # Add date fields
                date_fields = (
                    new_item.get_date_fields() if hasattr(new_item, "get_date_fields") else []
                )
                for field_name in date_fields:
                    if hasattr(new_item, field_name):
                        field_value = getattr(new_item, field_name)
                        created_item_data[field_name] = (
                            field_value.isoformat() if field_value else None
                        )

                created_items.append(created_item_data)

            except Exception as e:
                errors.append({"index": i, "error": str(e), "data": record_data})

        response_data = {
            "success": True,
            "message": f"Bulk create completed. Created {len(created_items)} items.",
            "created_count": len(created_items),
            "error_count": len(errors),
            "created_items": created_items,
        }

        if errors:
            response_data["errors"] = errors
            response_data["message"] += f" {len(errors)} items had errors."

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in bulk create: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_POST
@login_required
def generate_profile_bio(request: HttpRequest) -> JsonResponse:
    """
    Generate a professional bio for the user based on their profile data using an LLM.
    """
    try:
        user_id = request.user.id
        user_profile: UserProfile = UserProfile.objects.get(user_id=user_id)
        personal_agent = PersonalAgent(user_id=user_id)
        resume_composition = ResumeComposition(personal_agent)
        resume_composition.tailor_to_job()

        user_profile.professional_summary = resume_composition.professional_summary.strip()
        user_profile.save(update_fields=["professional_summary"])

        logger.info(f"Successfully generated and updated bio for user {request.user.username}")

        return JsonResponse({"success": True, "bio": user_profile.professional_summary})

    except Exception as e:
        logger.error(f"Error generating bio for user {request.user.username}: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "error": "An unexpected error occurred while generating the bio."},
            status=500,
        )
