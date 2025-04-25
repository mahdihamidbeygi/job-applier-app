"""
Views for managing education records.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from core.forms import EducationForm


@login_required
@require_POST
def add_education(request):
    """Add education to user profile"""
    form = EducationForm(request.POST)
    if form.is_valid():
        education = form.save(commit=False)
        education.profile = request.user.userprofile
        education.save()
        messages.success(request, "Education added successfully!")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        messages.error(request, "Error adding education.")
    return redirect("core:profile")
