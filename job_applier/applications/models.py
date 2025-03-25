from django.db import models
from django.conf import settings
from job_applier.core.models import TimeStampedModel, SoftDeleteModel
from django.urls import reverse
from django.utils import timezone

class Application(TimeStampedModel, SoftDeleteModel):
    """
    Model for tracking job applications and their status.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('applied', 'Applied'),
        ('interviewing', 'Interviewing'),
        ('offered', 'Offered'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('accepted', 'Accepted'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='applications'
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='draft'
    )
    cover_letter = models.TextField()
    resume_version = models.FileField(upload_to='application_resumes/')
    applied_date = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    interview_notes = models.JSONField(default=list)
    follow_up_reminder = models.DateTimeField(null=True, blank=True)
    ai_generated = models.BooleanField(default=False)
    ai_feedback = models.JSONField(default=dict)
    application_url = models.URLField(null=True, blank=True)
    tracking_id = models.CharField(max_length=100, null=True, blank=True)
    company_response = models.TextField(blank=True)
    next_steps = models.TextField(blank=True)
    salary_negotiation = models.JSONField(default=dict)
    benefits_negotiation = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['applied_date']),
            models.Index(fields=['user', 'job']),
        ]

    def __str__(self):
        return f"{self.user.email}'s application for {self.job.title}"

    def get_absolute_url(self):
        return reverse('applications:detail', kwargs={'pk': self.pk})

    def apply(self):
        """Mark the application as submitted."""
        self.status = 'applied'
        self.applied_date = timezone.now()
        self.save()

    def update_status(self, new_status):
        """Update the application status."""
        self.status = new_status
        self.save()

class ApplicationHistory(TimeStampedModel):
    """Model for tracking application status changes."""
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=50, choices=Application.STATUS_CHOICES)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Application History'
        verbose_name_plural = 'Application History'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application} - {self.status} at {self.created_at}"
