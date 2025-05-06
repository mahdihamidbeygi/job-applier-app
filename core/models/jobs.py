"""
Job-related models.
"""

from django.conf import settings
from django.db import models

from .base import TimestampMixin
from .profile import UserProfile


class JobListing(TimestampMixin):
    """Model for job listings"""

    JOB_SOURCES: list[tuple[str, str]] = [
        ("linkedin", "LinkedIn"),
        ("indeed", "Indeed"),
        ("glassdoor", "Glassdoor"),
        ("monster", "Monster"),
        ("jobbank", "JobBank"),
        ("ziprecruiter", "ZipRecruiter"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_listings", null=True
    )
    title = models.CharField(max_length=100, null=True, blank=True)
    company = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    requirements = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=100, choices=JOB_SOURCES, null=True, blank=True)
    source_url = models.URLField(max_length=500, blank=True, null=True)
    posted_date = models.DateField(blank=True, null=True)
    salary_range = models.CharField(max_length=100, blank=True, null=True)
    job_type = models.CharField(
        max_length=200, blank=True, null=True
    )  # Full-time, Part-time, Contract, etc.
    benefits = models.TextField(blank=True, null=True)
    experience_level = models.CharField(max_length=200, blank=True, null=True)
    required_skills = models.JSONField(default=list, blank=True, null=True)
    preferred_skills = models.JSONField(default=list, blank=True, null=True)
    is_active = models.BooleanField(default=True, null=True, blank=True)
    match_score = models.FloatField(null=True, blank=True)
    tailored_resume = models.FileField(
        upload_to="tailored_resumes/", blank=True, max_length=500, null=True
    )
    tailored_cover_letter = models.FileField(
        upload_to="tailored_cover_letters/", blank=True, max_length=500
    )
    applied = models.BooleanField(default=False, null=True, blank=True)
    application_date = models.DateField(null=True, blank=True)
    application_status = models.CharField(max_length=200, blank=True, null=True)
    how_to_apply = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-posted_date", "-match_score"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["company"]),
            models.Index(fields=["posted_date"]),
            models.Index(fields=["match_score"]),
        ]

    def __str__(self):
        return f"{self.title} at {self.company}"

    def get_resume_url(self):
        """Get the URL for the tailored resume if it exists"""
        return self.tailored_resume.url if self.tailored_resume else None

    def get_cover_letter_url(self):
        """Get the URL for the tailored cover letter if it exists"""
        return self.tailored_cover_letter.url if self.tailored_cover_letter else None

    @property
    def has_tailored_documents(self):
        """Check if the job has tailored documents"""
        return bool(self.tailored_resume or self.tailored_cover_letter)


class JobPlatformPreference(TimestampMixin):
    """Model to store user preferences for job platforms"""

    user_profile = models.OneToOneField(
        UserProfile, on_delete=models.CASCADE, related_name="job_platform_preferences"
    )
    preferred_platforms = models.JSONField(
        default=list, help_text="List of preferred job platforms"
    )

    def __str__(self):
        return f"{self.user_profile.user.username}'s job platform preferences"

    def get_preferred_platforms_display(self):
        """Get a display-friendly list of preferred platforms"""
        platforms_dict = dict(JobListing.JOB_SOURCES)
        return [platforms_dict.get(p, p) for p in self.preferred_platforms]

    class Meta:
        verbose_name = "Job Platform Preference"
        verbose_name_plural = "Job Platform Preferences"
