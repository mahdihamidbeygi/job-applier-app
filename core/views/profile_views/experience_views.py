"""
Work experience views using the generic form handler.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils.decorators import method_decorator

from core.forms import WorkExperienceForm
from core.models import WorkExperience
from core.utils.form_handler import FormHandler


@login_required
def add_work_experience(request):
    """Add a new work experience entry."""

    def pre_save_callback(form):
        """Set the profile before saving."""
        form.instance.profile = request.user.userprofile

    return FormHandler.process_form(
        request=request,
        form_class=WorkExperienceForm,
        template_name="core/experience/add.html",
        success_url=reverse("profile:experience_list"),
        success_message="Work experience added successfully!",
        pre_save_callback=pre_save_callback,
    )


@login_required
def edit_work_experience(request, experience_id):
    """Edit an existing work experience entry."""

    # Get the instance with permission check
    experience = WorkExperience.objects.get(id=experience_id, profile=request.user.userprofile)

    return FormHandler.process_form(
        request=request,
        form_class=WorkExperienceForm,
        template_name="core/experience/edit.html",
        success_url=reverse("profile:experience_list"),
        instance=experience,
        success_message="Work experience updated successfully!",
        extra_context={"experience": experience},
    )


@login_required
def delete_work_experience(request, experience_id):
    """Delete a work experience entry."""

    def permission_check(request, obj):
        """Check if the user has permission to delete this object."""
        return obj.profile == request.user.userprofile

    return FormHandler.handle_delete(
        request=request,
        model_class=WorkExperience,
        object_id=experience_id,
        success_url=reverse("profile:experience_list"),
        success_message="Work experience deleted successfully!",
        permission_check=permission_check,
    )


@login_required
@require_http_methods(["POST"])
def ajax_add_work_experience(request):
    """Add a new work experience entry via AJAX."""

    def pre_save_callback(form):
        """Set the profile before saving."""
        form.instance.profile = request.user.userprofile

    def post_save_callback(obj):
        """Return additional data after saving."""
        return {
            "experience_id": obj.id,
            "company": obj.company,
            "position": obj.position,
        }

    return FormHandler.process_ajax_form(
        request=request,
        form_class=WorkExperienceForm,
        pre_save_callback=pre_save_callback,
        post_save_callback=post_save_callback,
    )


@login_required
@require_http_methods(["POST"])
def ajax_edit_work_experience(request, experience_id):
    """Edit a work experience entry via AJAX."""

    # Get the instance with permission check
    experience = WorkExperience.objects.get(id=experience_id, profile=request.user.userprofile)

    return FormHandler.process_ajax_form(
        request=request,
        form_class=WorkExperienceForm,
        instance=experience,
    )


@login_required
@require_http_methods(["POST", "DELETE"])
def ajax_delete_work_experience(request, experience_id):
    """Delete a work experience entry via AJAX."""

    def permission_check(request, obj):
        """Check if the user has permission to delete this object."""
        return obj.profile == request.user.userprofile

    return FormHandler.handle_ajax_delete(
        request=request,
        model_class=WorkExperience,
        object_id=experience_id,
        permission_check=permission_check,
    )
