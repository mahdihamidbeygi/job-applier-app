import json
import logging
import time
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class GlassdoorScraper:
    """Scraper for Glassdoor job listings"""
    
    def __init__(self):
        self.base_url = "https://www.glassdoor.com"
        self.api_url = "https://www.glassdoor.com/api/v1/jobs/search"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def search_jobs(self, role: str, location: str) -> List[Dict]:
        """
        Search for jobs on Glassdoor with "Show more jobs" support
        
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
                # Prepare API request parameters
                params = {
                    'q': role,
                    'l': location,
                    'page': page,
                    'limit': 30,
                    'sort': 'date',
                    'format': 'json'
                }
                
                # Make API request
                response = requests.get(
                    self.api_url,
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                
                # Parse JSON response
                data = response.json()
                
                # Extract job listings
                job_cards = data.get('jobs', [])
                
                if not job_cards:
                    break
                
                for card in job_cards:
                    try:
                        # Extract job details from JSON
                        title = card.get('title', '').strip()
                        company = card.get('company', '').strip()
                        location = card.get('location', '').strip()
                        description = card.get('description', '').strip()
                        
                        # Get job URL
                        job_url = card.get('url', '')
                        if not job_url.startswith('http'):
                            job_url = self.base_url + job_url
                        
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': location,
                            'description': description,
                            'source_url': job_url,
                            'source': 'glassdoor',
                            'posted_date': card.get('date')
                        })
                    except Exception as e:
                        logger.error(f"Error parsing job card: {str(e)}")
                        continue
                
                # Check if there are more results
                total_count = data.get('totalCount', 0)
                has_more = len(jobs) < total_count
                
                if has_more:
                    page += 1
                    time.sleep(1)  # Be nice to the server
                
            return jobs
            
        except Exception as e:
            logger.error(f"Error searching Glassdoor: {str(e)}")
            return []
