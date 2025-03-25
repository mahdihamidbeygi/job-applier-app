from django.apps import AppConfig
import os


class ApplicationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "applications"
    verbose_name = "Applications"
    path = os.path.dirname(os.path.abspath(__file__))
