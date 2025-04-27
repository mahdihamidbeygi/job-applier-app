import os
from datetime import datetime

import django
from celery.exceptions import TimeoutError
from django.conf import settings

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_applier.settings")
django.setup()

from django.contrib.auth import get_user_model

from core.models import JobListing, UserProfile
from core.tasks import generate_documents_async

User = get_user_model()


def test_generate_documents():
    try:
        # Get or create test user
        user, created = User.objects.get_or_create(
            username="testuser", defaults={"email": "test@example.com", "password": "testpass123"}
        )

        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={"title": "Software Engineer", "professional_summary": "Test summary"},
        )

        # Get or create test job listing
        job_listing, created = JobListing.objects.get_or_create(
            title="Software Engineer",
            company="Test Company",
            defaults={
                "description": "Test job description",
                "required_skills": ["Python", "Django"],
                "posted_date": datetime.now().date(),
            },
        )

        print(f"Starting document generation for job {job_listing.id} and user {user.id}")

        # Call the task
        task = generate_documents_async.delay(job_listing.id, user.id)

        print(f"Task created with ID: {task.id}")
        print("Waiting for task to complete (this may take a few minutes)...")

        try:
            # Wait for task to complete with a longer timeout
            result = task.get(timeout=300)  # 5 minutes timeout
            print("Task completed successfully!")

        except TimeoutError:
            print("Task is taking longer than expected. Current status:")
            print(f"Task state: {task.state}")
            print(f"Task info: {task.info}")

        except Exception as e:
            print(f"Task failed with error: {str(e)}")
            print(f"Task state: {task.state}")
            print(f"Task info: {task.info}")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    test_generate_documents()
