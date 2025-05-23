from io import BytesIO
import logging
from typing import Any, Dict, List

from django.utils import timezone
from django.conf import settings

from core.models import JobListing
from core.utils.agents.base_agent import BaseAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.agents.writer_agent import WriterAgent
from core.utils.agents.job_agent import JobAgent
from core.utils.job_scrapers.glassdoor_scraper import GlassdoorScraper
from core.utils.job_scrapers.indeed_scraper import IndeedScraper
from core.utils.job_scrapers.jobbank_scraper import JobBankScraper
from core.utils.job_scrapers.linkedin_scraper import LinkedInJobScraper
from core.utils.job_scrapers.monster_scraper import MonsterScraper
from core.utils.rag.job_knowledge import JobKnowledgeBase

logger = logging.getLogger(__name__)

# --- Celery Task Import ---
generate_resume_for_job_task_imported = False
generate_resume_task_func = None
try:
    from core.tasks import generate_resume_for_job_task as _task_func

    generate_resume_task_func = _task_func
    generate_resume_for_job_task_imported = True
    logger.info("Successfully imported 'generate_resume_for_job_task'.")
except ImportError:
    logger.warning(
        "Celery task 'generate_resume_for_job_task' could not be imported. Resume generation will be synchronous if Celery is enabled."
    )
# --- End Celery Task Import ---


class SearchAgent(BaseAgent):
    def __init__(self, user_id: int):
        super().__init__(user_id)
        self.personal_agent: PersonalAgent = PersonalAgent(user_id=user_id)
        self.knowledge_base: JobKnowledgeBase = JobKnowledgeBase()
        self.linkedin_scraper = LinkedInJobScraper()
        self.indeed_scraper = IndeedScraper()
        self.glassdoor_scraper = GlassdoorScraper()
        self.monster_scraper = MonsterScraper()
        self.jobbank_scraper = JobBankScraper()

        # Determine if Celery is configured for resume generation
        self.celery_enabled_for_resumes = (
            getattr(settings, "USE_CELERY_FOR_RESUMES", False)
            and getattr(settings, "CELERY_BROKER_URL", None) is not None
        )

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

    def _generate_resume_synchronously(self, job_listing_id: int):
        """Helper method for synchronous resume generation."""
        logger.info(
            f"Generating resume synchronously for job_listing_id: {job_listing_id}, user_id: {self.user_id}"
        )
        try:
            # First verify the job listing exists
            try:
                job_listing = JobListing.objects.get(id=job_listing_id)
            except JobListing.DoesNotExist:
                logger.error(f"JobListing with ID {job_listing_id} not found.")
                return

            # Create JobAgent without user_id filter (since JobListing doesn't have user_id)
            job_agent = JobAgent(user_id=self.user_id, job_id=job_listing_id)
            writer_agent = WriterAgent(
                user_id=self.user_id,
                personal_agent=self.personal_agent,
                job_agent=job_agent,
            )
            # Generate resume
            writer_agent.generate_resume()
            logger.info(
                f"Synchronous resume generation completed for job_listing_id: {job_listing_id}"
            )
        except Exception as e:
            logger.error(
                f"Error during synchronous resume generation for job_listing_id: {job_listing_id}. Error: {e}",
                exc_info=True,
            )

    def process_jobs(self, jobs_data: List[Dict[str, str]]) -> List[JobListing]:
        """
        Process jobs from a specific source, create JobListing objects,
        and queue resume generation if needed.
        """
        processed_new_job_listings = []

        for job_data in jobs_data:
            if not job_data:  # Skip None or empty job data
                logger.debug("Skipping empty job data.")
                continue

            # Clean and validate job data
            title = job_data.get("title", "").strip()
            company = job_data.get("company", "").strip()
            location = job_data.get("location", "").strip()

            if not title or not company:
                logger.warning(f"Skipping job with missing title or company: {job_data}")
                continue

            try:
                job_listing, created = JobListing.objects.get_or_create(
                    user_id=self.user_id,
                    title=title,
                    company=company,
                    location=location,
                    description=job_data.get("description", ""),
                )

                if created:
                    logger.info(
                        f"Created new JobListing: {job_listing.id} - {job_listing.title} at {job_listing.company}"
                    )
                    processed_new_job_listings.append(job_listing)

                    # Generate resume for new job listings
                    self._queue_resume_generation(job_listing)

                else:
                    logger.info(
                        f"Found existing JobListing: {job_listing.id} - {job_listing.title} at {job_listing.company}"
                    )

                    # Check if existing job needs resume generation
                    if not bool(job_listing.tailored_resume):
                        logger.info(
                            f"Existing JobListing {job_listing.id} needs a tailored resume."
                        )
                        self._queue_resume_generation(job_listing)

            except Exception as e:
                logger.error(f"Error processing job data {job_data}: {str(e)}", exc_info=True)
                continue

        return processed_new_job_listings

    def _queue_resume_generation(self, job_listing: JobListing):
        """Helper method to queue resume generation for a job listing."""
        try:
            if (
                self.celery_enabled_for_resumes
                and generate_resume_for_job_task_imported
                and generate_resume_task_func
            ):
                try:
                    generate_resume_task_func.delay(self.user_id, job_listing.id)
                    logger.info(
                        f"Queued resume generation via Celery for job_listing_id: {job_listing.id}, user_id: {self.user_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to queue Celery task for job_listing_id: {job_listing.id}. Error: {e}. Falling back to synchronous."
                    )
                    self._generate_resume_synchronously(job_listing.id)
            else:
                logger.info("Celery not used for resume generation. Generating synchronously.")
                self._generate_resume_synchronously(job_listing.id)
        except Exception as e:
            logger.error(
                f"Error queueing resume generation for job_listing_id: {job_listing.id}. Error: {e}",
                exc_info=True,
            )

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
            {self.personal_agent.get_formatted_background()}
            
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

            response: str = self.llm.generate_text(prompt)

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
                logger.error(f"Error parsing job analysis response: {str(e)}")
                logger.debug(f"Raw response: {response}")
                # Return a default response
                return {
                    "match_score": 0,
                    "skills_match": {
                        "matching": ["Unable to determine matching skills"],
                        "missing": ["Unable to determine skill gaps"],
                    },
                    "recommendations": [
                        "Consider reviewing the job description carefully and highlighting relevant experience in your application."
                    ],
                }
        except Exception as e:
            logger.error(f"Error in analyze_job_fit: {str(e)}")
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
        {self.personal_agent.get_formatted_background()}
        
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
        {self.personal_agent.get_formatted_background()}
        
        Provide a JSON response with:
        1. ranked_jobs: list of jobs sorted by fit
        2. fit_scores: list of match percentages
        3. key_matches: list of matching criteria
        4. company_fit_analysis: analysis of company culture fit
        """

        response = self.llm.generate_text(prompt)
        self.save_context("Refine search results", response)
        return response
