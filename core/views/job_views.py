"""
Job-related views for the core app.
"""

import json
import logging
from datetime import date
from typing import List

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models.manager import BaseManager
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers
from drf_spectacular.utils import extend_schema

from core.forms import JobPlatformPreferenceForm
from core.models import JobListing, JobPlatformPreference
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.agents.search_agent import SearchAgent
from core.utils.agents.writer_agent import WriterAgent
from core.utils.agents.job_agent import JobAgent

logger = logging.getLogger(__name__)


class GenerateJobDocumentsResponseSerializer(serializers.Serializer):
    """Response schema for generate_job_documents endpoint"""

    success = serializers.BooleanField()
    resume_url = serializers.URLField()
    cover_letter_url = serializers.URLField()


class GetJobDocumentsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    resume_url = serializers.URLField()
    cover_letter_url = serializers.URLField()
    has_documents = serializers.BooleanField()


class JobDocumentErrorSerializer(serializers.Serializer):
    """Error response schema"""

    error = serializers.CharField()


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
    jobs: BaseManager[JobListing] = JobListing.objects.filter(user=request.user).order_by(
        "match_score", "posted_date"
    )

    # Prepare jobs for display
    for job in jobs:
        if len(job.description) > 300:
            job.short_description = job.description[:300] + "..."
        else:
            job.short_description = job.description

    # Get applied jobs
    applied_jobs = JobListing.objects.filter(user=request.user, applied=True).order_by(
        "application_date"
    )

    return render(
        request,
        "core/jobs.html",
        {
            "job_listings": jobs,
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
    filter_query = Q(user=request.user, is_active=True)

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
                    "posted_date": job.posted_date.strftime("%Y-%m-%d") if job.posted_date else "",
                    "match_score": job.match_score or 0,
                    "applied": job.applied,
                    "url": job.source_url,
                    "has_documents": job.has_tailored_documents,
                }
            )
        return JsonResponse({"jobs": job_list, "count": len(job_list)})

    # For regular request, render template
    return render(
        request,
        "core/search_jobs.html",
        {
            "job_listings": jobs,
            "query": query,
            "location": location,
            "selected_sources": sources,
        },
    )


@login_required
def online_jobsearch(request):
    """
    Online job search endpoint - Scrapes jobs from external platforms using SearchAgent
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            role = data.get("role", "")
            location = data.get("location", "")
            platforms = data.get("platform", [])

            if not role:
                return JsonResponse({"error": "Job role is required"}, status=400)

            # Default platforms if none specified
            if not platforms:
                try:
                    user_preferences = JobPlatformPreference.objects.get(
                        user_profile=request.user.userprofile
                    )
                    platforms = user_preferences.preferred_platforms
                except JobPlatformPreference.DoesNotExist:
                    platforms = ["linkedin", "indeed", "glassdoor"]

            # Initialize search agent
            search_agent = SearchAgent(request.user.id)

            all_jobs = []
            scraping_results = {
                "successful_platforms": [],
                "failed_platforms": [],
                "total_jobs_found": 0,
            }

            # Search each platform
            for platform in platforms:
                try:
                    logger.info(f"Searching {platform} for role: {role}, location: {location}")

                    # Scrape jobs from the platform
                    platform_jobs = search_agent.search_jobs(
                        role=role,
                        location=location,
                        platform=platform,
                        request=request,
                    )

                    if platform_jobs:
                        # Process and save jobs to database
                        processed_jobs: List[JobListing] = search_agent.process_jobs(platform_jobs)

                        # Analyze job fit for each job
                        for job_listing in processed_jobs:

                            # Analyze job fit
                            job_data = {
                                "title": job_listing.title,
                                "company": job_listing.company,
                                "location": job_listing.location,
                                "description": job_listing.description,
                                "required_skills": job_listing.required_skills,
                            }

                            try:
                                analysis = search_agent.analyze_job_fit(job_data)
                                job_listing.match_score = analysis.get("match_score", 0)
                                job_listing.match_details = json.dumps(analysis)
                            except Exception as e:
                                logger.warning(
                                    f"Failed to analyze job fit for {job_listing.title}: {str(e)}"
                                )
                                job_listing.match_score = 50  # Default score

                            job_listing.save()
                            all_jobs.append(job_listing)

                        scraping_results["successful_platforms"].append(platform)
                        scraping_results["total_jobs_found"] += len(processed_jobs)

                        logger.info(
                            f"Successfully scraped {len(processed_jobs)} jobs from {platform}"
                        )
                    else:
                        scraping_results["failed_platforms"].append(f"{platform} (no jobs found)")
                        logger.warning(f"No jobs found on {platform}")

                except Exception as e:
                    logger.error(f"Error scraping {platform}: {str(e)}")
                    scraping_results["failed_platforms"].append(f"{platform} (error: {str(e)})")

            # Sort jobs by match score
            all_jobs.sort(key=lambda x: x.match_score or 0, reverse=True)

            # Prepare response data
            job_list = []
            for job in all_jobs:  # Limit to top 50 jobs
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
                        "posted_date": (
                            job.posted_date.strftime("%Y-%m-%d") if job.posted_date else ""
                        ),
                        "match_score": job.match_score or 0,
                        "applied": job.applied,
                        "url": job.source_url,
                        "has_documents": job.has_tailored_documents,
                    }
                )

            response_data = {
                "success": True,
                "job_listings": job_list,
                "count": len(job_list),
                "scraping_summary": scraping_results,
                "message": f"Found {scraping_results['total_jobs_found']} new jobs from {len(scraping_results['successful_platforms'])} platforms",
            }

            # Add warnings if some platforms failed
            if scraping_results["failed_platforms"]:
                response_data["warnings"] = [
                    f"Some platforms had issues: {', '.join(scraping_results['failed_platforms'])}"
                ]

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            logger.error(f"Error in online job search: {str(e)}")
            return JsonResponse({"error": f"Search failed: {str(e)}"}, status=500)

    # For GET requests, redirect to search_jobs
    return redirect("core:search_jobs")


@extend_schema(
    operation_id="generate_job_documents",
    description="Generate tailored resume and cover letter for a job",
    request=None,
    responses={
        200: GenerateJobDocumentsResponseSerializer,
        400: JobDocumentErrorSerializer,
        500: JobDocumentErrorSerializer,
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

        # Initialize personal agent
        personal_agent = PersonalAgent(request.user.id)
        job_agent = JobAgent(user_id=request.user.id, job_id=job_id)
        writer_agent = WriterAgent(
            user_id=user_profile.user.id, personal_agent=personal_agent, job_agent=job_agent
        )

        # Generate documents
        resume = writer_agent.generate_resume()
        cover_letter = writer_agent.generate_cover_letter()

        if not job_listing.has_tailored_documents:
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


@extend_schema(
    operation_id="get_job_documents",
    description="Get tailored documents for a job",
    responses={200: GetJobDocumentsResponseSerializer},
)
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
