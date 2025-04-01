from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class GlassdoorJobScraper:
    def __init__(self):
        self.base_url = "https://www.glassdoor.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def search_jobs(self, role: str, location: str) -> List[Dict[str, str]]:
        """
        Search for jobs on Glassdoor
        
        Args:
            role (str): Job title or role to search for
            location (str): Location to search in
            
        Returns:
            List[Dict[str, str]]: List of job listings with title, company, location, description, and source_url
        """
        try:
            # Format the search URL
            search_url = f"{self.base_url}/Job/jobs.htm?sc.keyword={role}&locT=C&locId={location}"
            
            # Make the request
            response = requests.get(search_url, headers=self.headers)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all job cards
            job_cards = soup.find_all('li', class_='react-job-listing')
            
            jobs = []
            for card in job_cards:
                try:
                    # Extract job details
                    title_elem = card.find('div', class_='job-title')
                    company_elem = card.find('div', class_='employer-name')
                    location_elem = card.find('div', class_='location')
                    description_elem = card.find('div', class_='job-description')
                    link_elem = card.find('a', class_='job-link')
                    
                    if not all([title_elem, company_elem, location_elem, description_elem, link_elem]):
                        continue
                    
                    job = {
                        'title': title_elem.get_text(strip=True),
                        'company': company_elem.get_text(strip=True),
                        'location': location_elem.get_text(strip=True),
                        'description': description_elem.get_text(strip=True),
                        'source_url': self.base_url + link_elem['href'] if link_elem['href'].startswith('/') else link_elem['href']
                    }
                    
                    jobs.append(job)
                    
                except Exception as e:
                    logger.error(f"Error parsing job card: {str(e)}")
                    continue
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error searching Glassdoor jobs: {str(e)}")
            return [] 