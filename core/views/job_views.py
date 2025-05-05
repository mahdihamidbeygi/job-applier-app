"""
Job-related views for the core app.
"""

import json
import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.forms import JobPlatformPreferenceForm
from core.models import JobListing, JobPlatformPreference, UserProfile
from core.utils.agents.personal_agent import PersonalAgent, PersonalBackground
from core.utils.agents.search_agent import SearchAgent
from core.views.utility_views import load_user_background

logger = logging.getLogger(__name__)


@login_required
def jobs_page(request):
    """Jobs page view"""
    # Get user preferences for job platforms
    try:
        user_preferences = JobPlatformPreference.objects.get(user_profile=request.user.userprofile)
    except JobPlatformPreference.DoesNotExist:
        # Create default preferences
        user_preferences = JobPlatformPreference.objects.create(
            user_profile=request.user.userprofile,
            preferred_platforms=["linkedin", "indeed", "glassdoor"],
        )

    # Get jobs filtered by preferred platforms
    preferred_platforms = user_preferences.preferred_platforms
    jobs = JobListing.objects.filter(
        user=request.user, source__in=preferred_platforms, is_active=True
    ).order_by("-match_score", "-posted_date")[:20]

    # Prepare jobs for display
    for job in jobs:
        if len(job.description) > 300:
            job.short_description = job.description[:300] + "..."
        else:
            job.short_description = job.description

    # Get applied jobs
    applied_jobs = JobListing.objects.filter(user=request.user, applied=True).order_by(
        "-application_date"
    )[:5]

    return render(
        request,
        "core/jobs.html",
        {
            "jobs": jobs,
            "applied_jobs": applied_jobs,
            "user_preferences": user_preferences,
        },
    )


