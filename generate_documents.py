import os
from datetime import datetime, timedelta

import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_applier.settings")
django.setup()

from celery import group
from django.contrib.auth import get_user_model

from core.models import JobListing, UserProfile

User = get_user_model()


def process_job_listings(user_id, days_back=30):
    """
    Process all available job listings for a user.

    Args:
        user_id (int): The ID of the user
        days_back (int): Number of days to look back for job listings
    """
    try:
        # Get the user and profile
        user = User.objects.get(id=user_id)
        user_profile = UserProfile.objects.get(user=user)
        print(f"Processing jobs for user: {user.username}")

        # Get recent job listings that haven't been processed
        cutoff_date = datetime.now().date() - timedelta(days=days_back)
        job_listings = JobListing.objects.filter(
            posted_date__gte=cutoff_date,
            match_score__isnull=True,  # Only get unprocessed listings
            tailored_resume="",  # No resume generated yet
            tailored_cover_letter="",  # No cover letter generated yet
        )

        total_jobs = job_listings.count()
        print(f"Found {total_jobs} unprocessed job listings")

        if total_jobs == 0:
            print("No new jobs to process")
            return

        # Create a group of tasks for parallel processing
        job_tasks = group(generate_documents_async.s(job.id, user_id) for job in job_listings)

        # Execute tasks
        print("Starting document generation tasks...")
        result = job_tasks.apply_async()

        # Wait for all tasks to complete (with timeout)
        try:
            result.get(timeout=600)  # 10 minutes timeout
            print("All documents generated successfully!")

            # Get updated match scores
            processed_jobs = JobListing.objects.filter(
                id__in=[job.id for job in job_listings], match_score__isnull=False
            ).order_by("-match_score")

            print("\nMatch Score Summary:")
            print("-------------------")
            for job in processed_jobs:
                print(f"{job.title} at {job.company}: {job.match_score:.2f}%")

        except Exception as e:
            print(f"Error waiting for tasks to complete: {str(e)}")

    except Exception as e:
        print(f"Error processing job listings: {str(e)}")


def main():
    # Get user input
    username = input("Enter username: ")
    days = input("Enter number of days to look back (default 30): ")

    try:
        # Get user
        user = User.objects.get(username=username)

        # Process days input
        try:
            days = int(days) if days.strip() else 30
        except ValueError:
            print("Invalid days input, using default of 30 days")
            days = 30

        # Process job listings
        print(f"\nProcessing jobs from the last {days} days...")
        process_job_listings(user.id, days)

    except User.DoesNotExist:
        print(f"User '{username}' not found")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
