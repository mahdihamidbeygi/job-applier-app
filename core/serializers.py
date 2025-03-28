from rest_framework import serializers
from .models import (
    UserProfile, WorkExperience, Project, Education,
    Certification, Publication, Skill
)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'id', 'phone', 'address', 'city', 'state', 'country', 'postal_code',
            'website', 'linkedin', 'github', 'headline', 'professional_summary',
            'current_position', 'company', 'years_of_experience', 'resume'
        ]
        read_only_fields = ['id']

class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = [
            'id', 'company', 'position', 'location', 'start_date', 'end_date',
            'current', 'description', 'achievements', 'technologies', 'order'
        ]
        read_only_fields = ['id', 'order']

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'technologies', 'start_date', 'end_date',
            'github_url', 'live_url', 'order'
        ]
        read_only_fields = ['id', 'order']

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            'id', 'institution', 'degree', 'field_of_study', 'start_date', 'end_date',
            'current', 'gpa', 'achievements', 'order'
        ]
        read_only_fields = ['id', 'order']

class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = [
            'id', 'name', 'issuer', 'issue_date', 'expiry_date',
            'credential_id', 'credential_url', 'order'
        ]
        read_only_fields = ['id', 'order']

class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = [
            'id', 'title', 'authors', 'publication_date', 'publisher',
            'journal', 'doi', 'abstract', 'url', 'order'
        ]
        read_only_fields = ['id', 'order']

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name', 'category', 'proficiency', 'order']
        read_only_fields = ['id', 'order']

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
            'id', 'phone', 'address', 'city', 'state', 'country', 'postal_code',
            'website', 'linkedin', 'github', 'headline', 'professional_summary',
            'current_position', 'company', 'years_of_experience', 'resume',
            'work_experiences', 'projects', 'education', 'certifications',
            'publications', 'skills'
        ]
        read_only_fields = ['id'] 