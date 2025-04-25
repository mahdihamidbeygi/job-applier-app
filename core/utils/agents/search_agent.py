import logging
from typing import Any, Dict, List

from django.utils import timezone

from core.models import JobListing
from core.tasks import generate_documents_async
from core.utils.agents.base_agent import BaseAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.job_scrapers.glassdoor_scraper import GlassdoorScraper
from core.utils.job_scrapers.indeed_scraper import IndeedScraper
from core.utils.job_scrapers.jobbank_scraper import JobBankScraper
from core.utils.job_scrapers.linkedin_scraper import LinkedInJobScraper
from core.utils.job_scrapers.monster_scraper import MonsterScraper
from core.utils.rag.job_knowledge import JobKnowledgeBase

logger = logging.getLogger(__name__)


class SearchAgent(BaseAgent):
    def __init__(self, user_id: int, personal_agent: PersonalAgent):
        super().__init__(user_id)
        self.personal_agent: PersonalAgent = personal_agent
        self.knowledge_base: JobKnowledgeBase = JobKnowledgeBase()
        self.linkedin_scraper = LinkedInJobScraper()
        self.indeed_scraper = IndeedScraper()
        self.glassdoor_scraper = GlassdoorScraper()
        self.monster_scraper = MonsterScraper()
        self.jobbank_scraper = JobBankScraper()

    def search_jobs(
        self, role: str, location: str, platform: str = "linkedin", request=None
    ) -> List[Dict]:
        """
        Search for jobs on the specified platform

        Args:
            role: Job title or role to search for
            location: Location to search in
            platform: Platform to search on (linkedin, indeed, glassdoor, monster, jobbank)
            request: Django request object for session access

        Returns:
            List of job listings
        """
        platform = platform.lower()

        if platform == "linkedin":
            return self.linkedin_scraper.search_jobs(role, location, request=request)
        elif platform == "indeed":
            return self.indeed_scraper.search_jobs(role, location)
        elif platform == "glassdoor":
            return self.glassdoor_scraper.search_jobs(role, location)
        elif platform == "monster":
            return self.monster_scraper.search_jobs(role, location)
        elif platform == "jobbank":
            return self.jobbank_scraper.search_jobs(role, location)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

    def _process_jobs(self, jobs: List[Dict[str, str]], source: str) -> List[JobListing]:
        """Process jobs from a specific source and create JobListing objects"""
        job_listings = []
        for job in jobs:
            if job:  # Skip None results
                # Check for existing job with same title, company, and location
                existing_job = JobListing.objects.filter(
                    title=job.get("title", ""),
                    company=job.get("company", ""),
                    location=job.get("location", ""),
                    source=source,
                ).first()

                if not existing_job:
                    job_listing = JobListing.objects.create(
                        title=job.get("title", ""),
                        company=job.get("company", ""),
                        location=job.get("location", ""),
                        description=job.get("description", ""),
                        source_url=job.get("source_url", ""),
                        source=source,
                        posted_date=timezone.now().date(),
                    )

                    job_listings.append(job_listing)

                    # Trigger background document generation
                    generate_documents_async.delay(job_listing.id, self.user_id)

        return job_listings

    def analyze_job_fit(self, job_posting: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes job posting for fit with personal background"""
        try:
            # Get company context from knowledge base
            company_context = self.knowledge_base.get_company_context(
                job_posting.get("company", "")
            )

            prompt = f"""
            As a job search specialist, analyze this job posting for fit with the candidate's background:
            
            Job Posting:
            {job_posting.get('description', '')}
            
            Company Context:
            {company_context}
            
            Required Skills:
            {', '.join(job_posting.get('required_skills', []))}
            
            Candidate Background Summary:
            {self.personal_agent.get_background_str()}
            
            Provide a response in JSON format with the following structure:
            {{
                "match_score": 0-100,
                "key_matching_skills": ["skill1", "skill2", ...],
                "potential_gaps": ["skill1", "skill2", ...],
                "application_strategy": "string with recommended approach",
                "company_fit": "analysis of company culture fit"
            }}
            
            RULES:
            - DO NOT INCLUDE ANY EXTRA TEXT, NUMBERS, OR EXPLANATION OUTSIDE THE JSON OBJECT
            - Return valid JSON only
            - Use simple structure with clear fields
            - Ensure match_score is a NUMBER between 0-100 (not a string)
            """

            response = self.llm.generate_text(prompt)

            try:
                # Handle case where response is not already in JSON format
                if isinstance(response, str):
                    import json

                    json_response = json.loads(response)
                else:
                    json_response = response

                # Ensure required fields are present
                required_fields = ["match_score", "key_matching_skills", "potential_gaps"]
                for field in required_fields:
                    if field not in json_response:
                        json_response[field] = [] if field != "match_score" else 0

                # Format response for the frontend
                formatted_response = {
                    "match_score": float(json_response.get("match_score", 0)),
                    "skills_match": {
                        "matching": json_response.get("key_matching_skills", []),
                        "missing": json_response.get("potential_gaps", []),
                    },
                    "recommendations": [
                        json_response.get(
                            "application_strategy",
                            "Consider highlighting your relevant experience in your application.",
                        )
                    ],
                }

                self.save_context("Analyze job fit", json.dumps(formatted_response))
                return formatted_response

            except Exception as e:
                print(f"Error parsing job analysis response: {str(e)}")
                print(f"Raw response: {response}")
                # Return a default response
                return {
                    "match_score": 50,
                    "skills_match": {
                        "matching": ["Unable to determine matching skills"],
                        "missing": ["Unable to determine skill gaps"],
                    },
                    "recommendations": [
                        "Consider reviewing the job description carefully and highlighting relevant experience in your application."
                    ],
                }
        except Exception as e:
            print(f"Error in analyze_job_fit: {str(e)}")
            # Return a default response
            return {
                "match_score": 0,
                "skills_match": {"matching": [], "missing": []},
                "recommendations": [
                    "There was an error analyzing this job. Please try again later."
                ],
            }

    def suggest_job_search_strategy(self) -> Dict[str, Any]:
        """Suggests personalized job search strategy"""
        # Get similar jobs from knowledge base
        similar_jobs = self.knowledge_base.search_similar_jobs(
            self.personal_agent.get_background_str()
        )

        prompt = f"""
        Based on the candidate's background:
        {self.personal_agent.get_background_str()}
        
        Similar Jobs Found:
        {similar_jobs}
        
        Suggest a JSON response with:
        1. target_job_titles: list of suitable job titles
        2. industry_focus: list of relevant industries
        3. key_search_terms: list of search keywords
        4. recommended_job_boards: list of job sites
        5. networking_strategy: string with networking tips
        6. similar_jobs_analysis: insights from similar job postings
        """

        response = self.llm.generate_text(prompt)
        self.save_context("Suggest search strategy", response)
        return response

    def refine_job_search(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Refines job search results based on candidate's background"""
        # Get company contexts for all jobs
        company_contexts = {
            job["company"]: self.knowledge_base.get_company_context(job["company"])
            for job in search_results
        }

        prompt = f"""
        Analyze these job search results and rank them by fit:
        
        Search Results:
        {search_results}
        
        Company Contexts:
        {company_contexts}
        
        Candidate Background:
        {self.personal_agent.get_background_str()}
        
        Provide a JSON response with:
        1. ranked_jobs: list of jobs sorted by fit
        2. fit_scores: list of match percentages
        3. key_matches: list of matching criteria
        4. company_fit_analysis: analysis of company culture fit
        """

        response = self.llm.generate_text(prompt)
        self.save_context("Refine search results", response)
        return response
