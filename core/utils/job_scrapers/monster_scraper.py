"""
Monster job scraper implementation.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from core.utils.job_scrapers.base_scraper import BaseJobScraper
from core.utils.logging_utils import log_exceptions

logger = logging.getLogger(__name__)


class MonsterScraper(BaseJobScraper):
    """Scraper for Monster job listings."""

    def __init__(self):
        """Initialize the Monster scraper."""
        super().__init__(source_name="monster")

    def _build_search_url(self, query: str, location: str) -> str:
        """Build Monster search URL."""
        q = query.replace(" ", "-")
        l = location.replace(" ", "-")
        return f"https://www.monster.com/jobs/search?q={q}&where={l}"

    def _fetch_search_results(self, search_url: str, limit: int) -> Optional[BeautifulSoup]:
        """Fetch search results from Monster."""
        response = self._make_request(search_url)
        if not response:
            return None
        return self._get_soup(response)

    def _parse_search_results(
        self, soup: Optional[BeautifulSoup], limit: int
    ) -> List[Dict[str, Any]]:
        """Parse Monster search results."""
        if not soup:
            return []

        job_cards = soup.select(".results-card")
        results = []

        for card in job_cards[:limit]:
            try:
                # Extract job info
                job_title_elem = card.select_one(".title")
                job_title = job_title_elem.text.strip() if job_title_elem else "Unknown Title"

                company_elem = card.select_one(".company")
                company = company_elem.text.strip() if company_elem else "Unknown Company"

                location_elem = card.select_one(".location")
                location = location_elem.text.strip() if location_elem else ""

                link_elem = card.select_one("a.job-cardstyle__JobCardTitle-sc-1mbmxes-2")
                if link_elem and "href" in link_elem.attrs:
                    job_link = link_elem["href"]
                else:
                    job_link = ""

                posted_elem = card.select_one(".posted-date")
                posted_text = posted_elem.text.strip() if posted_elem else ""
                posted_date = self._parse_date(posted_text)

                # Get job ID from URL
                job_id = ""
                if job_link:
                    job_id_match = re.search(r"/job/([^/]+)", job_link)
                    if job_id_match:
                        job_id = job_id_match.group(1)

                results.append(
                    {
                        "title": job_title,
                        "company": company,
                        "location": location,
                        "source_url": job_link,
                        "posted_date": posted_date,
                        "source": "monster",
                        "job_id": job_id,
                    }
                )
            except Exception as e:
                logger.error(f"Error parsing Monster job card: {str(e)}")
                continue

        return results

    def _parse_job_details(self, response: requests.Response) -> Dict[str, Any]:
        """Parse job details from Monster."""
        soup = self._get_soup(response)
        if not soup:
            return {}

        try:
            # Extract detailed job info
            job_title_elem = soup.select_one("h1.job-title")
            job_title = job_title_elem.text.strip() if job_title_elem else "Unknown Title"

            company_elem = soup.select_one(".company-name")
            company = company_elem.text.strip() if company_elem else "Unknown Company"

            location_elem = soup.select_one(".location")
            location = location_elem.text.strip() if location_elem else ""

            description_elem = soup.select_one(".job-description")
            description = description_elem.text.strip() if description_elem else ""

            # Extract salary info if available
            salary_elem = soup.select_one(".salary")
            salary = salary_elem.text.strip() if salary_elem else ""

            # Extract job type if available
            job_type_elem = soup.select_one(".job-type")
            job_type = job_type_elem.text.strip() if job_type_elem else ""

            return {
                "title": job_title,
                "company": company,
                "location": location,
                "description": description,
                "salary": salary,
                "job_type": job_type,
                "source": "monster",
                "source_url": response.url,
            }
        except Exception as e:
            logger.error(f"Error parsing Monster job details: {str(e)}")
            return {}

    def _parse_date(self, date_str: str) -> datetime:
        """Parse Monster date format."""
        if not date_str:
            return timezone.now().date()

        today = timezone.now().date()

        # Handle 'Just posted', 'Today', etc.
        if "just posted" in date_str.lower() or "today" in date_str.lower():
            return today

        # Handle 'Posted 3 days ago', etc.
        days_match = re.search(r"(\d+)\s+days?\s+ago", date_str.lower())
        if days_match:
            days = int(days_match.group(1))
            return today - timedelta(days=days)

        # Handle 'Posted 3 hours ago', etc.
        hours_match = re.search(r"(\d+)\s+hours?\s+ago", date_str.lower())
        if hours_match:
            return today

        # Default to today if can't parse
        return today
