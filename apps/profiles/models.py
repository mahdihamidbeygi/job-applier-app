from django.db import models
from django.conf import settings

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    skills = models.JSONField(default=list)
    experience = models.JSONField(default=list)
    education = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s profile"

class Skill(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    level = models.CharField(max_length=20)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='skill_set')

    def __str__(self):
        return f"{self.name} ({self.category})"

class Experience(models.Model):
    company = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField()
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='experience_set')

    def __str__(self):
        return f"{self.position} at {self.company}" 