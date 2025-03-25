from django.db import models
from django.conf import settings

class Job(models.Model):
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    job_type = models.CharField(max_length=50)  # Full-time, Part-time, Contract, etc.
    salary_range = models.CharField(max_length=100, blank=True)
    url = models.URLField()
    source = models.CharField(max_length=50)  # LinkedIn, Indeed, etc.
    posted_date = models.DateTimeField()
    scraped_date = models.DateTimeField(auto_now_add=True)
    requirements = models.JSONField(default=list)
    status = models.CharField(max_length=50, default='active')  # active, filled, expired
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} at {self.company}"

class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('applied', 'Applied'),
        ('interviewing', 'Interviewing'),
        ('rejected', 'Rejected'),
        ('accepted', 'Accepted'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    cover_letter = models.TextField(blank=True)
    applied_date = models.DateTimeField(null=True, blank=True)
    responses = models.JSONField(default=dict)  # Store form responses
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s application for {self.job.title}"

class JobSearch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    keywords = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    job_type = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s search for {self.keywords}" 