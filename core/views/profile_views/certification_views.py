"""
Views for managing certifications.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from core.forms import CertificationForm


@login_required
@require_POST
def add_certification(request):
    """Add certification to user profile"""
    form = CertificationForm(request.POST)
    if form.is_valid():
        certification = form.save(commit=False)
        certification.profile = request.user.userprofile
        certification.save()
        messages.success(request, "Certification added successfully!")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        messages.error(request, "Error adding certification.")
    return redirect("core:profile")
