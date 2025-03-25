from django.apps import AppConfig
import os


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = "Users"
    path = os.path.dirname(os.path.abspath(__file__))
