"""
API ViewSets for the core app
"""

import json
import logging
from datetime import date
from typing import Dict, List

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.db.models import Count, QuerySet
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import (
    Certification,
    ChatConversation,
    ChatMessage,
    Education,
    Project,
    Publication,
    Skill,
    UserProfile,
    WorkExperience,
)
from core.serializers import (
    CertificationSerializer,
    EducationSerializer,
    ProfileSerializer,
    ProjectSerializer,
    PublicationSerializer,
    SkillSerializer,
    UserProfileSerializer,
    WorkExperienceSerializer,
)
from core.utils.agents.assistant_agent import AssistantAgent

logger: logging.Logger = logging.getLogger(__name__)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            obj.profile.user == request.user
            if hasattr(obj, "profile")
            else obj.user == request.user
        )


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user profiles
    """

    serializer_class: UserProfileSerializer = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields: list[str] = ["city", "state", "country"]
    search_fields: list[str] = ["headline", "professional_summary", "current_position", "company"]
    ordering_fields: list[str] = ["years_of_experience", "created_at", "updated_at"]

    def get_queryset(self) -> QuerySet[UserProfile]:
        # Fix for drf-spectacular schema generation
        if getattr(self, "swagger_fake_view", False):
            return UserProfile.objects.none()

        if isinstance(self.request.user, AnonymousUser):
            return UserProfile.objects.none()

        return UserProfile.objects.filter(user=self.request.user)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="include_related", type=OpenApiTypes.BOOL, description="Include related data"
            )
        ]
    )
    @action(detail=True, methods=["get"])
    def full_profile(self, request, pk=None) -> Response:
        """
        Get the full profile with all related data
        """
        profile: UserProfile = self.get_object()
        include_related: bool = (
            request.query_params.get("include_related", "false").lower() == "true"
        )
        serializer: ProfileSerializer = ProfileSerializer(
            profile, context={"include_related": include_related}
        )
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request) -> Response:
        """
        Get profile statistics
        """
        profile: UserProfile = UserProfile.objects.get(user=request.user)
        stats: dict[str, int | float] = {
            "work_experience_count": profile.work_experiences.count(),
            "education_count": profile.education.count(),
            "skills_count": profile.skills.count(),
            "projects_count": profile.projects.count(),
            "certifications_count": profile.certifications.count(),
            "publications_count": profile.publications.count(),
            "years_of_experience": profile.years_of_experience,
        }
        return Response(stats)


class WorkExperienceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user work experiences
    """

    serializer_class = WorkExperienceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["company", "position", "location", "current"]
    search_fields = ["company", "position", "description", "technologies"]
    ordering_fields = ["start_date", "end_date", "created_at"]

    def get_queryset(self) -> QuerySet[WorkExperience]:
        # Fix for drf-spectacular schema generation
        if getattr(self, "swagger_fake_view", False):
            return WorkExperience.objects.none()

        if isinstance(self.request.user, AnonymousUser):
            return WorkExperience.objects.none()

        return WorkExperience.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def current_position(self, request) -> Response:
        """
        Get the current work position
        """
        current_position: WorkExperience | None = WorkExperience.objects.filter(
            profile__user=request.user, current=True
        ).first()
        if current_position:
            serializer = self.get_serializer(current_position)
            return Response(serializer.data)
        return Response({"detail": "No current position found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["get"])
    def by_company(self, request) -> Response:
        """
        Group work experiences by company
        """
        companies: QuerySet[WorkExperience] = (
            WorkExperience.objects.filter(profile__user=request.user)
            .values("company")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response(companies)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user projects
    """

    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields: list[str] = ["technologies"]
    search_fields: list[str] = ["title", "description", "technologies"]
    ordering_fields: list[str] = ["start_date", "end_date", "created_at"]

    def get_queryset(self) -> QuerySet[Project]:
        # Fix for drf-spectacular schema generation
        if getattr(self, "swagger_fake_view", False):
            return Project.objects.none()

        if isinstance(self.request.user, AnonymousUser):
            return Project.objects.none()

        return Project.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_technology(self, request) -> Response:
        """
        Group projects by technology
        """
        projects: QuerySet[Project] = Project.objects.filter(profile__user=request.user)
        technologies: Dict[str, List[int]] = {}

        for project in projects:
            techs: list[str] = [t.strip() for t in project.technologies.split(",") if t.strip()]
            for tech in techs:
                if tech in technologies:
                    technologies[tech].append(project.pk)
                else:
                    technologies[tech] = [project.pk]

        return Response(technologies)


class EducationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user education
    """

    serializer_class = EducationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields: list[str] = ["institution", "degree", "field_of_study", "current"]
    search_fields: list[str] = ["institution", "degree", "field_of_study", "achievements"]
    ordering_fields: list[str] = ["start_date", "end_date", "gpa", "created_at"]

    def get_queryset(self) -> QuerySet[Education]:
        # Fix for drf-spectacular schema generation
        if getattr(self, "swagger_fake_view", False):
            return Education.objects.none()

        if isinstance(self.request.user, AnonymousUser):
            return Education.objects.none()

        return Education.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_institution(self, request) -> Response:
        """
        Group education entries by institution
        """
        institutions: QuerySet[Education] = (
            Education.objects.filter(profile__user=request.user)
            .values("institution")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response(institutions)


class CertificationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user certifications
    """

    serializer_class = CertificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields: list[str] = ["issuer"]
    search_fields: list[str] = ["name", "issuer", "credential_id"]
    ordering_fields: list[str] = ["issue_date", "expiry_date", "created_at"]

    def get_queryset(self) -> QuerySet[Certification]:
        # Fix for drf-spectacular schema generation
        if getattr(self, "swagger_fake_view", False):
            return Certification.objects.none()

        if isinstance(self.request.user, AnonymousUser):
            return Certification.objects.none()

        return Certification.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_issuer(self, request) -> Response:
        """
        Group certifications by issuer
        """
        issuers: QuerySet[Certification] = (
            Certification.objects.filter(profile__user=request.user)
            .values("issuer")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response(issuers)


class PublicationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user publications
    """

    serializer_class = PublicationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields: list[str] = ["publisher", "journal"]
    search_fields: list[str] = ["title", "authors", "abstract", "doi"]
    ordering_fields: list[str] = ["publication_date", "created_at"]

    def get_queryset(self) -> QuerySet[Publication]:
        # Fix for drf-spectacular schema generation
        if getattr(self, "swagger_fake_view", False):
            return Publication.objects.none()

        if isinstance(self.request.user, AnonymousUser):
            return Publication.objects.none()

        return Publication.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_publisher(self, request) -> Response:
        """
        Group publications by publisher
        """
        publishers: QuerySet[Publication] = (
            Publication.objects.filter(profile__user=request.user)
            .values("publisher")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response(publishers)


class SkillViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user skills
    """

    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields: list[str] = ["category", "proficiency"]
    search_fields: list[str] = ["name", "category"]
    ordering_fields: list[str] = ["proficiency", "created_at"]

    def get_queryset(self) -> QuerySet[Skill]:
        # Fix for drf-spectacular schema generation
        if getattr(self, "swagger_fake_view", False):
            return Skill.objects.none()

        if isinstance(self.request.user, AnonymousUser):
            return Skill.objects.none()

        return Skill.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_category(self, request) -> Response:
        """
        Group skills by category
        """
        categories: QuerySet[Skill] = (
            Skill.objects.filter(profile__user=request.user)
            .values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response(categories)

    @action(detail=False, methods=["get"])
    def by_proficiency(self, request) -> Response:
        """
        Group skills by proficiency level
        """
        proficiency_levels: QuerySet[Skill] = (
            Skill.objects.filter(profile__user=request.user)
            .values("proficiency")
            .annotate(count=Count("id"))
            .order_by("-proficiency")
        )
        return Response(proficiency_levels)


@login_required
@require_POST
def chat_api(request):
    """
    Process a chat message using the RAGProcessor.

    Handles chat interactions, leverages RAG for context-aware responses,
    and persists the conversation.
    """
    try:
        with transaction.atomic():  # Wrap DB operations
            data = json.loads(request.body)
            user_message_content = data.get("message", "")
            conversation_id = data.get("conversation_id")  # Get existing conversation ID

            if not user_message_content:
                return JsonResponse({"error": "No message provided"}, status=400)

            user_id = request.user.id

            # --- Conversation Handling (Same as before) ---
            conversation = None

            first_message_preview = (
                user_message_content[:50] + "..."
                if len(user_message_content) > 50
                else user_message_content
            )
            # --- Ensure Conversation Exists ---
            conversation, created = ChatConversation.objects.get_or_create(
                id=conversation_id,
                user_id=user_id,
                defaults={
                    "title": f"Chat on {date.today().strftime('%Y-%m-%d')}: {first_message_preview}"
                },  # Or generate title later
            )
            if created:
                conversation_id = conversation.id  # Get the new ID

            # Save the user's message BEFORE calling the agent
            ChatMessage.objects.create(
                conversation=conversation, role="user", content=user_message_content
            )

        # --- Agentic RAG Integration ---
        # Initialize AgenticRAGProcessor for the current user and conversation
        agent_processor = AssistantAgent(user_id=user_id, conversation_id=conversation_id)

        # --- Get Response using Agent ---
        assistant_response_content = agent_processor.run(user_message_content)
        # --- End Agentic RAG Integration ---

        with transaction.atomic():
            # Save the assistant's response AFTER getting it from the agent
            ChatMessage.objects.create(
                conversation=conversation, role="assistant", content=assistant_response_content
            )

        # Return response and the conversation ID
        return JsonResponse(
            {
                "response": assistant_response_content,
                "conversation_id": conversation_id,  # Return the potentially new ID
            }
        )

    except json.JSONDecodeError:
        logger.error("Invalid JSON received in chat API")
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        logger.exception(f"Error in chat API (Agentic) for user {request.user.id}: {str(e)}")
        return JsonResponse(
            {"error": "An internal error occurred. Please try again later."}, status=500
        )
