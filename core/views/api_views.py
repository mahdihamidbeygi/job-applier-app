"""
API ViewSets for the core app.
"""

import logging

from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import (
    Certification,
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

logger = logging.getLogger(__name__)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
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

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["city", "state", "country"]
    search_fields = ["headline", "professional_summary", "current_position", "company"]
    ordering_fields = ["years_of_experience", "created_at", "updated_at"]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="include_related", type=OpenApiTypes.BOOL, description="Include related data"
            )
        ]
    )
    @action(detail=True, methods=["get"])
    def full_profile(self, request, pk=None):
        """
        Get the full profile with all related data
        """
        profile = self.get_object()
        include_related = request.query_params.get("include_related", "false").lower() == "true"
        serializer = ProfileSerializer(profile, context={"include_related": include_related})
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get profile statistics
        """
        profile = UserProfile.objects.get(user=request.user)
        stats = {
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

    def get_queryset(self):
        return WorkExperience.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def current_position(self, request):
        """
        Get the current work position
        """
        current_position = WorkExperience.objects.filter(
            profile__user=request.user, current=True
        ).first()
        if current_position:
            serializer = self.get_serializer(current_position)
            return Response(serializer.data)
        return Response({"detail": "No current position found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["get"])
    def by_company(self, request):
        """
        Group work experiences by company
        """
        companies = (
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
    filterset_fields = ["technologies"]
    search_fields = ["title", "description", "technologies"]
    ordering_fields = ["start_date", "end_date", "created_at"]

    def get_queryset(self):
        return Project.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_technology(self, request):
        """
        Group projects by technology
        """
        projects = Project.objects.filter(profile__user=request.user)
        technologies = {}

        for project in projects:
            techs = [t.strip() for t in project.technologies.split(",") if t.strip()]
            for tech in techs:
                if tech in technologies:
                    technologies[tech].append(project.id)
                else:
                    technologies[tech] = [project.id]

        return Response(technologies)


class EducationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user education
    """

    serializer_class = EducationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["institution", "degree", "field_of_study", "current"]
    search_fields = ["institution", "degree", "field_of_study", "achievements"]
    ordering_fields = ["start_date", "end_date", "gpa", "created_at"]

    def get_queryset(self):
        return Education.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_institution(self, request):
        """
        Group education entries by institution
        """
        institutions = (
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
    filterset_fields = ["issuer"]
    search_fields = ["name", "issuer", "credential_id"]
    ordering_fields = ["issue_date", "expiry_date", "created_at"]

    def get_queryset(self):
        return Certification.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_issuer(self, request):
        """
        Group certifications by issuer
        """
        issuers = (
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
    filterset_fields = ["publisher", "journal"]
    search_fields = ["title", "authors", "abstract", "doi"]
    ordering_fields = ["publication_date", "created_at"]

    def get_queryset(self):
        return Publication.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_publisher(self, request):
        """
        Group publications by publisher
        """
        publishers = (
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
    filterset_fields = ["category", "proficiency"]
    search_fields = ["name", "category"]
    ordering_fields = ["proficiency", "created_at"]

    def get_queryset(self):
        return Skill.objects.filter(profile__user=self.request.user)

    @action(detail=False, methods=["get"])
    def by_category(self, request):
        """
        Group skills by category
        """
        categories = (
            Skill.objects.filter(profile__user=request.user)
            .values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response(categories)

    @action(detail=False, methods=["get"])
    def by_proficiency(self, request):
        """
        Group skills by proficiency level
        """
        proficiency_levels = (
            Skill.objects.filter(profile__user=request.user)
            .values("proficiency")
            .annotate(count=Count("id"))
            .order_by("-proficiency")
        )
        return Response(proficiency_levels)
