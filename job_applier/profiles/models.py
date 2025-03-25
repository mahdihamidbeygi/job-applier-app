from django.db import models
from django.conf import settings
from job_applier.core.models import TimeStampedModel, SoftDeleteModel


class Profile(TimeStampedModel, SoftDeleteModel):
    """
    User profile model that extends the User model with additional
    professional information.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    full_name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    skills = models.JSONField(default=list)
    experience = models.JSONField(default=list)
    education = models.JSONField(default=list)
    preferred_job_types = models.JSONField(default=list)
    preferred_locations = models.JSONField(default=list)
    preferred_industries = models.JSONField(default=list)
    salary_expectations = models.JSONField(default=dict)
    availability = models.DateField(null=True, blank=True)
    is_public = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}'s Profile"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('profiles:detail', kwargs={'pk': self.pk})
