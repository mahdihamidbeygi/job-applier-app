from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from typing import List, Dict
import logging
from django.conf import settings
from apps.jobs.schemas import JobCreate
from datetime import datetime

logger = logging.getLogger(__name__)

class JobScraper:
    def __init__(self):
        self.user_agent = settings.SCRAPING_SETTINGS['USER_AGENT']
        self.delay = settings.SCRAPING_SETTINGS['DELAY_BETWEEN_REQUESTS']

    async def scrape_jobs(self, search_terms: List[str], locations: List[str]) -> List[JobCreate]:
        """Scrape jobs from multiple sources based on search criteria."""
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            for term in search_terms:
                for location in locations:
                    # Scrape from different sources
                    indeed_jobs = await self._scrape_indeed(browser, term, location)
                    linkedin_jobs = await self._scrape_linkedin(browser, term, location)
                    
                    jobs.extend(indeed_jobs + linkedin_jobs)
                    await asyncio.sleep(self.delay)  # Rate limiting
            
            await browser.close()
        
        return jobs

    async def _scrape_indeed(self, browser, term: str, location: str) -> List[JobCreate]:
        """Scrape jobs from Indeed."""
        jobs = []
        try:
            page = await browser.new_page()
            await page.set_extra_http_headers({'User-Agent': self.user_agent})
            
            # Navigate to Indeed search results
            url = f"https://www.indeed.com/jobs?q={term}&l={location}"
            await page.goto(url)
            
            # Wait for job cards to load
            await page.wait_for_selector('.job_seen_beacon')
            
            # Extract job information
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            for job_card in soup.select('.job_seen_beacon'):
                job = self._parse_indeed_job(job_card)
                if job:
                    jobs.append(job)
            
            await page.close()
            
        except Exception as e:
            logger.error(f"Error scraping Indeed: {str(e)}")
        
        return jobs

    async def _scrape_linkedin(self, browser, term: str, location: str) -> List[JobCreate]:
        """Scrape jobs from LinkedIn."""
        jobs = []
        try:
            page = await browser.new_page()
            await page.set_extra_http_headers({'User-Agent': self.user_agent})
            
            # Navigate to LinkedIn job search
            url = f"https://www.linkedin.com/jobs/search/?keywords={term}&location={location}"
            await page.goto(url)
            
            # Wait for job cards to load
            await page.wait_for_selector('.job-card-container')
            
            # Extract job information
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            for job_card in soup.select('.job-card-container'):
                job = self._parse_linkedin_job(job_card)
                if job:
                    jobs.append(job)
            
            await page.close()
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {str(e)}")
        
        return jobs

    def _parse_indeed_job(self, job_card) -> JobCreate:
        """Parse Indeed job card HTML into structured data."""
        try:
            title = job_card.select_one('.jobTitle').text.strip()
            company = job_card.select_one('.companyName').text.strip()
            location = job_card.select_one('.companyLocation').text.strip()
            description = job_card.select_one('.job-snippet').text.strip()
            url = job_card.select_one('.jobTitle a')['href']
            
            return JobCreate(
                title=title,
                company=company,
                location=location,
                description=description,
                url=url,
                source='indeed',
                job_type='Full-time',  # Default value, can be updated later
                posted_date=datetime.now(),  # Indeed doesn't always show exact date
                status='active'
            )
        except Exception as e:
            logger.error(f"Error parsing Indeed job card: {str(e)}")
            return None

    def _parse_linkedin_job(self, job_card) -> JobCreate:
        """Parse LinkedIn job card HTML into structured data."""
        try:
            title = job_card.select_one('.base-search-card__title').text.strip()
            company = job_card.select_one('.base-search-card__subtitle').text.strip()
            location = job_card.select_one('.job-search-card__location').text.strip()
            description = job_card.select_one('.base-search-card__metadata').text.strip()
            url = job_card.select_one('.base-card__full-link')['href']
            
            return JobCreate(
                title=title,
                company=company,
                location=location,
                description=description,
                url=url,
                source='linkedin',
                job_type='Full-time',  # Default value, can be updated later
                posted_date=datetime.now(),  # LinkedIn doesn't always show exact date
                status='active'
            )
        except Exception as e:
            logger.error(f"Error parsing LinkedIn job card: {str(e)}")
            return None 