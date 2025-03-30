import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import urllib.parse
from core.utils.local_llms import OllamaClient
import json
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

class LinkedInJobScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.ollama_client = OllamaClient(model="phi4:latest", temperature=0.0)
        self.job_selectors = None

    def _get_link_selector_with_ai(self, html_content: str) -> str:
        """Use AI to find the correct CSS selector for job links"""
        prompt = f"""You are a LinkedIn job scraping expert. Your task is to find the CSS selector that will extract job posting URLs.

IMPORTANT: Return ONLY a JSON object with the link selector. No other text or explanations.

Example response:
{{
    "link_selector": "a.job-card-container__link"
}}

HTML Content:
{html_content}

Return ONLY this exact JSON structure:
{{
    "link_selector": "CSS selector here"
}}

Rules:
1. Return ONLY the JSON object, no other text
2. The selector must target <a> tags that link to job postings
3. The href must contain '/jobs/view/'
4. Use the most specific CSS selector possible
5. Prefer class names over generic selectors
6. Avoid selectors that might match non-job links
7. If no specific selector is found, return the most reliable one"""
        
        try:
            response = self.ollama_client.generate(prompt, resp_in_json=True)
            # Clean the response to ensure it's valid JSON
            response = response.replace('```json', '').replace('```', '').strip()
            # Remove any text before the first {
            response = response[response.find('{'):]
            # Remove any text after the last }
            response = response[:response.rfind('}')+1]
            
            selectors = json.loads(response)
            
            if 'link_selector' not in selectors:
                raise ValueError("Missing link_selector key")
                
            return selectors['link_selector']
        except Exception as e:
            print(f"Error getting link selector from AI: {str(e)}")
            # Fallback to default selector
            return "a.base-card__full-link"

    def _get_job_selectors_with_ai(self, html_content: str) -> Dict[str, str]:
        """Use AI to find CSS selectors for job details"""
        prompt = f"""You are a LinkedIn job scraping expert. Your task is to find CSS selectors for job details.

IMPORTANT: Return ONLY a JSON object with the selectors. No other text or explanations.

Example response:
{{
    "title": "h1.job-details-jobs-unified-top-card__job-title",
    "company": "a.job-details-jobs-unified-top-card__company-name",
    "location": "span.job-details-jobs-unified-top-card__bullet",
    "description": "div.job-details-jobs-unified-top-card__job-insight",
    "requirements": "div.job-details-jobs-unified-top-card__job-insight",
    "posted_date": "span.job-details-jobs-unified-top-card__posted-date",
    "salary_range": "span.job-details-jobs-unified-top-card__job-insight",
    "job_type": "span.job-details-jobs-unified-top-card__job-insight",
    "experience_level": "span.job-details-jobs-unified-top-card__job-insight",
    "required_skills": "div.job-details-jobs-unified-top-card__job-insight",
    "preferred_skills": "div.job-details-jobs-unified-top-card__job-insight"
}}

HTML Content:
{html_content}

Return ONLY this exact JSON structure with the most specific and reliable CSS selectors:
{{
    "title": "CSS selector here",
    "company": "CSS selector here",
    "location": "CSS selector here",
    "description": "CSS selector here",
    "requirements": "CSS selector here",
    "posted_date": "CSS selector here",
    "salary_range": "CSS selector here",
    "job_type": "CSS selector here",
    "experience_level": "CSS selector here",
    "required_skills": "CSS selector here",
    "preferred_skills": "CSS selector here"
}}

Rules:
1. Return ONLY the JSON object, no other text
2. Use the most specific CSS selectors possible
3. Prefer class names over generic selectors
4. Each selector must target a single element
5. Selectors should be reliable and consistent
6. Include all required fields
7. If a specific selector isn't found, use the most reliable one available"""
        
        try:
            response = self.ollama_client.generate(prompt, resp_in_json=True)
            # Clean the response to ensure it's valid JSON
            response = response.replace('```json', '').replace('```', '').strip()
            # Remove any text before the first {
            response = response[response.find('{'):]
            # Remove any text after the last }
            response = response[:response.rfind('}')+1]
            
            selectors = json.loads(response)
            
            # Validate required keys
            required_keys = {
                "title", "company", "location", "description", "requirements",
                "posted_date", "salary_range", "job_type", "experience_level",
                "required_skills", "preferred_skills"
            }
            if not all(key in selectors for key in required_keys):
                raise ValueError("Missing required selector keys")
                
            return selectors
        except Exception as e:
            print(f"Error getting job selectors from AI: {str(e)}")
            # Fallback to default selectors
            return {
                "title": "h1.job-details-jobs-unified-top-card__job-title",
                "company": "a.job-details-jobs-unified-top-card__company-name",
                "location": "span.job-details-jobs-unified-top-card__bullet",
                "description": "div.job-details-jobs-unified-top-card__job-insight",
                "requirements": "div.job-details-jobs-unified-top-card__job-insight",
                "posted_date": "span.job-details-jobs-unified-top-card__posted-date",
                "salary_range": "span.job-details-jobs-unified-top-card__job-insight",
                "job_type": "span.job-details-jobs-unified-top-card__job-insight",
                "experience_level": "span.job-details-jobs-unified-top-card__job-insight",
                "required_skills": "div.job-details-jobs-unified-top-card__job-insight",
                "preferred_skills": "div.job-details-jobs-unified-top-card__job-insight"
            }

    async def _fetch_job_page(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetch a job page asynchronously"""
        try:
            async with session.get(url, headers=self.headers) as response:
                return await response.text()
        except Exception as e:
            print(f"Error fetching job page {url}: {str(e)}")
            return ""

    def _extract_job_details_with_ai(self, html_content: str) -> Dict[str, str]:
        """Extract job details using AI when BeautifulSoup fails"""
        try:
            # Clean the HTML content to remove scripts and styles
            soup = BeautifulSoup(html_content, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            text_content = soup.get_text(separator=' ', strip=True)
            print(text_content)
            # Create prompt for AI
            prompt = f"""You are a LinkedIn job description extraction expert. Extract ONLY the job description from this LinkedIn job posting.

IMPORTANT: Return ONLY a JSON object with the description field. No other text or explanations.

Required field:
- description: The complete job description including:
  * Job responsibilities
  * Required qualifications
  * Experience requirements
  * Skills needed
  * Any other relevant job details

Rules:
1. Return ONLY a JSON object, no other text
2. Extract the complete description text
3. Include all sections of the job posting
4. If no description is found, use an empty string
5. Do not add any explanations or notes
6. Do not include any other fields in the response

Job posting text:
{text_content}

Return ONLY this exact JSON structure:
{{
    "description": "Full job description..."
}}"""

            # Get AI response
            response = self.ollama_client.generate(prompt, resp_in_json=True)
            print(response)
            # Parse AI response
            try:
                job_data = json.loads(response)
                return {
                    'title': '',
                    'company': '',
                    'location': '',
                    'description': job_data.get('description', ''),
                    'requirements': '',
                    'posted_date': '',
                    'salary_range': '',
                    'job_type': '',
                    'experience_level': '',
                    'required_skills': '',
                    'preferred_skills': ''
                }
            except json.JSONDecodeError:
                print("Failed to parse AI response as JSON")
                return self._get_empty_job_data()
                
        except Exception as e:
            print(f"Error in AI extraction: {str(e)}")
            return self._get_empty_job_data()

    def _get_empty_job_data(self) -> Dict[str, str]:
        """Return empty job data structure"""
        return {
            'title': '',
            'company': '',
            'location': '',
            'description': '',
            'requirements': '',
            'posted_date': '',
            'salary_range': '',
            'job_type': '',
            'experience_level': '',
            'required_skills': '',
            'preferred_skills': ''
        }

    def _extract_job_details(self, html_content: str) -> Dict[str, str]:
        """Extract job details using fixed selectors"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract job details
            job_details = {}

            # Extract job title
            title = soup.find("h1")
            title = title.get_text(strip=True) if title else "N/A"

            # Extract company name
            company = soup.find("a", {"class": "topcard__org-name-link"})
            if not company:
                company = soup.find("span", {"class": "topcard__flavor"})
            company = company.get_text(strip=True) if company else "N/A"

            # Extract location
            location = soup.find("span", {"class": "topcard__flavor topcard__flavor--bullet"})
            location = location.get_text(strip=True) if location else "N/A"

            # Extract posted time
            posted_time = soup.find("span", {"class": "posted-time-ago__text"})
            posted_time = posted_time.get_text(strip=True) if posted_time else "N/A"

            # Extract job description
            description = soup.find("div", {"class": "show-more-less-html__markup"})
            description = description.get_text(strip=True) if description else "N/A"

            # If we couldn't extract essential details with BeautifulSoup, try AI
            # if not job_details['description']:
            #     print("BeautifulSoup extraction incomplete, trying AI extraction...")
            #     ai_job_details = self._extract_job_details_with_ai(html_content)
                
            #     # Only use AI results for missing fields
            #     for field in ['title', 'company', 'location', 'description']:
            #         if not job_details[field] and ai_job_details[field]:
            #             job_details[field] = ai_job_details[field]
            
            return job_details
            
        except Exception as e:
            print(f"Error extracting job details: {str(e)}")
            # Try AI extraction as fallback
            print("BeautifulSoup extraction failed, trying AI extraction...")
            return self._extract_job_details_with_ai(html_content)

    async def _process_job_url(self, session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        """Process a single job URL"""
        html_content = await self._fetch_job_page(session, url)
        if not html_content:
            # Return empty job data with source info
            return {
                'source_url': url,
                'source': 'linkedin',
                'title': "",
                'company': "",
                'location': "",
                'description': ""
            }
            
        job_data = self._extract_job_details(html_content)
        job_data['source_url'] = url
        job_data['source'] = 'linkedin'
        return job_data

    async def _process_job_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Process multiple job URLs in parallel"""
        async with aiohttp.ClientSession() as session:
            tasks = [self._process_job_url(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            # Filter out any None results
            return [job for job in results if job is not None]

    def search_jobs(self, role: str, location: str) -> List[Dict[str, Any]]:
        jobs = []
        try:
            encoded_role = urllib.parse.quote(role)
            encoded_location = urllib.parse.quote(location)
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_role}&location={encoded_location}&f_TPR=r86400&f_JT=F%2CP%2CC%2CI&f_WT=2&position=1&pageNum=0"
            
            response = requests.get(search_url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Fixed selector for job links
            link_selector = "a.base-card__full-link"
            
            # Find all job links
            job_links = soup.select(link_selector)
            job_urls = []
            
            for link in job_links:
                try:
                    job_url = link['href']
                    if '/jobs/view/' in job_url:  # Ensure it's a job posting link
                        job_urls.append(job_url)
                        print(f"Found job link: {job_url}")
                except Exception as e:
                    print(f"Error extracting job link: {str(e)}")
                    continue

            if job_urls:
                # Process all job URLs in parallel
                jobs = asyncio.run(self._process_job_urls(job_urls))
            
            return jobs
        except Exception as e:
            print(f"Error during job search: {str(e)}")
            return jobs

    def close(self):
        """Empty method to maintain compatibility with search agent"""
        pass 