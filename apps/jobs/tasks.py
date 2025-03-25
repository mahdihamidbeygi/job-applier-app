from celery import shared_task
from django.conf import settings
from services.scraping.job_scraper import JobScraper
from .models import Job, JobSearch
from .schemas import JobCreate
import asyncio
import logging

logger = logging.getLogger(__name__)

@shared_task
def scrape_jobs_for_search(search_id: int):
    """Scrape jobs for a specific search."""
    try:
        search = JobSearch.objects.get(id=search_id)
        scraper = JobScraper()
        
        # Run async scraping
        jobs = asyncio.run(scraper.scrape_jobs(
            search_terms=[search.keywords],
            locations=[search.location]
        ))
        
        # Save jobs to database
        for job_data in jobs:
            if isinstance(job_data, JobCreate):
                Job.objects.create(
                    title=job_data.title,
                    company=job_data.company,
                    description=job_data.description,
                    location=job_data.location,
                    url=str(job_data.url),  # Convert HttpUrl to string
                    source=job_data.source,
                    job_type=job_data.job_type,
                    posted_date=job_data.posted_date,
                    status=job_data.status
                )
        
        return f"Scraped {len(jobs)} jobs for search {search_id}"
    
    except JobSearch.DoesNotExist:
        logger.error(f"Job search {search_id} not found")
        return "Search not found"
    except Exception as e:
        logger.error(f"Error scraping jobs: {str(e)}")
        return f"Error: {str(e)}"

@shared_task
def scrape_all_active_searches():
    """Scrape jobs for all active searches."""
    active_searches = JobSearch.objects.filter(is_active=True)
    
    for search in active_searches:
        scrape_jobs_for_search.delay(search.id)
    
    return f"Triggered scraping for {active_searches.count()} active searches"

@shared_task
def clean_old_jobs():
    """Clean up old job listings."""
    from django.utils import timezone
    from datetime import timedelta
    
    # Remove jobs older than 30 days
    cutoff_date = timezone.now() - timedelta(days=30)
    old_jobs = Job.objects.filter(
        scraped_date__lt=cutoff_date,
        status='active'
    )
    
    count = old_jobs.count()
    old_jobs.update(status='expired')
    
    return f"Marked {count} old jobs as expired" 