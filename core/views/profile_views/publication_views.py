"""
Views for managing publications.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from core.forms import PublicationForm


@login_required
@require_POST
def add_publication(request):
    """Add publication to user profile"""
    form = PublicationForm(request.POST)
    if form.is_valid():
        publication = form.save(commit=False)
        publication.profile = request.user.userprofile
        publication.save()
        messages.success(request, "Publication added successfully!")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        messages.error(request, "Error adding publication.")
    return redirect("core:profile")
