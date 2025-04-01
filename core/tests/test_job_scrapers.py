import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
from core.utils.job_scrapers.linkedin_scraper import LinkedInJobScraper
from core.utils.job_scrapers.indeed_scraper import IndeedJobScraper
from core.utils.job_scrapers.glassdoor_scraper import GlassdoorJobScraper
from core.utils.job_scrapers.monster_scraper import MonsterJobScraper
from core.utils.job_scrapers.jobbank_scraper import JobBankScraper

class TestJobScrapers(unittest.TestCase):
    def setUp(self):
        self.test_role = "Software Engineer"
        self.test_location = "New York, NY"
        
        # Sample HTML responses for each platform
        self.linkedin_html = """
        <div class="job-card-container">
            <h3 class="base-search-card__title">Software Engineer</h3>
            <h4 class="base-search-card__subtitle">Google</h4>
            <div class="base-search-card__metadata">New York, NY</div>
            <div class="base-search-card__description">Looking for a software engineer...</div>
            <a href="/jobs/view/123">View Job</a>
        </div>
        """
        
        self.indeed_html = """
        <div class="job_seen_beacon">
            <h2 class="jobTitle">Software Engineer</h2>
            <span class="companyName">Google</span>
            <div class="companyLocation">New York, NY</div>
            <div class="job-snippet">Looking for a software engineer...</div>
            <a href="/viewjob?jk=123">View Job</a>
        </div>
        """
        
        self.glassdoor_html = """
        <li class="react-job-listing">
            <div class="job-title">Software Engineer</div>
            <div class="employer-name">Google</div>
            <div class="location">New York, NY</div>
            <div class="job-description">Looking for a software engineer...</div>
            <a href="/job-listing/123">View Job</a>
        </li>
        """
        
        self.monster_html = """
        <div class="job-search-card">
            <h2 class="title">Software Engineer</h2>
            <div class="company">Google</div>
            <div class="location">New York, NY</div>
            <div class="description">Looking for a software engineer...</div>
            <a href="/jobs/123">View Job</a>
        </div>
        """
        
        self.jobbank_html = """
        <article class="resultJobItem">
            <span class="noctitle">Software Engineer</span>
            <span class="business">Google</span>
            <span class="location">New York, NY</span>
            <div class="result-description">Looking for a software engineer...</div>
            <a href="/job/123">View Job</a>
        </article>
        """

    @patch('requests.get')
    def test_linkedin_scraper(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = self.linkedin_html
        mock_get.return_value = mock_response
        
        # Test scraper
        scraper = LinkedInJobScraper()
        jobs = scraper.search_jobs(self.test_role, self.test_location)
        
        # Assertions
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['title'], 'Software Engineer')
        self.assertEqual(jobs[0]['company'], 'Google')
        self.assertEqual(jobs[0]['location'], 'New York, NY')
        self.assertTrue('Looking for a software engineer' in jobs[0]['description'])

    @patch('requests.get')
    def test_indeed_scraper(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = self.indeed_html
        mock_get.return_value = mock_response
        
        # Test scraper
        scraper = IndeedJobScraper()
        jobs = scraper.search_jobs(self.test_role, self.test_location)
        
        # Assertions
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['title'], 'Software Engineer')
        self.assertEqual(jobs[0]['company'], 'Google')
        self.assertEqual(jobs[0]['location'], 'New York, NY')
        self.assertTrue('Looking for a software engineer' in jobs[0]['description'])

    @patch('requests.get')
    def test_glassdoor_scraper(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = self.glassdoor_html
        mock_get.return_value = mock_response
        
        # Test scraper
        scraper = GlassdoorJobScraper()
        jobs = scraper.search_jobs(self.test_role, self.test_location)
        
        # Assertions
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['title'], 'Software Engineer')
        self.assertEqual(jobs[0]['company'], 'Google')
        self.assertEqual(jobs[0]['location'], 'New York, NY')
        self.assertTrue('Looking for a software engineer' in jobs[0]['description'])

    @patch('requests.get')
    def test_monster_scraper(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = self.monster_html
        mock_get.return_value = mock_response
        
        # Test scraper
        scraper = MonsterJobScraper()
        jobs = scraper.search_jobs(self.test_role, self.test_location)
        
        # Assertions
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['title'], 'Software Engineer')
        self.assertEqual(jobs[0]['company'], 'Google')
        self.assertEqual(jobs[0]['location'], 'New York, NY')
        self.assertTrue('Looking for a software engineer' in jobs[0]['description'])

    @patch('requests.get')
    def test_jobbank_scraper(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = self.jobbank_html
        mock_get.return_value = mock_response
        
        # Test scraper
        scraper = JobBankScraper()
        jobs = scraper.search_jobs(self.test_role, self.test_location)
        
        # Assertions
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['title'], 'Software Engineer')
        self.assertEqual(jobs[0]['company'], 'Google')
        self.assertEqual(jobs[0]['location'], 'New York, NY')
        self.assertTrue('Looking for a software engineer' in jobs[0]['description'])

    def test_scraper_error_handling(self):
        """Test error handling for all scrapers"""
        scrapers = [
            LinkedInJobScraper(),
            IndeedJobScraper(),
            GlassdoorJobScraper(),
            MonsterJobScraper(),
            JobBankScraper()
        ]
        
        for scraper in scrapers:
            with patch('requests.get') as mock_get:
                # Simulate a network error
                mock_get.side_effect = Exception("Network error")
                
                # Test that scraper handles error gracefully
                jobs = scraper.search_jobs(self.test_role, self.test_location)
                self.assertEqual(jobs, [])

if __name__ == '__main__':
    unittest.main() 