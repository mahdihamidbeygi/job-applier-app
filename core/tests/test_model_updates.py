import logging
import os
import sys
import unittest
from datetime import date

import django

# --- Add Django Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_applier.settings")
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)
# --- End Django Setup ---

from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import JobListing, UserProfile
from core.utils.agents.job_agent import JobAgent
from core.utils.agents.personal_agent import PersonalAgent

logger = logging.getLogger(__name__)
User = get_user_model()


class TestModelUpdates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Get or create the test user with ID 1
        cls.user, user_created = User.objects.get_or_create(
            id=1,
            defaults={
                "username": "test_updater_user",
                "email": "test_updater@example.com",
                "first_name": "Test",
                "last_name": "Updater",
            },
        )
        if user_created:
            cls.user.set_password("password123")
            cls.user.save()
            logger.info(f"Created test user: {cls.user.username} (ID: {cls.user.id})")
        else:
            logger.info(f"Using existing test user: {cls.user.username} (ID: {cls.user.id})")

        # Ensure UserProfile exists for this user
        cls.user_profile, profile_created = UserProfile.objects.get_or_create(user=cls.user)
        if profile_created:
            logger.info(f"Created UserProfile for user ID {cls.user.id}")

        # Get or create the test JobListing with ID 219 for user_id=1
        cls.job, job_created = JobListing.objects.get_or_create(
            id=219,
            user=cls.user,
            defaults={
                "title": "Initial Test Job Title",
                "company": "Initial Test Company",
                "description": "This is an initial description for the test job.",
                "posted_date": timezone.now().date(),
            },
        )
        if job_created:
            logger.info(f"Created test JobListing with ID 219 for user {cls.user.username}")
        else:
            logger.info(f"Using existing JobListing with ID 219 for user {cls.user.username}")

    def test_update_user_profile(self):
        logger.info(f"Running test_update_user_profile for user_id={self.user.id}")
        personal_agent = PersonalAgent(user_id=self.user.id)

        update_data = {
            "title": "Senior Test Engineer",
            "professional_summary": "An updated professional summary for testing purposes.",
            "phone": "1234567890",
            "city": "Testville",
        }

        success, message = personal_agent.update_profile(update_data)

        self.assertTrue(success, f"UserProfile update failed: {message}")
        logger.info(f"UserProfile update message: {message}")

        # Verify the changes in the database
        updated_profile = UserProfile.objects.get(user_id=self.user.id)
        self.assertEqual(updated_profile.title, update_data["title"])
        self.assertEqual(updated_profile.professional_summary, update_data["professional_summary"])
        self.assertEqual(updated_profile.phone, update_data["phone"])
        self.assertEqual(updated_profile.city, update_data["city"])
        logger.info("UserProfile successfully updated and verified.")

    def test_update_job_listing(self):
        logger.info(
            f"Running test_update_job_listing for user_id={self.user.id}, job_id={self.job.id}"
        )
        job_agent = JobAgent(user_id=self.user.id, job_id=self.job.id)

        update_data = {
            "application_status": "Applied",
            "applied": True,
            "application_date": date(2024, 1, 15),
            "is_active": False,
        }

        success, message = job_agent.update_job_listing(update_data)

        self.assertTrue(success, f"JobListing update failed: {message}")
        logger.info(f"JobListing update message: {message}")

        # Verify the changes in the database
        updated_job = JobListing.objects.get(id=self.job.id, user_id=self.user.id)
        self.assertEqual(updated_job.application_status, update_data["application_status"])
        self.assertEqual(updated_job.applied, update_data["applied"])
        self.assertEqual(updated_job.application_date, update_data["application_date"])
        self.assertEqual(updated_job.is_active, update_data["is_active"])
        logger.info("JobListing successfully updated and verified.")


if __name__ == "__main__":
    unittest.main()
