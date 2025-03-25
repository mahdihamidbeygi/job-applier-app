from django.db import models
from django.conf import settings
from job_applier.core.models import TimeStampedModel, SoftDeleteModel


class JobSearch(TimeStampedModel, SoftDeleteModel):
    """
    Model for storing job search criteria and preferences.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_searches'
    )
    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    keywords = models.JSONField(default=list)
    excluded_keywords = models.JSONField(default=list)
    job_types = models.JSONField(default=list)
    experience_level = models.CharField(max_length=50, blank=True)
    salary_range = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    notification_preferences = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'Job Search'
        verbose_name_plural = 'Job Searches'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}'s search for {self.title}"


class Job(TimeStampedModel, SoftDeleteModel):
    """
    Model for storing job listings from various sources.
    """
    search = models.ForeignKey(
        JobSearch,
        on_delete=models.CASCADE,
        related_name='jobs',
        null=True,
        blank=True
    )
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.JSONField(default=list)
    salary_range = models.JSONField(default=dict)
    job_type = models.CharField(max_length=50)
    experience_level = models.CharField(max_length=50)
    url = models.URLField()
    source = models.CharField(max_length=50)  # e.g., 'indeed', 'linkedin', etc.
    posted_date = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    is_expired = models.BooleanField(default=False)
    is_applied = models.BooleanField(default=False)
    application_url = models.URLField(null=True, blank=True)
    company_logo = models.URLField(null=True, blank=True)
    company_description = models.TextField(null=True, blank=True)
    benefits = models.JSONField(default=list)
    remote_work = models.BooleanField(default=False)
    visa_sponsorship = models.BooleanField(default=False)
    match_score = models.FloatField(null=True, blank=True)
    match_details = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'Job'
        verbose_name_plural = 'Jobs'
        ordering = ['-posted_date']
        indexes = [
            models.Index(fields=['title', 'company', 'location']),
            models.Index(fields=['posted_date']),
            models.Index(fields=['is_expired']),
            models.Index(fields=['is_applied']),
        ]

    def __str__(self):
        return f"{self.title} at {self.company}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('jobs:detail', kwargs={'pk': self.pk})
