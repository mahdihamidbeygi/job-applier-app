"""
Document generation views for the core app.
"""

import json
import logging
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.models import UserProfile
from core.utils.agents.application_agent import ApplicationAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.cover_letter_composition import CoverLetterComposition
from core.utils.local_llms import OllamaClient
from core.utils.resume_composition import ResumeComposition
from core.views.utility_views import load_user_background

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class ManualSubmissionView(TemplateView):
    """View for manual job application submission assistance"""

    template_name = "core/application_assistance.html"


@login_required
@require_http_methods(["POST"])
def generate_documents(request):
    """
    Generate resume and cover letter
    """
    try:
        data = json.loads(request.body)
        job_title = data.get("job_title")
        job_description = data.get("job_description")
        company = data.get("company")

        if not job_title or not job_description or not company:
            return JsonResponse(
                {"error": "Job title, description, and company are required"}, status=400
            )

        # Load user background
        background = load_user_background(request.user.id)

        if not background:
            return JsonResponse({"error": "Failed to load user background"}, status=400)

        # Initialize personal agent
        personal_agent = PersonalAgent(request.user.id)
        personal_agent.load_background(background)

        # Generate documents
        resume_composition = ResumeComposition()
        cover_letter_composition = CoverLetterComposition()

        # Generate resume
        resume_html = resume_composition.generate_resume(
            profile=background.profile,
            work_experience=background.work_experience,
            education=background.education,
            skills=background.skills,
            projects=background.projects,
            job_title=job_title,
            job_description=job_description,
            company=company,
        )

        # Generate cover letter
        cover_letter_html = cover_letter_composition.generate_cover_letter(
            profile=background.profile,
            work_experience=background.work_experience,
            education=background.education,
            skills=background.skills,
            job_title=job_title,
            job_description=job_description,
            company=company,
        )

        # Save documents
        now = date.today().strftime("%Y%m%d")
        resume_filename = f"resume_{request.user.username}_{company}_{now}.html"
        cover_letter_filename = f"cover_letter_{request.user.username}_{company}_{now}.html"

        resume_path = f"documents/{request.user.username}/resumes/{resume_filename}"
        cover_letter_path = (
            f"documents/{request.user.username}/cover_letters/{cover_letter_filename}"
        )

        resume_url = default_storage.save(resume_path, ContentFile(resume_html.encode("utf-8")))
        cover_letter_url = default_storage.save(
            cover_letter_path, ContentFile(cover_letter_html.encode("utf-8"))
        )

        return JsonResponse(
            {
                "success": True,
                "resume_url": default_storage.url(resume_url),
                "cover_letter_url": default_storage.url(cover_letter_url),
            }
        )
    except Exception as e:
        logger.error(f"Error generating documents: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def generate_answers(request):
    """
    Generate answers to job application questions
    """
    try:
        data = json.loads(request.body)
        job_title = data.get("job_title")
        job_description = data.get("job_description")
        company = data.get("company")
        questions = data.get("questions", [])

        if not job_title or not job_description or not company or not questions:
            return JsonResponse(
                {"error": "Job title, description, company, and questions are required"}, status=400
            )

        # Load user background
        background = load_user_background(request.user.id)

        if not background:
            return JsonResponse({"error": "Failed to load user background"}, status=400)

        # Initialize application agent
        application_agent = ApplicationAgent(
            user_id=request.user.id,
            job_title=job_title,
            job_description=job_description,
            company=company,
        )

        application_agent.load_background(background)

        # Generate answers
        answers = []
        for question in questions:
            answer = application_agent.generate_answer(question)
            answers.append(
                {
                    "question": question,
                    "answer": answer,
                }
            )

        return JsonResponse(
            {
                "success": True,
                "answers": answers,
            }
        )
    except Exception as e:
        logger.error(f"Error generating answers: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def process_job_application(request):
    """
    Process a job application form
    """
    try:
        data = json.loads(request.body)
        job_title = data.get("job_title")
        job_description = data.get("job_description")
        company = data.get("company")
        application_url = data.get("application_url")
        form_fields = data.get("form_fields", [])

        if not job_title or not job_description or not company or not application_url:
            return JsonResponse(
                {"error": "Job title, description, company, and application URL are required"},
                status=400,
            )

        # Load user background
        background = load_user_background(request.user.id)

        if not background:
            return JsonResponse({"error": "Failed to load user background"}, status=400)

        # Initialize application agent
        application_agent = ApplicationAgent(
            user_id=request.user.id,
            job_title=job_title,
            job_description=job_description,
            company=company,
        )

        application_agent.load_background(background)

        # Process form fields
        field_values = {}

        for field in form_fields:
            field_id = field.get("id")
            field_type = field.get("type")
            field_label = field.get("label")
            field_options = field.get("options", [])

            if not field_id or not field_type or not field_label:
                continue

            # Skip if field is already filled
            if field.get("value"):
                field_values[field_id] = field.get("value")
                continue

            # Get value based on field type
            if field_type == "text" or field_type == "textarea":
                value = application_agent.fill_text_field(field_label)
            elif field_type == "select" or field_type == "radio":
                value = application_agent.select_option(field_label, field_options)
            elif field_type == "checkbox":
                value = application_agent.select_checkboxes(field_label, field_options)
            else:
                value = ""

            field_values[field_id] = value

        return JsonResponse(
            {
                "success": True,
                "field_values": field_values,
            }
        )
    except Exception as e:
        logger.error(f"Error processing job application: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["POST"])
@permission_classes([AllowAny])  # Temporarily allow any user for testing
def fill_form(request):
    """
    API endpoint to fill a form using user's profile data
    """
    try:
        form_fields = request.data.get("form_fields", [])
        job_title = request.data.get("job_title", "")
        job_description = request.data.get("job_description", "")
        company = request.data.get("company", "")

        # Authenticate the user
        user_id = request.user.id if request.user.is_authenticated else None

        if not user_id:
            return Response({"error": "Authentication required"}, status=401)

        # Load user background
        background = load_user_background(user_id)

        if not background:
            return Response({"error": "Failed to load user background"}, status=400)

        # Initialize application agent
        application_agent = ApplicationAgent(
            user_id=user_id,
            job_title=job_title,
            job_description=job_description,
            company=company,
        )

        application_agent.load_background(background)

        # Process form fields
        field_values = {}

        for field in form_fields:
            field_id = field.get("id")
            field_type = field.get("type")
            field_label = field.get("label")
            field_options = field.get("options", [])

            if not field_id or not field_type or not field_label:
                continue

            # Skip if field is already filled
            if field.get("value"):
                field_values[field_id] = field.get("value")
                continue

            # Get value based on field type
            if field_type == "text" or field_type == "textarea":
                value = application_agent.fill_text_field(field_label)
            elif field_type == "select" or field_type == "radio":
                value = application_agent.select_option(field_label, field_options)
            elif field_type == "checkbox":
                value = application_agent.select_checkboxes(field_label, field_options)
            else:
                value = ""

            field_values[field_id] = value

        return Response(
            {
                "success": True,
                "field_values": field_values,
            }
        )
    except Exception as e:
        logger.error(f"Error in fill_form: {str(e)}")
        return Response({"error": str(e)}, status=500)
