import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_applier.settings')
django.setup()

from django.contrib.auth.models import User

from core.models import UserProfile


def create_missing_profiles():
    users_without_profile = User.objects.filter(userprofile__isnull=True)
    profiles_created = 0

    for user in users_without_profile:
        UserProfile.objects.create(user=user)
        profiles_created += 1

    print(f'Successfully created {profiles_created} user profile(s)')

if __name__ == '__main__':
    create_missing_profiles() 