from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from typing import Union
from datetime import date

from .models import (
    Certification,
    Education,
    Project,
    Publication,
    Skill,
    UserProfile,
    WorkExperience,
)


class UserProfileSerializer(serializers.ModelSerializer):

    years_of_experience = serializers.SerializerMethodField()

    @extend_schema_field(serializers.IntegerField)
    def get_years_of_experience(self, obj) -> int:
        """Calculate years of experience"""
        # Your existing calculation logic here
        if hasattr(obj, "years_of_experience") and obj.years_of_experience:
            return obj.years_of_experience

        # Calculate from work experiences if not directly available
        if hasattr(obj, "work_experiences"):

            total_years = 0
            for exp in obj.work_experiences.all():
                if exp.start_date:
                    end_date = exp.end_date or date.today()
                    years = (end_date - exp.start_date).days / 365.25
                    total_years += years
            return int(total_years)

        return 0

    class Meta:
        model = UserProfile
        fields = "__all__"
        read_only_fields = ["id"]


class WorkExperienceSerializer(serializers.ModelSerializer):

    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = WorkExperience
        fields = [
            "id",
            "company",
            "position",
            "location",
            "start_date",
            "end_date",
            "description",
            "achievements",
            "technologies",
            "order",
            "is_current",
        ]
        read_only_fields = ["id", "order"]


class ProjectSerializer(serializers.ModelSerializer):

    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "description",
            "technologies",
            "start_date",
            "end_date",
            "github_url",
            "live_url",
            "order",
            "is_current",
        ]
        read_only_fields = ["id", "order"]


class EducationSerializer(serializers.ModelSerializer):

    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = Education
        fields = [
            "id",
            "institution",
            "degree",
            "field_of_study",
            "start_date",
            "end_date",
            "gpa",
            "achievements",
            "order",
            "is_current",
        ]
        read_only_fields = ["id", "order"]


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = [
            "id",
            "name",
            "issuer",
            "issue_date",
            "expiry_date",
            "credential_id",
            "credential_url",
            "order",
        ]
        read_only_fields = ["id", "order"]


class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = [
            "id",
            "title",
            "authors",
            "publication_date",
            "publisher",
            "journal",
            "doi",
            "abstract",
            "url",
            "order",
        ]
        read_only_fields = ["id", "order"]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name", "category", "proficiency", "order"]
        read_only_fields = ["id", "order"]


class ProfileSerializer(serializers.ModelSerializer):
    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    projects = ProjectSerializer(many=True, read_only=True)
    education = EducationSerializer(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    publications = PublicationSerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "phone",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "website",
            "linkedin_url",
            "github_url",
            "headline",
            "professional_summary",
            "current_position",
            "company",
            "years_of_experience",
            "resume",
            "work_experiences",
            "projects",
            "education",
            "certifications",
            "publications",
            "skills",
            "github_data",
        ]
        read_only_fields = ["id"]
