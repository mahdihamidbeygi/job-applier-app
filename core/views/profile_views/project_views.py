"""
Project management views.
"""

import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.forms import ProjectForm
from core.models import Project
from core.utils.form_handler import FormHandler
from core.utils.logging_utils import log_exceptions

logger = logging.getLogger(__name__)


@login_required
def add_project(request):
    """Add a new project to user profile."""

    def pre_save_callback(form):
        """Set the profile before saving."""
        form.instance.profile = request.user.userprofile

    return FormHandler.process_form(
        request=request,
        form_class=ProjectForm,
        template_name="core/project/add.html",
        success_url=reverse("core:profile") + "#projects",
        success_message="Project added successfully!",
        pre_save_callback=pre_save_callback,
    )


@login_required
def edit_project(request, project_id):
    """Edit an existing project."""

    # Get the instance with permission check
    project = Project.objects.get(id=project_id, profile=request.user.userprofile)

    return FormHandler.process_form(
        request=request,
        form_class=ProjectForm,
        template_name="core/project/edit.html",
        success_url=reverse("core:profile") + "#projects",
        instance=project,
        success_message="Project updated successfully!",
        extra_context={"project": project},
    )


@login_required
def delete_project(request, project_id):
    """Delete a project."""

    def permission_check(request, obj):
        """Check if the user has permission to delete this project."""
        return obj.profile == request.user.userprofile

    return FormHandler.handle_delete(
        request=request,
        model_class=Project,
        object_id=project_id,
        success_url=reverse("core:profile") + "#projects",
        success_message="Project deleted successfully!",
        permission_check=permission_check,
    )


@login_required
@require_POST
@log_exceptions(level=logging.ERROR)
def ajax_add_project(request):
    """Add a new project via AJAX."""

    def pre_save_callback(form):
        """Set the profile before saving."""
        form.instance.profile = request.user.userprofile

    def post_save_callback(obj):
        """Return additional data after saving."""
        return {
            "project_id": obj.id,
            "title": obj.title,
            "technologies": obj.technologies,
        }

    return FormHandler.process_ajax_form(
        request=request,
        form_class=ProjectForm,
        pre_save_callback=pre_save_callback,
        post_save_callback=post_save_callback,
    )
