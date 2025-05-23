"""
Skill management views.
"""

import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.forms import SkillForm
from core.models import Skill
from core.utils.form_handler import FormHandler
from core.utils.logging_utils import log_exceptions

logger = logging.getLogger(__name__)


@login_required
def add_skill(request):
    """Add a skill to user profile."""

    def pre_save_callback(form):
        """Set the profile before saving."""
        form.instance.profile = request.user.userprofile

    return FormHandler.process_form(
        request=request,
        form_class=SkillForm,
        template_name="core/skill/add.html",
        success_url=reverse("core:profile") + "#skills",
        success_message="Skill added successfully!",
        pre_save_callback=pre_save_callback,
    )


@login_required
def edit_skill(request, skill_id):
    """Edit an existing skill."""

    # Get the instance with permission check
    skill = Skill.objects.get(id=skill_id, profile=request.user.userprofile)

    return FormHandler.process_form(
        request=request,
        form_class=SkillForm,
        template_name="core/skill/edit.html",
        success_url=reverse("core:profile") + "#skills",
        instance=skill,
        success_message="Skill updated successfully!",
        extra_context={"skill": skill},
    )


@login_required
def delete_skill(request, skill_id):
    """Delete a skill."""

    def permission_check(request, obj):
        """Check if the user has permission to delete this skill."""
        return obj.profile == request.user.userprofile

    return FormHandler.handle_delete(
        request=request,
        model_class=Skill,
        object_id=skill_id,
        success_url=reverse("core:profile") + "#skills",
        success_message="Skill deleted successfully!",
        permission_check=permission_check,
    )


@login_required
@log_exceptions(level=logging.ERROR)
def deduplicate_skills(request):
    """Remove duplicate skills from user profile"""
    profile = request.user.userprofile

    # Find duplicate skills (case-insensitive match)
    duplicate_skills = (
        Skill.objects.filter(profile=profile)
        .values("name__lower")
        .annotate(name_lower=Count("name__lower"))
        .filter(name_lower__gt=1)
    )

    removed_count = 0

    # For each group of duplicates, keep the highest proficiency one
    for dup in duplicate_skills:
        skill_name = dup["name__lower"]
        skills = Skill.objects.filter(profile=profile, name__iexact=skill_name).order_by(
            "-proficiency"
        )

        # Keep the first one (highest proficiency), delete the rest
        if skills.count() > 1:
            to_delete = skills[1:]
            removed_count += to_delete.count()
            to_delete.delete()

    data = {
        "success": True,
        "removed_count": removed_count,
        "message": f"Removed {removed_count} duplicate skills.",
    }

    messages.success(request, data["message"])

    # If this is an AJAX request, return JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(data)

    # Otherwise redirect to profile
    return redirect(reverse("core:profile") + "#skills")
