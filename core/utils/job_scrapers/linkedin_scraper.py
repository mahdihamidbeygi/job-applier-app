import asyncio
import json
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import aiohttp
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.models import JobListing
from core.utils.llm_clients import OllamaClient


class LinkedInJobScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.ollama_client = OllamaClient(model="phi4:latest", temperature=0.0)
        self.driver = None

    def setup_driver(self):
        if self.driver is not None:
            return self.driver

        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--enable-unsafe-webgl")
        chrome_options.add_argument("--enable-unsafe-swiftshader")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Initialize the Chrome WebDriver
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver

    def _extract_job_details(self, job_url: str) -> Dict[str, str]:
        """Extract job details using fixed selectors"""
        try:
            # Navigate to the URL
            self.driver.get(job_url)

            # 2. Handle Dynamic Content (Wait for elements to load)
            wait = WebDriverWait(self.driver, 5)

            # Wait for the job title to be present
            job_title_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.top-card-layout__title"))
            )
            job_title = job_title_element.text

            company_name_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.topcard__org-name-link"))
            )
            company_name = company_name_element.text

            location_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.topcard__flavor--bullet"))
            )
            location = location_element.text

            # Scroll down to load more content
            # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # time.sleep(2)

            try:
                # Try to find and click "Show more" button if it exists
                try:
                    show_more_button = wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "button.show-more-less-html__button")
                        )
                    )
                    self.driver.execute_script("arguments[0].click();", show_more_button)
                    time.sleep(1)
                except TimeoutException:
                    print("No 'Show more' button found")
                description_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.description__text"))
                )
                job_description = description_element.text
            except TimeoutException:
                job_description = "Description not found"

            return {
                "title": job_title,
                "company": company_name,
                "location": location,
                "description": job_description,
                "source_url": job_url,
                "source": "linkedin",
            }

        except Exception as e:
            print(f"Error extracting job details: {str(e)}")
            return None

    async def _process_job_url(self, session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        """Process a single job URL"""
        try:
            job_data = self._extract_job_details(job_url=url)
            if job_data:
                job_data["source_url"] = url
                job_data["source"] = "linkedin"
            return job_data
        except Exception as e:
            print(f"Error processing job URL {url}: {str(e)}")
            return None

    async def _process_job_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Process multiple job URLs in parallel with rate limiting"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in urls:
                tasks.append(self._process_job_url(session, url))
                await asyncio.sleep(1)  # Rate limiting between requests
            results = await asyncio.gather(*tasks)
            return [job for job in results if job is not None]

    def scrape_job_links(self) -> List[str]:
        """Scrape job links from the current page"""
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            job_cards = soup.find_all("div", class_="base-card")
            job_links = []
            for card in job_cards:
                link = card.find("a", class_="base-card__full-link")
                if link and link.get("href"):
                    job_links.append(link["href"])
            return job_links
        except Exception as e:
            print(f"Error scraping job links: {str(e)}")
            return []

    def scroll_down(self):
        """Scrolls to the bottom of the page and waits for dynamic content to load."""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  # Wait for content to load
        self.driver.execute_script("window.scrollTo(0, 0);")  # scroll back to the top
        time.sleep(1)

    def search_jobs(
        self, role: str, location: str, max_pages: int = 3, request=None
    ) -> List[Dict[str, Any]]:
        jobs = []
        urls_done = []
        try:
            self.setup_driver()
            encoded_role = urllib.parse.quote(role)
            encoded_location = urllib.parse.quote(location)
            # Remove filters to get more general results
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_role}&location={encoded_location}&position=1&pageNum=0"

            self.driver.get(search_url)
            time.sleep(3)  # Wait for initial load

            # Get hidden jobs from session if request is provided
            hidden_jobs = []
            if request:
                hidden_jobs = request.session.get("hidden_jobs", [])

            page = 0
            while page <= max_pages:
                job_links = self.scrape_job_links()

                # Scrape details for each job on this page
                for link in job_links:
                    if link in urls_done:
                        continue

                    job_details = self._extract_job_details(link)
                    if job_details:
                        # Check if we have tailored documents for this job
                        existing_job = JobListing.objects.filter(
                            title=job_details["title"],
                            company=job_details["company"],
                            location=job_details["location"],
                            source_url=job_details["source_url"],
                            description=job_details["description"],
                        ).first()

                        if existing_job:
                            # Skip if job is in hidden jobs list
                            if existing_job.id in hidden_jobs:
                                continue
                            job_details["has_tailored_documents"] = (
                                existing_job.has_tailored_documents
                            )
                            job_details["id"] = existing_job.id  # Add job ID for frontend
                        else:
                            job_details["has_tailored_documents"] = False
                            job_details["id"] = None

                        jobs.append(job_details)
                        urls_done.append(link)
                        time.sleep(2)  # Avoid overwhelming the server

                # Check if there's a next page
                try:
                    self.scroll_down()
                    page += 1
                except Exception as e:
                    print(f"Error navigating to next page: {str(e)}")
                    break

            return jobs
        except Exception as e:
            print(f"Error during job search: {str(e)}")
            return jobs
        finally:
            self.close()

    def close(self):
        """Properly close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error closing WebDriver: {str(e)}")
            finally:
                self.driver = None
