"""
Document generation views for the core app - FIXED VERSION
"""

import json
import logging
from typing import Any, Dict

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from core.utils.agents.job_agent import JobAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.agents.writer_agent import WriterAgent
from core.utils.form_processors import process_form_fields

logger = logging.getLogger(__name__)


# Add serializers for API documentation
class FormFieldSerializer(serializers.Serializer):
    field_name = serializers.CharField()
    field_type = serializers.CharField()
    field_value = serializers.CharField(required=False, allow_blank=True)


class FillFormRequestSerializer(serializers.Serializer):
    form_fields = FormFieldSerializer(many=True)
    job_title = serializers.CharField(required=False, allow_blank=True)
    job_description = serializers.CharField(required=False, allow_blank=True)
    company = serializers.CharField(required=False, allow_blank=True)


class FillFormResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    field_values = serializers.DictField()


@method_decorator(login_required, name="dispatch")
class ManualSubmissionView(TemplateView):
    """View for manual job application submission assistance"""

    template_name = "core/application_assistance.html"


@login_required
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

        personal_agent = PersonalAgent(request.user.id)
        job_agent = JobAgent(
            user_id=request.user.id,
            text=job_title
            + job_description
            + company
            + f"user: {personal_agent.user_profile.user.username}",
        )
        # Initialize application agent
        application_agent = WriterAgent(
            user_id=request.user.id,
            personal_agent=personal_agent,
            job_agent=job_agent,
        )

        application_agent.generate_resume()
        application_agent.generate_cover_letter()

        return JsonResponse(
            {
                "success": True,
                "resume_url": job_agent.job_record.tailored_resume,
                "cover_letter_url": job_agent.job_record.tailored_cover_letter,
            }
        )
    except ValueError as e:
        logger.error(f"Value error in generate_documents: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error generating documents: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
# @require_http_methods(["POST"])
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

        personal_agent = PersonalAgent(request.user.id)
        job_agent = JobAgent(
            user_id=request.user.id,
            text=job_title
            + job_description
            + company
            + f"user: {personal_agent.user_profile.user.username}",
        )
        # Initialize application agent
        application_agent = WriterAgent(
            user_id=request.user.id,
            personal_agent=personal_agent,
            job_agent=job_agent,
        )

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
# @require_http_methods(["POST"])
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

        agent_personal = PersonalAgent(request.user.id)
        agent_job = JobAgent(
            user_id=request.user.id,
            job_id=None,
            text=job_title
            + job_description
            + company
            + application_url
            + f"user: {agent_personal.user_profile.user.username}",
        )

        # Initialize application agent
        application_agent = WriterAgent(
            user_id=request.user.id,
            personal_agent=agent_personal,
            job_agent=agent_job,
        )

        # Process form fields using the utility function
        field_values: Dict[str, Any] = process_form_fields(form_fields, application_agent)

        return JsonResponse(
            {
                "success": True,
                "field_values": field_values,
            }
        )
    except Exception as e:
        logger.error(f"Error processing job application: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@extend_schema(
    operation_id="fill_form",
    description="Fill a form using user's profile data",
    request=FillFormRequestSerializer,
    responses={200: FillFormResponseSerializer},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def fill_form(request):
    """
    API endpoint to fill a form using user's profile data
    """
    try:
        # Extract the request data
        data = request.data
        form_fields = data.get("form_fields", [])
        job_title = data.get("job_title", "")
        job_description = data.get("job_description", "")
        company = data.get("company", "")

        # Authenticate the user
        user_id = request.user.id

        personal_agent = PersonalAgent(user_id)
        job_agent = JobAgent(
            user_id=user_id,
            job_id=None,
            text=job_title
            + job_description
            + company
            + f"user: {personal_agent.user_profile.user.username}",
        )
        # Initialize application agent
        application_agent = WriterAgent(
            user_id=user_id,
            personal_agent=personal_agent,
            job_agent=job_agent,
        )

        # Process form fields using the utility function
        field_values: Dict[str, Any] = process_form_fields(form_fields, application_agent)

        return Response(
            {
                "success": True,
                "field_values": field_values,
            }
        )
    except Exception as e:
        logger.error(f"Error in fill_form: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
