import os
import time

import django
from django.db.models import Q

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_applier.settings')
django.setup()

from core.models import JobListing, UserProfile
from core.tasks import generate_documents_async


def process_unhandled_jobs():
    """
    Process all job listings that don't have documents or match scores.
    Process one job at a time sequentially.
    """
    try:
        # Get all jobs that need processing (no documents or no match score)
        unprocessed_jobs = JobListing.objects.filter(
            Q(tailored_resume='') | 
            Q(tailored_cover_letter='') |
            Q(match_score__isnull=True)
        )
        
        total_jobs = unprocessed_jobs.count()
        print(f"Found {total_jobs} unprocessed job listings")
        
        if total_jobs == 0:
            print("No jobs need processing")
            return
        
        # Get the default user profile (assuming single user system for now)
        user_profile = UserProfile.objects.first()
        if not user_profile:
            print("No user profile found. Please create a user profile first.")
            return
        
        # Process jobs one at a time
        processed_count = 0
        for job in unprocessed_jobs:
            processed_count += 1
            print(f"\nProcessing job {processed_count} of {total_jobs}")
            print(f"Job: {job.title} at {job.company}")
            
            try:
                # Process single job
                result = generate_documents_async.delay(job.id, user_profile.user.id)
                
                # Wait for job to complete with timeout
                result.get(timeout=300)  # 5 minutes timeout per job
                print(f"✓ Job processed successfully!")
                
                # Show updated match score
                job.refresh_from_db()
                if job.match_score is not None:
                    print(f"Match Score: {job.match_score:.2f}%")
                
                # Add a small delay between jobs
                if processed_count < total_jobs:
                    print("Waiting 10 seconds before next job...")
                    time.sleep(10)
                
            except Exception as e:
                print(f"✗ Error processing job: {str(e)}")
                print("Continuing with next job...")
                continue
        
        # Print final summary
        print("\nFinal Processing Summary:")
        print("-----------------------")
        print(f"Total jobs processed: {processed_count}")
        
        # Show top overall matches
        top_matches = JobListing.objects.filter(
            match_score__isnull=False
        ).order_by('-match_score')[:5]
        
        print("\nTop Overall Matches:")
        for job in top_matches:
            print(f"{job.title} at {job.company}: {job.match_score:.2f}%")
    
    except Exception as e:
        print(f"Error processing job listings: {str(e)}")

if __name__ == '__main__':
    print("Starting job processing...")
    process_unhandled_jobs() 