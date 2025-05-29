"""
Utility views for the core app.
"""

import json
import logging
import smtplib
from datetime import timedelta
from io import BytesIO

import pdfminer.high_level
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.files.storage import default_storage

from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)


def home(request):
    """Home page view"""
    return render(request, "core/home.html")


@login_required
def test_s3(request):
    """Test S3 connection"""
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        try:
            logger.info(f"Attempting to upload file: {file.name}")
            file_path = f"test/{file.name}"
            saved_path = default_storage.save(file_path, file)
            file_url = default_storage.url(saved_path)
            logger.info(f"File uploaded successfully. URL: {file_url}")
            return render(request, "core/test_s3.html", {"file_url": file_url})
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return render(request, "core/test_s3.html", {"error": str(e)})
    return render(request, "core/test_s3.html")


def parse_pdf_resume(pdf_file):
    """Parse text from a PDF resume"""
    try:
        pdf_bytes = BytesIO(pdf_file.read())
        text = pdfminer.high_level.extract_text(pdf_bytes)
        pdf_file.seek(0)  # Reset file pointer for further processing
        return text
    except Exception as e:
        logger.error(f"Error parsing PDF resume: {str(e)}")
        return ""


def load_user_background(user_id):
    """
    Load user background data for use with agents
    """
    from core.models import UserProfile
    from core.utils.agents.personal_agent import PersonalBackground

    try:
        user_profile: UserProfile = UserProfile.objects.get(user_id=user_id)
        background: PersonalBackground = PersonalBackground(
            profile=user_profile.__dict__,
            work_experience=list(user_profile.work_experiences.values()),
            education=list(user_profile.education.values()),
            skills=list(user_profile.skills.values()),
            projects=list(user_profile.projects.values()),
            github_data=user_profile.github_data,
            achievements=[],
            interests=[],
        )
        return background
    except Exception as e:
        logger.error(f"Error loading user background: {str(e)}")
        return None


@csrf_exempt
def health_check(request):
    """Health check endpoint for Fly.io"""
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse({"status": "healthy", "database": "connected"}, status=200)

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JsonResponse({"status": "unhealthy", "error": str(e)}, status=503)
