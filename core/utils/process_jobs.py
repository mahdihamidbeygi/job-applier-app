import os
import time

import django
from django.db.models import Q

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_applier.settings')
django.setup()

from core.models import JobListing, UserProfile
from core.utils.agents.personal_agent import PersonalAgent, PersonalBackground
from core.utils.agents.search_agent import SearchAgent


def calculate_match_score(job, user):
    """Calculate match score for a job using PersonalAgent and SearchAgent"""
    try:
        # Initialize personal agent first
        personal_agent = PersonalAgent(user.id)
        
        # Initialize search agent with user_id and personal_agent
        search_agent = SearchAgent(user.id, personal_agent)

        # Get user profile
        user_profile = UserProfile.objects.get(user_id=user.id)

        # Create PersonalBackground object
        background = PersonalBackground(
            profile=user_profile.__dict__,
            work_experience=list(user_profile.work_experiences.values()),
            education=list(user_profile.education.values()),
            skills=list(user_profile.skills.values()),
            projects=list(user_profile.projects.values()),
            github_data=user_profile.github_data,
            achievements=[],  # We'll add this field to the model later
            interests=[],  # We'll add this field to the model later
        )

        # Load background first
        personal_agent.load_background(background)

        # Get job details
        job_details = {
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "location": job.location,
            "requirements": job.requirements,
            "source": job.source,
            "source_url": job.source_url,
            "posted_date": job.posted_date,
            "applied": job.applied,
            "match_score": job.match_score,
            "id": job.id,
        }

        # Analyze job fit using search agent
        analysis = search_agent.analyze_job_fit(job_details)
        
        # Extract match score from analysis
        match_score = float(analysis.get("match_score", 0))
        
        return match_score
    except Exception as e:
        print(f"Error calculating match score: {str(e)}")
        return 0.0

def process_job(job, user):
    """Process a single job by calculating and saving its match score"""
    try:
        # Calculate match score
        match_score = calculate_match_score(job, user)
        
        # Save match score to database
        job.match_score = match_score
        job.save()
        
        print(f"✓ Match score calculated successfully!")
        print(f"Match Score: {match_score:.2f}%")
        
        return True
    except Exception as e:
        print(f"Error processing job: {str(e)}")
        return False

def process_unscored_jobs():
    """Process all jobs that don't have a match score"""
    try:
        # Get all users
        users = UserProfile.objects.all()
        
        if not users.exists():
            print("No users found in the database.")
            return
            
        # Get all jobs without match scores
        jobs = JobListing.objects.filter(match_score__isnull=True)
        
        if not jobs.exists():
            print("No jobs found without match scores.")
            return
            
        print(f"Found {jobs.count()} jobs without match scores")
        
        # Process each job
        for i, job in enumerate(jobs, 1):
            print(f"\nProcessing job {i} of {jobs.count()}")
            print(f"Job: {job.title} at {job.company}")
            
            # Process with first user (assuming single user system for now)
            success = process_job(job, users.first())
            
            if not success:
                print("Failed to process job")
                
            # Add delay between jobs to avoid overwhelming the system
            if i < jobs.count():
                print("Waiting 10 seconds before next job...")
                time.sleep(10)
                
        print("\nFinished processing all jobs!")
        
    except Exception as e:
        print(f"Error in process_unscored_jobs: {str(e)}")

if __name__ == '__main__':
    print("Starting match score calculation...")
    process_unscored_jobs() 