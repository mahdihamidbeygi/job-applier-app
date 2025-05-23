import json
from unittest.mock import patch, MagicMock, call

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import UserProfile, JobListing
from core.utils.agents.search_agent import SearchAgent


class SearchAgentTests(TestCase):
    def setUp(self):
        # Create a user and profile for context
        self.user = User.objects.create_user(
            username="testuser2", password="password123", email="test2@example.com"
        )
        self.user_profile, created = UserProfile.objects.get_or_create(
            user=self.user, defaults={"name": "Test User1"}
        )

        # Instantiate the SearchAgent
        self.search_agent = SearchAgent(user_id=self.user.id)

        # For creating mock Django HTTP requests
        self.factory = RequestFactory()

        # Mock components that are instance attributes of SearchAgent or its BaseAgent
        # These are typically initialized within SearchAgent or BaseAgent's __init__
        self.search_agent.llm = MagicMock()
        self.search_agent.personal_agent = MagicMock()
        self.search_agent.knowledge_base = MagicMock()

        # Scrapers are also instantiated by SearchAgent.
        # For testing search_jobs, we'll patch the scraper classes' methods directly.
        # If other SearchAgent methods were to call other specific methods on scraper instances,
        # we might mock them like: self.search_agent.linkedin_scraper = MagicMock()

    @patch("core.utils.job_scrapers.linkedin_scraper.LinkedInJobScraper.search_jobs")
    @patch("core.utils.job_scrapers.indeed_scraper.IndeedScraper.search_jobs")
    @patch("core.utils.job_scrapers.glassdoor_scraper.GlassdoorScraper.search_jobs")
    @patch("core.utils.job_scrapers.monster_scraper.MonsterScraper.search_jobs")
    @patch("core.utils.job_scrapers.jobbank_scraper.JobBankScraper.search_jobs")
    def test_search_jobs_calls_correct_scraper(
        self,
        mock_jobbank_search,
        mock_monster_search,
        mock_glassdoor_search,
        mock_indeed_search,
        mock_linkedin_search,
    ):
        mock_request = self.factory.get("/")  # Dummy request, e.g., for LinkedIn
        mock_request.user = self.user

        # Test LinkedIn
        expected_linkedin_jobs = [{"title": "LinkedIn Developer", "company": "LI Corp"}]
        mock_linkedin_search.return_value = expected_linkedin_jobs
        result = self.search_agent.search_jobs(
            "developer", "San Francisco", "linkedin", request=mock_request
        )
        mock_linkedin_search.assert_called_once_with(
            "developer", "San Francisco", request=mock_request
        )
        self.assertEqual(result, expected_linkedin_jobs)

        # Test Indeed
        expected_indeed_jobs = [{"title": "Indeed Analyst", "company": "Indeed LLC"}]
        mock_indeed_search.return_value = expected_indeed_jobs
        result = self.search_agent.search_jobs("analyst", "New York", "indeed")
        mock_indeed_search.assert_called_once_with("analyst", "New York")
        self.assertEqual(result, expected_indeed_jobs)

        # Test Glassdoor
        expected_glassdoor_jobs = [{"title": "Glassdoor PM", "company": "GD Inc."}]
        mock_glassdoor_search.return_value = expected_glassdoor_jobs
        result = self.search_agent.search_jobs("product manager", "Remote", "glassdoor")
        mock_glassdoor_search.assert_called_once_with("product manager", "Remote")
        self.assertEqual(result, expected_glassdoor_jobs)

        # Test Monster
        expected_monster_jobs = [{"title": "Monster QA", "company": "Monster Co."}]
        mock_monster_search.return_value = expected_monster_jobs
        result = self.search_agent.search_jobs("qa engineer", "Austin", "monster")
        mock_monster_search.assert_called_once_with("qa engineer", "Austin")
        self.assertEqual(result, expected_monster_jobs)

        # Test JobBank
        expected_jobbank_jobs = [{"title": "JobBank Clerk", "company": "Gov Canada"}]
        mock_jobbank_search.return_value = expected_jobbank_jobs
        result = self.search_agent.search_jobs("clerk", "Ottawa", "jobbank")
        mock_jobbank_search.assert_called_once_with("clerk", "Ottawa")
        self.assertEqual(result, expected_jobbank_jobs)

        # Test unsupported platform
        with self.assertRaisesRegex(ValueError, "Unsupported platform: unknown_platform"):
            self.search_agent.search_jobs("role", "location", "unknown_platform")

    def test_process_jobs_creates_new_listings_and_skips_duplicates(self):
        source_platform = "test_platform_alpha"
        # Sample data from a scraper
        scraped_jobs_data = [
            {
                "title": "Alpha Job 1",
                "company": "Alpha Corp",
                "location": "Alpha City",
                "description": "Description Alpha 1",
                "source_url": "http://alpha1.com",
            },
            {
                "title": "Alpha Job 2",
                "company": "Beta LLC",
                "location": "Beta Town",
                "description": "Description Beta 2",
                "source_url": "http://beta2.com",
            },
            None,  # To ensure None values are handled gracefully
            {
                "title": "Existing Alpha Job",
                "company": "Gamma Inc",
                "location": "Gamma Ville",
                "description": "This description should NOT be used",
                "source_url": "http://gamma_new.com",
            },
        ]

        # Pre-populate an existing job that should be skipped
        JobListing.objects.create(
            title="Existing Alpha Job",
            company="Gamma Inc",
            location="Gamma Ville",
            source=source_platform,  # Same source
            description="Original Gamma Description",
            posted_date=timezone.now().date(),
        )
        self.assertEqual(JobListing.objects.count(), 1)

        processed_listings = self.search_agent.process_jobs(scraped_jobs_data, source_platform)

        # Expecting 2 new JobListing objects to be created and returned
        self.assertEqual(len(processed_listings), 2)
        # Total jobs in DB: 1 existing + 2 new
        self.assertEqual(JobListing.objects.count(), 3)

        # Verify Alpha Job 1
        job1 = JobListing.objects.get(title="Alpha Job 1", company="Alpha Corp")
        self.assertEqual(job1.location, "Alpha City")
        self.assertEqual(job1.description, "Description Alpha 1")
        self.assertEqual(job1.source_url, "http://alpha1.com")
        self.assertEqual(job1.source, source_platform)
        self.assertEqual(job1.posted_date, timezone.now().date())  # Should be set

        # Verify Alpha Job 2
        job2 = JobListing.objects.get(title="Alpha Job 2", company="Beta LLC")
        self.assertEqual(job2.location, "Beta Town")
        self.assertEqual(job2.description, "Description Beta 2")

        # Verify the existing job was not modified by _process_jobs
        existing_job_db = JobListing.objects.get(title="Existing Alpha Job", company="Gamma Inc")
        self.assertEqual(
            existing_job_db.description, "Original Gamma Description"
        )  # Description remains unchanged

        # Test with empty input
        processed_empty = self.search_agent.process_jobs([], "another_platform")
        self.assertEqual(len(processed_empty), 0)

    @patch("core.utils.agents.search_agent.SearchAgent.save_context")  # Mock instance method
    def test_analyze_job_fit_success(self, mock_save_context):
        job_posting_data = {
            "title": "Senior Python Developer",
            "company": "PySolutions",
            "location": "Remote",
            "description": "Seeking an expert Python developer...",
            "required_skills": ["Python", "API Design", "Docker"],
        }

        self.search_agent.personal_agent.get_background_str.return_value = (
            "10 years Python, strong API and Docker."
        )
        self.search_agent.knowledge_base.get_company_context.return_value = (
            "PySolutions is a leader in Python tools."
        )

        llm_response_payload = {  # This is what the LLM is expected to produce as per the prompt
            "match_score": 95,
            "key_matching_skills": ["Python", "API Design", "Docker"],
            "potential_gaps": ["Kubernetes"],
            "application_strategy": "Emphasize extensive Python experience and API portfolio.",
            "company_fit": "Excellent cultural and technical alignment.",
        }
        # The analyze_job_fit method expects the LLM to return a JSON string
        self.search_agent.llm.generate_text.return_value = json.dumps(llm_response_payload)

        expected_analysis_output = {  # This is how analyze_job_fit formats the LLM response
            "match_score": 95.0,
            "skills_match": {
                "matching": ["Python", "API Design", "Docker"],
                "missing": ["Kubernetes"],
            },
            "recommendations": ["Emphasize extensive Python experience and API portfolio."],
        }

        analysis_result = self.search_agent.analyze_job_fit(job_posting_data)

        self.assertEqual(analysis_result, expected_analysis_output)
        self.search_agent.personal_agent.get_background_str.assert_called_once()
        self.search_agent.knowledge_base.get_company_context.assert_called_once_with(
            job_posting_data["company"]
        )
        self.search_agent.llm.generate_text.assert_called_once()

        # Optionally, check parts of the prompt sent to LLM
        prompt_arg = self.search_agent.llm.generate_text.call_args[0][0]
        self.assertIn(job_posting_data["description"], prompt_arg)
        self.assertIn("10 years Python, strong API and Docker.", prompt_arg)
        self.assertIn("PySolutions is a leader in Python tools.", prompt_arg)

        mock_save_context.assert_called_once_with(
            "Analyze job fit", json.dumps(expected_analysis_output)
        )

    @patch("core.utils.agents.search_agent.SearchAgent.save_context")
    def test_analyze_job_fit_llm_parse_error(self, mock_save_context):
        job_posting_data = {"description": "Another job", "company": "ParseError Co"}
        self.search_agent.personal_agent.get_background_str.return_value = "Some background"
        self.search_agent.knowledge_base.get_company_context.return_value = "Company context"
        self.search_agent.llm.generate_text.return_value = "This is definitely not JSON { malformed"

        expected_default_response = {
            "match_score": 50,  # Default from error handling
            "skills_match": {
                "matching": ["Unable to determine matching skills"],
                "missing": ["Unable to determine skill gaps"],
            },
            "recommendations": [
                "Consider reviewing the job description carefully and highlighting relevant experience in your application."
            ],
        }
        analysis_result = self.search_agent.analyze_job_fit(job_posting_data)
        self.assertEqual(analysis_result, expected_default_response)
        mock_save_context.assert_not_called()  # Not called on parse error before formatting

    @patch("core.utils.agents.search_agent.SearchAgent.save_context")
    def test_analyze_job_fit_llm_missing_fields(self, mock_save_context):
        job_posting_data = {
            "description": "Job with missing LLM fields",
            "company": "MissingFields Ltd",
        }
        self.search_agent.personal_agent.get_background_str.return_value = "Background info"
        self.search_agent.knowledge_base.get_company_context.return_value = (
            "Context for MissingFields Ltd"
        )

        llm_response_payload_missing = {
            "match_score": 60,
            "potential_gaps": ["Specific Tool X"],
        }  # Missing key_matching_skills
        self.search_agent.llm.generate_text.return_value = json.dumps(llm_response_payload_missing)

        expected_analysis_output = {
            "match_score": 60.0,
            "skills_match": {"matching": [], "missing": ["Specific Tool X"]},  # Defaulted matching
            "recommendations": [
                "Consider highlighting your relevant experience in your application."
            ],  # Defaulted
        }
        analysis_result = self.search_agent.analyze_job_fit(job_posting_data)
        self.assertEqual(analysis_result, expected_analysis_output)
        mock_save_context.assert_called_once_with(
            "Analyze job fit", json.dumps(expected_analysis_output)
        )

    @patch("core.utils.agents.search_agent.SearchAgent.save_context")
    def test_analyze_job_fit_outer_exception(self, mock_save_context):
        job_posting_data = {"description": "Job causing outer error", "company": "ErrorProne Corp"}
        self.search_agent.personal_agent.get_background_str.return_value = "User background"
        # Simulate an error during knowledge_base access
        self.search_agent.knowledge_base.get_company_context.side_effect = Exception(
            "Database connection failed"
        )

        expected_default_error_response = {
            "match_score": 0,
            "skills_match": {"matching": [], "missing": []},
            "recommendations": ["There was an error analyzing this job. Please try again later."],
        }
        analysis_result = self.search_agent.analyze_job_fit(job_posting_data)
        self.assertEqual(analysis_result, expected_default_error_response)
        self.search_agent.llm.generate_text.assert_not_called()  # LLM call should be skipped
        mock_save_context.assert_not_called()

    @patch("core.utils.agents.search_agent.SearchAgent.save_context")
    def test_suggest_job_search_strategy(self, mock_save_context):
        self.search_agent.personal_agent.get_background_str.return_value = (
            "Experienced marketing manager seeking new opportunities."
        )
        similar_jobs_mock = [
            {"title": "Senior Marketing Manager"},
            {"title": "Digital Marketing Lead"},
        ]
        self.search_agent.knowledge_base.search_similar_jobs.return_value = similar_jobs_mock

        llm_expected_response_payload = {
            "target_job_titles": ["Marketing Director", "Head of Marketing"],
            "industry_focus": ["Tech", "E-commerce"],
            "key_search_terms": ["strategic marketing", "brand management"],
            "recommended_job_boards": ["LinkedIn", "MarketingJobs.com"],
            "networking_strategy": "Attend industry webinars and connect with thought leaders.",
            "similar_jobs_analysis": "Similar roles emphasize leadership and digital transformation.",
        }
        # suggest_job_search_strategy returns the raw LLM response (which is a JSON string as per prompt)
        llm_response_str = json.dumps(llm_expected_response_payload)
        self.search_agent.llm.generate_text.return_value = llm_response_str

        result = self.search_agent.suggest_job_search_strategy()

        self.assertEqual(result, llm_response_str)
        self.search_agent.personal_agent.get_background_str.assert_called_once()
        self.search_agent.knowledge_base.search_similar_jobs.assert_called_once_with(
            "Experienced marketing manager seeking new opportunities."
        )
        self.search_agent.llm.generate_text.assert_called_once()
        prompt_arg = self.search_agent.llm.generate_text.call_args[0][0]
        self.assertIn("Experienced marketing manager seeking new opportunities.", prompt_arg)
        self.assertIn(str(similar_jobs_mock), prompt_arg)
        mock_save_context.assert_called_once_with("Suggest search strategy", llm_response_str)

    @patch("core.utils.agents.search_agent.SearchAgent.save_context")
    def test_refine_job_search(self, mock_save_context):
        search_results_input = [
            {"title": "Job A", "company": "Company X", "description": "Desc A"},
            {"title": "Job B", "company": "Company Y", "description": "Desc B"},
        ]
        self.search_agent.personal_agent.get_background_str.return_value = "Skilled data scientist."

        # Mock get_company_context for each company
        # self.search_agent.knowledge_base.get_company_context.side_effect = lambda company_name: f"Context for {company_name}"
        # Or more explicitly:
        def mock_company_context(company_name):
            if company_name == "Company X":
                return "Context for Company X"
            if company_name == "Company Y":
                return "Context for Company Y"
            return "Default context"

        self.search_agent.knowledge_base.get_company_context.side_effect = mock_company_context

        llm_expected_response_payload = {
            "ranked_jobs": [search_results_input[1], search_results_input[0]],  # Example ranking
            "fit_scores": [90, 75],
            "key_matches": ["Python", "Machine Learning"],
            "company_fit_analysis": "Company Y seems a better cultural fit.",
        }
        # refine_job_search also returns the raw LLM response (JSON string)
        llm_response_str = json.dumps(llm_expected_response_payload)
        self.search_agent.llm.generate_text.return_value = llm_response_str

        result = self.search_agent.refine_job_search(search_results_input)

        self.assertEqual(result, llm_response_str)
        self.search_agent.personal_agent.get_background_str.assert_called_once()

        # Check that get_company_context was called for each company in search_results_input
        expected_calls = [call("Company X"), call("Company Y")]
        self.search_agent.knowledge_base.get_company_context.assert_has_calls(
            expected_calls, any_order=True
        )

        self.search_agent.llm.generate_text.assert_called_once()
        prompt_arg = self.search_agent.llm.generate_text.call_args[0][0]
        self.assertIn(str(search_results_input), prompt_arg)
        self.assertIn("Skilled data scientist.", prompt_arg)
        self.assertIn("Context for Company X", prompt_arg)
        self.assertIn("Context for Company Y", prompt_arg)

        mock_save_context.assert_called_once_with("Refine search results", llm_response_str)
