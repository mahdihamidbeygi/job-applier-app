from django.apps import AppConfig
import os


class ProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "profiles"
    verbose_name = "Profiles"
    path = os.path.dirname(os.path.abspath(__file__))
