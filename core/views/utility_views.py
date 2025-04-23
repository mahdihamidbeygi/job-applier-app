"""
Utility views for the core app.
"""

import base64
import io
import logging
from io import BytesIO

import pdfminer.high_level
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.shortcuts import render

from core.models import UserProfile

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
