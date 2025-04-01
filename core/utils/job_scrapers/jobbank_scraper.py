import logging
import time
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class JobBankScraper:
    """Scraper for JobBank job listings"""
    
    def __init__(self):
        self.base_url = "https://www.jobbank.gc.ca"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def search_jobs(self, role: str, location: str) -> List[Dict]:
        """
        Search for jobs on JobBank with pagination support
        
        Args:
            role (str): Job title/role to search for
            location (str): Location to search in
            
        Returns:
            List[Dict]: List of job listings
        """
        try:
            jobs = []
            page = 1
            has_more = True
            
            while has_more:
                # Format search URL with page parameter
                search_url = f"{self.base_url}/jobsearch/jobsearch?searchstring={role}&locationstring={location}&page={page}"
                
                # Make request
                response = requests.get(search_url, headers=self.headers)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find job listings
                job_cards = soup.find_all('article', class_='resultJobItem')
                
                if not job_cards:
                    break
                
                for card in job_cards:
                    try:
                        # Extract job details
                        title = card.find('span', class_='noctitle').text.strip()
                        company = card.find('li', class_='business').text.strip()
                        location = card.find('li', class_='location').text.strip()
                        description = card.find('div', class_='resultJobItemDesc').text.strip()
                        
                        # Get job URL
                        job_url = card.find('a', class_='resultJobItem')['href']
                        if not job_url.startswith('http'):
                            job_url = self.base_url + job_url
                        
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': location,
                            'description': description,
                            'source_url': job_url,
                            'source': 'jobbank',
                            'posted_date': None  # JobBank doesn't show posted date in search results
                        })
                    except Exception as e:
                        logger.error(f"Error parsing job card: {str(e)}")
                        continue
                
                # Check for "Show more results" button
                show_more = soup.find('button', {'id': 'moreresultbutton'})
                has_more = bool(show_more)
                
                if has_more:
                    page += 1
                    time.sleep(1)  # Be nice to the server
                
            return jobs
            
        except Exception as e:
            logger.error(f"Error searching JobBank: {str(e)}")
            return []
