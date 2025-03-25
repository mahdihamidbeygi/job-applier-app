from django.apps import AppConfig
import os


class JobsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jobs"
    verbose_name = "Jobs"
    path = os.path.dirname(os.path.abspath(__file__))
