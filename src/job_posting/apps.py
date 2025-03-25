from django.apps import AppConfig


class JobPostingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.job_posting"
    verbose_name = "Job Postings"
    label = "job_posting"
