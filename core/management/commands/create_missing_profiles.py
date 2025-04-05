from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import UserProfile


class Command(BaseCommand):
    help = 'Creates UserProfile objects for users that do not have one'

    def handle(self, *args, **options):
        users_without_profile = User.objects.filter(userprofile__isnull=True)
        profiles_created = 0

        for user in users_without_profile:
            UserProfile.objects.create(user=user)
            profiles_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {profiles_created} user profile(s)'
            )
        ) 