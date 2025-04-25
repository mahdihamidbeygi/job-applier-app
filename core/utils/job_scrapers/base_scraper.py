"""
Base job scraper class that provides common functionality for all job scrapers.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from core.utils.logging_utils import log_exceptions

logger = logging.getLogger(__name__)


class BaseJobScraper(ABC):
    """
    Base class for all job scrapers.

    This class provides common functionality for scraping job listings,
    including error handling, request handling, and data normalization.
    """

    def __init__(self, source_name: str):
        """
        Initialize the job scraper.

        Args:
            source_name: The name of the job source (e.g., 'linkedin', 'indeed')
        """
        self.source_name = source_name
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
        }

    @log_exceptions(level=logging.ERROR)
    def search_jobs(self, query: str, location: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for jobs with the given query and location.

        Args:
            query: The job search query (e.g., 'software engineer')
            location: The location to search in (e.g., 'San Francisco, CA')
            limit: Maximum number of jobs to return

        Returns:
            List of job listings
        """
        try:
            search_url = self._build_search_url(query, location)
            search_results = self._fetch_search_results(search_url, limit)
            return self._parse_search_results(search_results, limit)
        except Exception as e:
            logger.error(f"{self.source_name} scraper error in search_jobs: {str(e)}")
            return []

    @log_exceptions(level=logging.ERROR)
    def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific job.

        Args:
            job_url: The URL of the job listing

        Returns:
            Dictionary with job details
        """
        try:
            response = self._make_request(job_url)
            if not response:
                return {}

            return self._parse_job_details(response)
        except Exception as e:
            logger.error(f"{self.source_name} scraper error in get_job_details: {str(e)}")
            return {}

    def _make_request(self, url: str) -> Optional[requests.Response]:
        """
        Make an HTTP request with error handling.

        Args:
            url: The URL to request

        Returns:
            Response object or None if the request failed
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"{self.source_name} request error for {url}: {str(e)}")
            return None

    def _get_soup(self, response: requests.Response) -> Optional[BeautifulSoup]:
        """
        Parse HTML response into BeautifulSoup object.

        Args:
            response: HTTP response

        Returns:
            BeautifulSoup object or None if parsing failed
        """
        try:
            return BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            logger.error(f"{self.source_name} error parsing HTML: {str(e)}")
            return None

    def _normalize_date(self, date_str: str) -> datetime:
        """
        Convert various date formats to a consistent datetime object.

        Args:
            date_str: Date string in various formats

        Returns:
            Datetime object (defaults to today if parsing fails)
        """
        try:
            # Implementation depends on the specific format
            # This would be extended in derived classes
            return self._parse_date(date_str)
        except Exception as e:
            logger.error(f"{self.source_name} date parsing error: {str(e)}")
            return timezone.now().date()

    @abstractmethod
    def _build_search_url(self, query: str, location: str) -> str:
        """
        Build the search URL for the job source.

        Args:
            query: Job search query
            location: Location to search in

        Returns:
            Search URL
        """
        pass

    @abstractmethod
    def _fetch_search_results(self, search_url: str, limit: int) -> Any:
        """
        Fetch search results from the job source.

        Args:
            search_url: The search URL
            limit: Maximum number of results to fetch

        Returns:
            Raw search results (format depends on the job source)
        """
        pass

    @abstractmethod
    def _parse_search_results(self, search_results: Any, limit: int) -> List[Dict[str, Any]]:
        """
        Parse search results into a standard format.

        Args:
            search_results: Raw search results
            limit: Maximum number of results to return

        Returns:
            List of standardized job listings
        """
        pass

    @abstractmethod
    def _parse_job_details(self, response: requests.Response) -> Dict[str, Any]:
        """
        Parse job details from the response.

        Args:
            response: HTTP response for the job listing page

        Returns:
            Dictionary with job details
        """
        pass

    @abstractmethod
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse date string into a datetime object.

        Args:
            date_str: Date string in a format specific to the job source

        Returns:
            Datetime object
        """
        pass
