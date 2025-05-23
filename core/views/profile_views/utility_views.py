"""
Utility views for profile management.
"""

import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods, require_POST

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
    models = {
        "work_experience": WorkExperience,
        "project": Project,
        "education": Education,
        "certification": Certification,
        "publication": Publication,
        "skill": Skill,
    }

    if model_name not in models:
        messages.error(request, f"Invalid model type: {model_name}")
        return redirect("core:profile")

    model = models[model_name]
    item = get_object_or_404(model, id=item_id, profile=request.user.userprofile)

    try:
        item.delete()
        messages.success(request, f"{model_name.replace('_', ' ').title()} deleted successfully!")
    except Exception as e:
        logger.error(f"Error deleting {model_name}: {str(e)}")
        messages.error(request, f"Error deleting {model_name}")

    return redirect("core:profile")


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
            "work_experience": WorkExperience,
            "project": Project,
            "education": Education,
            "certification": Certification,
            "publication": Publication,
            "skill": Skill,
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
    """Edit a specific record"""
    models = {
        "work_experience": (WorkExperience, WorkExperienceForm),
        "project": (Project, ProjectForm),
        "education": (Education, EducationForm),
        "certification": (Certification, CertificationForm),
        "publication": (Publication, PublicationForm),
        "skill": (Skill, SkillForm),
    }

    if record_type not in models:
        messages.error(request, f"Invalid record type: {record_type}")
        return redirect("core:profile")

    model_class, form_class = models[record_type]
    item = get_object_or_404(model_class, id=record_id, profile=request.user.userprofile)

    form = form_class(request.POST, instance=item)
    if form.is_valid():
        form.save()
        messages.success(request, f"{record_type.replace('_', ' ').title()} updated successfully!")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        messages.error(request, f"Error updating {record_type}")

    return redirect("core:profile")


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

        # 4. Update and save profile
        user_profile.professional_summary = resume_composition.professional_summary.strip()
        user_profile.save(update_fields=["professional_summary"])

        logger.info(f"Successfully generated and updated bio for user {request.user.username}")
        # messages.success(request, "Professional summary generated and updated successfully!") # Good for non-AJAX

        return JsonResponse({"success": True, "bio": user_profile.professional_summary})

    except Exception as e:
        logger.error(f"Error generating bio for user {request.user.username}: {e}", exc_info=True)
        return JsonResponse(
            {"success": False, "error": "An unexpected error occurred while generating the bio."},
            status=500,
        )