@login_required
def search_jobs(request):
    """Search for jobs"""
    query = request.GET.get("q", "")
    location = request.GET.get("location", "")
    sources = request.GET.getlist("sources", [])

    # Initialize search agent
    search_agent = SearchAgent()

    # Get user preferences for job platforms if no sources specified
    if not sources:
        try:
            user_preferences = JobPlatformPreference.objects.get(
                user_profile=request.user.userprofile
            )
            sources = user_preferences.preferred_platforms
        except JobPlatformPreference.DoesNotExist:
            # Default to all sources
            sources = ["linkedin", "indeed", "glassdoor", "monster", "jobbank", "ziprecruiter"]

    # Build filter query
    filter_query = Q(user=request.user)

    if query:
        filter_query &= (
            Q(title__icontains=query)
            | Q(company__icontains=query)
            | Q(description__icontains=query)
            | Q(requirements__icontains=query)
        )

    if location:
        filter_query &= Q(location__icontains=location)

    if sources:
        filter_query &= Q(source__in=sources)

    # Get jobs from database
    jobs = JobListing.objects.filter(filter_query).order_by("-match_score", "-posted_date")[:50]

    # If this is an API request (AJAX), return JSON response
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        job_list = []
        for job in jobs:
            job_list.append(
                {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "description": (
                        job.description[:300] + "..."
                        if len(job.description) > 300
                        else job.description
                    ),
                    "source": job.source,
                    "posted_date": job.posted_date.strftime("%Y-%m-%d"),
                    "match_score": job.match_score,
                    "applied": job.applied,
                    "url": job.source_url,
                    "has_documents": job.has_tailored_documents,
                }
            )
        return JsonResponse({"jobs": job_list})

    # For regular request, render template
    return render(
        request,
        "core/search_jobs.html",
        {
            "jobs": jobs,
            "query": query,
            "location": location,
            "selected_sources": sources,
        },
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_job_documents(request, job_id):
    """
    Generate tailored resume and cover letter for a job
    """
    try:
        job_listing = get_object_or_404(JobListing, id=job_id, user=request.user)
        user_profile = request.user.userprofile

        # Load user background
        background = load_user_background(request.user.id)

        if not background:
            return Response({"error": "Failed to load user background"}, status=400)

        # Initialize personal agent
        personal_agent = PersonalAgent(request.user.id)
        personal_agent.load_background(background)

        # Generate documents
        success = personal_agent.generate_tailored_documents(job_listing)

        if not success:
            return Response({"error": "Failed to generate documents"}, status=500)

        return Response(
            {
                "success": True,
                "resume_url": job_listing.get_resume_url(),
                "cover_letter_url": job_listing.get_cover_letter_url(),
            }
        )
    except Exception as e:
        logger.error(f"Error generating job documents: {str(e)}")
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_job_documents(request, job_id):
    """
    Get tailored documents for a job
    """
    try:
        job_listing = get_object_or_404(JobListing, id=job_id, user=request.user)

        # Check if documents exist
        has_documents = job_listing.has_tailored_documents

        if not has_documents:
            return Response({"error": "No documents found for this job"}, status=404)

        return Response(
            {
                "success": True,
                "resume_url": job_listing.get_resume_url(),
                "cover_letter_url": job_listing.get_cover_letter_url(),
                "has_documents": has_documents,
            }
        )
    except Exception as e:
        logger.error(f"Error getting job documents: {str(e)}")
        return Response({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def apply_to_job(request, job_id) -> JsonResponse:
    """
    Mark a job as applied
    """
    try:
        job_listing = get_object_or_404(JobListing, id=job_id, user=request.user)

        # Update job status
        job_listing.applied = True
        job_listing.application_date = date.today()
        job_listing.application_status = "Applied"
        job_listing.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Successfully marked '{job_listing.title}' as applied!",
            }
        )
    except Exception as e:
        logger.error(f"Error applying to job: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def job_detail(request, job_id) -> HttpResponse:
    """Job detail view"""
    job = get_object_or_404(JobListing, id=job_id, user=request.user)
    return render(request, "core/job_detail.html", {"job": job})


@login_required
def job_apply(request, job_id) -> HttpResponseRedirect:
    """Job application view"""
    job = get_object_or_404(JobListing, id=job_id, user=request.user)

    # If job is already applied to, redirect to job detail
    if job.applied:
        messages.info(request, f"You have already applied to {job.title} at {job.company}")
        return redirect("core:job_detail", job_id=job.id)

    # Check if tailored documents are available
    if not job.has_tailored_documents:
        messages.warning(request, "Please generate tailored documents before applying to this job.")
        return redirect("core:job_detail", job_id=job.id)

    return render(request, "core/job_apply.html", {"job": job})


@login_required
def job_platform_preferences(request):
    """Job platform preferences view"""
    try:
        preferences = JobPlatformPreference.objects.get(user_profile=request.user.userprofile)
    except JobPlatformPreference.DoesNotExist:
        preferences = JobPlatformPreference.objects.create(
            user_profile=request.user.userprofile,
            preferred_platforms=["linkedin", "indeed", "glassdoor"],
        )

    if request.method == "POST":
        form = JobPlatformPreferenceForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Job platform preferences updated successfully!")
            return redirect("core:jobs_page")
    else:
        form = JobPlatformPreferenceForm(instance=preferences)

    return render(request, "core/job_platform_preferences.html", {"form": form})


@login_required
@require_POST
def remove_job(request):
    """Remove a job from the list"""
    try:
        data = json.loads(request.body)
        job_id = data.get("job_id")

        if not job_id:
            return JsonResponse({"error": "Job ID is required"}, status=400)

        job = get_object_or_404(JobListing, id=job_id, user=request.user)

        # Check if the job has been applied to
        if job.applied:
            return JsonResponse(
                {"error": "Cannot remove a job that has been applied to"}, status=400
            )

        # Mark as inactive instead of deleting
        job.is_active = False
        job.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Successfully removed '{job.title}' from your job list",
            }
        )
    except Exception as e:
        logger.error(f"Error removing job: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
