from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Basic Information
    name = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)

    # Contact Information
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)

    # Professional Summary
    headline = models.CharField(max_length=100, blank=True)
    professional_summary = models.TextField(blank=True)
    current_position = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)

    # Resume
    resume = models.FileField(upload_to="resumes/", blank=True)
    parsed_resume_data = models.JSONField(default=dict, blank=True)

    # GitHub Data
    github_data = models.JSONField(default=dict, blank=True)
    last_github_refresh = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    @property
    def years_of_experience(self):
        """Calculate total years of experience from work experiences"""
        if not self.work_experiences.exists():
            return 0

        total_months = 0
        for exp in self.work_experiences.all():
            start_date = exp.start_date
            end_date = (
                exp.end_date or date.today()
            )  # Use today's date if end_date is None (current job)

            # Calculate months between dates
            delta = relativedelta(end_date, start_date)
            months = delta.years * 12 + delta.months

            total_months += months

        # Convert total months to years (rounded to 1 decimal place)
        return round(total_months / 12, 1)


class WorkExperience(models.Model):
    profile = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="work_experiences"
    )
    company = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    current = models.BooleanField(default=False)
    description = models.TextField()
    achievements = models.TextField(blank=True)
    technologies = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-start_date", "-order"]

    def __str__(self):
        return f"{self.position} at {self.company}"


class Project(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    current = models.BooleanField(default=False)
    technologies = models.TextField(blank=True)
    github_url = models.URLField(blank=True)
    live_url = models.URLField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-start_date", "-order"]

    def __str__(self):
        return self.title


class Education(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="education")
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    current = models.BooleanField(default=False)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    achievements = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-start_date", "-order"]

    def __str__(self):
        return f"{self.degree} in {self.field_of_study}"


class Certification(models.Model):
    profile = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="certifications"
    )
    name = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=100, blank=True)
    credential_url = models.URLField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-issue_date", "-order"]

    def __str__(self):
        return f"{self.name} from {self.issuer}"


class Publication(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="publications")
    title = models.CharField(max_length=500)
    authors = models.TextField()
    publication_date = models.DateField()
    publisher = models.CharField(max_length=200)
    journal = models.CharField(max_length=200, blank=True)
    doi = models.CharField(max_length=100, blank=True)
    url = models.URLField(blank=True)
    abstract = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-publication_date", "-order"]

    def __str__(self):
        return self.title


class Skill(models.Model):
    SKILL_CATEGORIES = [
        ("programming", "Programming Languages"),
        ("frameworks", "Frameworks & Libraries"),
        ("databases", "Databases"),
        ("tools", "Tools & Technologies"),
        ("soft_skills", "Soft Skills"),
        ("languages", "Languages"),
        ("other", "Other"),
    ]

    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=SKILL_CATEGORIES)
    proficiency = models.IntegerField(choices=[(i, i) for i in range(1, 6)], default=3)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["category", "-proficiency", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class JobListing(models.Model):
    JOB_SOURCES = [
        ("linkedin", "LinkedIn"),
        ("indeed", "Indeed"),
        ("glassdoor", "Glassdoor"),
        ("monster", "Monster"),
        ("jobbank", "JobBank"),
        ("ziprecruiter", "ZipRecruiter"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=500)
    company = models.CharField(max_length=500)
    location = models.CharField(max_length=500)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    source = models.CharField(max_length=20, choices=JOB_SOURCES)
    source_url = models.URLField()
    posted_date = models.DateField()
    salary_range = models.CharField(max_length=100, blank=True)
    job_type = models.CharField(max_length=200, blank=True)  # Full-time, Part-time, Contract, etc.
    experience_level = models.CharField(max_length=200, blank=True)
    required_skills = models.JSONField(default=list)
    preferred_skills = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    match_score = models.FloatField(null=True, blank=True)
    tailored_resume = models.FileField(upload_to="tailored_resumes/", blank=True, max_length=500)
    tailored_cover_letter = models.FileField(
        upload_to="tailored_cover_letters/", blank=True, max_length=500
    )
    applied = models.BooleanField(default=False)
    application_date = models.DateField(null=True, blank=True)
    application_status = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-posted_date", "-match_score"]
        indexes = [
            models.Index(fields=["title", "company", "location"]),
            models.Index(fields=["posted_date"]),
            models.Index(fields=["match_score"]),
        ]

    def __str__(self):
        return f"{self.title} at {self.company}"

    def get_resume_url(self):
        """Get the URL for the tailored resume"""
        if self.tailored_resume:
            return self.tailored_resume.url
        return None

    def get_cover_letter_url(self):
        """Get the URL for the tailored cover letter"""
        if self.tailored_cover_letter:
            return self.tailored_cover_letter.url
        return None

    @property
    def has_tailored_documents(self):
        """Check if both tailored documents exist"""
        return bool(self.tailored_resume and self.tailored_cover_letter)


class JobPlatformPreference(models.Model):
    """Model to store user preferences for job platforms"""

    user_profile = models.OneToOneField(
        UserProfile, on_delete=models.CASCADE, related_name="job_platform_preferences"
    )
    preferred_platforms = models.JSONField(
        default=list, help_text="List of preferred job platforms from JOB_SOURCES"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_profile.user.username}'s job platform preferences"

    def get_preferred_platforms_display(self):
        """Get human-readable list of preferred platforms"""
        return [dict(JobListing.JOB_SOURCES)[platform] for platform in self.preferred_platforms]

    class Meta:
        verbose_name = "Job Platform Preference"
        verbose_name_plural = "Job Platform Preferences"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()
