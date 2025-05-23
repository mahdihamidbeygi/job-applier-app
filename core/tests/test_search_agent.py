import json
import django
import os
import sys

from django.db.models.manager import BaseManager

# --- Add Django Setup ---
# Add the project root directory to Python path if running script directly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_applier.settings")
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)
# --- End Django Setup ---


from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.utils import timezone

from core.models import JobListing, UserProfile
from core.utils.agents.search_agent import SearchAgent
from core.utils.agents.job_agent import JobAgent


# def test_search_jobs_calls_correct_scraper():
#     # Instantiate the SearchAgent
#     searcher = SearchAgent(user_id=1)
#     expected_linkedin_jobs = [{"title": "LinkedIn Developer", "company": "LI Corp"}]
#     result = searcher.search_jobs(role="developer", location="San Francisco", platform="linkedin")

#     # Ensure the correct scraper was called
#     searcher.linkedin_scraper.search_jobs.assert_called_once_with(
#         role="developer", location="San Francisco"
#     )
#     print(result)
#     assert len(result) > 0


# def test_process_jobs_creates_new_listings_and_skips_duplicates():
#     # Instantiate the SearchAgent
#     searcher = SearchAgent(user_id=1)
#     source_platform = "test_platform_alpha"
#     # Sample data from a scraper
#     job1: BaseManager[JobListing] = JobListing.objects.filter(id=300).first()
#     job2: BaseManager[JobListing] = JobListing.objects.filter(id=301).first()
#     job3: BaseManager[JobListing] = JobListing.objects.filter(id=302).first()
#     job4: BaseManager[JobListing] = JobListing.objects.filter(id=303).first()
#     print(job1)
#     scraped_jobs_data = [
#         {
#             "title": job1.title,
#             "company": job1.company,
#             "location": job1.location,
#             "description": job1.description,
#             "source_url": job1.source_url,
#         },
#         {
#             "title": job2.title,
#             "company": job2.company,
#             "location": job2.location,
#             "description": job2.description,
#             "source_url": job2.source_url,
#         },
#         None,  # To ensure None values are handled gracefully
#         {
#             "title": job3.title,
#             "company": job3.company,
#             "location": job3.location,
#             "description": job3.description,
#             "source_url": job3.source_url,
#         },
#     ]

#     # # Pre-populate an existing job that should be skipped
#     # JobListing.objects.create(
#     #     title="Existing Alpha Job",
#     #     company="Gamma Inc",
#     #     location="Gamma Ville",
#     #     source=source_platform,  # Same source
#     #     description="Original Gamma Description",
#     #     posted_date=timezone.now().date(),
#     # )

#     processed_listings = searcher.process_jobs(scraped_jobs_data, source_platform)


def test__queue_resume_generation_success():
    """Test successful resume generation"""
    # Setup mocks
    joblisting: JobListing = JobListing.objects.get(id=537)
    # mock_job_agent.return_value = JobAgent(id=537, user_id=1)
    searcher = SearchAgent(user_id=1)

    # Call the function (you'll need to adjust this based on your actual class structure)
    result = searcher._queue_resume_generation(job_listing=joblisting)
