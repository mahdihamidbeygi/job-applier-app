from django.apps import AppConfig


class JobApplicationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.job_application"
    verbose_name = "Job Applications"
    label = "job_application"
