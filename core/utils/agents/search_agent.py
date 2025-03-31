from typing import Dict, Any, List
from core.utils.agents.base_agent import BaseAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.rag.job_knowledge import JobKnowledgeBase
from core.utils.job_scrapers.linkedin_scraper import LinkedInJobScraper
from core.models import JobListing
from core.utils.resume_composition import ResumeComposition
from core.utils.cover_letter_composition import CoverLetterComposition
import logging
from django.utils import timezone
import json

logger = logging.getLogger(__name__)

class SearchAgent(BaseAgent):
    def __init__(self, user_id: int, personal_agent: PersonalAgent):
        super().__init__(user_id)
        self.personal_agent = personal_agent
        self.knowledge_base = JobKnowledgeBase()
        self.linkedin_scraper = None
    
    def search_linkedin_jobs(self, role: str, location: str) -> List[JobListing]:
        """Search for jobs on LinkedIn"""
        try:
            # Import task here to avoid circular import
            from core.tasks import generate_documents_async
            
            # Initialize LinkedIn scraper
            scraper = LinkedInJobScraper()
            
            # Search for jobs
            jobs = scraper.search_jobs(role, location)
            
            # Convert to JobListing objects
            job_listings = []
            for job in jobs:
                if job:  # Skip None results
                    # Check for existing job with same title, company, and location
                    existing_job = JobListing.objects.filter(
                        title=job.get('title', ''),
                        company=job.get('company', ''),
                        location=job.get('location', ''),
                        source='linkedin'
                    ).first()
                    
                    if not existing_job:
                        job_listing = JobListing.objects.create(
                            title=job.get('title', ''),
                            company=job.get('company', ''),
                            location=job.get('location', ''),
                            description=job.get('description', ''),
                            source_url=job.get('source_url', ''),
                            source='linkedin',
                            posted_date=timezone.now().date()
                        )
                        
                        job_listings.append(job_listing)
                        
                        # Trigger background document generation
                        generate_documents_async.delay(job_listing.id, self.user_id)
            
            return job_listings
            
        except Exception as e:
            logger.error(f"Error searching LinkedIn jobs: {str(e)}")
            return []

    def generate_tailored_documents(self, job_listing: JobListing) -> bool:
        """
        Generate tailored resume and cover letter for a job listing.
        This can be called separately after job search or via a button click.
        
        Args:
            job_listing (JobListing): The job listing to generate documents for
            
        Returns:
            bool: True if documents were generated successfully, False otherwise
        """
        try:
            # Get the UserProfile instance first
            from core.models import UserProfile
            user_profile = UserProfile.objects.get(user_id=self.user_id)
            
            # Get personal background
            background = self.personal_agent.get_background_summary()
            
            # Extract required skills from job description
            required_skills = self._extract_required_skills(job_listing.description)
            
            # Generate tailored resume
            resume_composer = ResumeComposition(self.personal_agent)
            tailored_resume = resume_composer.generate_tailored_resume(
                job_listing.title,
                job_listing.company,
                job_listing.description,
                required_skills,
                background
            )
            
            # Save tailored resume
            if tailored_resume:
                # Create a safe filename
                safe_name = "".join(c for c in user_profile.name if c.isalnum() or c in (' ', '_')).strip()
                safe_title = "".join(c for c in job_listing.title if c.isalnum() or c in (' ', '_')).strip()
                safe_company = "".join(c for c in job_listing.company if c.isalnum() or c in (' ', '_')).strip()
                
                resume_filename = f"{safe_name}_resume_{safe_title}_{safe_company}_{job_listing.id}.pdf"
                job_listing.tailored_resume.save(resume_filename, tailored_resume)
            
            # Generate tailored cover letter
            cover_letter_composer = CoverLetterComposition(user_profile, job_listing.description)
            tailored_cover_letter = cover_letter_composer.generate_tailored_cover_letter(
                job_listing.title,
                job_listing.company,
                job_listing.description,
                required_skills,
                background
            )
            
            # Save tailored cover letter
            if tailored_cover_letter:
                # Create a safe filename
                cover_letter_filename = f"{safe_name}_cover_letter_{safe_title}_{safe_company}_{job_listing.id}.pdf"
                job_listing.tailored_cover_letter.save(cover_letter_filename, tailored_cover_letter)
            
            job_listing.save()
            return True
            
        except Exception as e:
            logger.error(f"Error generating tailored documents: {str(e)}")
            return False

    def _extract_required_skills(self, job_description: str) -> List[str]:
        """Extract required skills from job description using Ollama"""
        try:
            prompt = f"""
            Extract the required skills from this job description. Return them as a JSON array of strings.
            Focus on technical skills, tools, and technologies.
            
            Job Description:
            {job_description}
            
            Return only the JSON array, no other text. Example format: ["Python", "JavaScript", "React"]
            """
            
            response = self.llm.generate(prompt)
            # Clean the response to ensure it's valid JSON
            response = response.strip()
            if not response.startswith('['):
                response = response[response.find('['):]
            if not response.endswith(']'):
                response = response[:response.rfind(']')+1]
            
            try:
                skills = json.loads(response)
                return skills if isinstance(skills, list) else []
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract skills as a comma-separated list
                skills = [skill.strip().strip('"\'') for skill in response.strip('[]').split(',')]
                return [skill for skill in skills if skill]
            
        except Exception as e:
            logger.error(f"Error extracting required skills: {str(e)}")
            return []
    
    def analyze_job_fit(self, job_posting: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes job posting for fit with personal background"""
        # Get company context from knowledge base
        company_context = self.knowledge_base.get_company_context(
            job_posting.get('company', '')
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
        {self.personal_agent.get_background_summary()}
        
        Provide a response in JSON format with no extra text/numbers/etc:
        1. match_percentage: number between 0-100
        2. key_matching_skills: list of matching skills
        3. potential_gaps: list of missing skills
        4. application_strategy: string with recommended approach
        5. company_fit: analysis of company culture fit
        RULES:
        - DO NOT INCLUDE ANY EXTRA TEXT/NUMBERS/ETC AT THE BEGINNING OR END OF THE RESPONSE
        """
        
        response = self.llm.generate(prompt, resp_in_json=True)
        self.save_context("Analyze job fit", response)
        return response
    
    def suggest_job_search_strategy(self) -> Dict[str, Any]:
        """Suggests personalized job search strategy"""
        # Get similar jobs from knowledge base
        similar_jobs = self.knowledge_base.search_similar_jobs(
            self.personal_agent.get_background_summary()
        )
        
        prompt = f"""
        Based on the candidate's background:
        {self.personal_agent.get_background_summary()}
        
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
        
        response = self.llm.generate(prompt, resp_in_json=True)
        self.save_context("Suggest search strategy", response)
        return response
    
    def refine_job_search(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Refines job search results based on candidate's background"""
        # Get company contexts for all jobs
        company_contexts = {
            job['company']: self.knowledge_base.get_company_context(job['company'])
            for job in search_results
        }
        
        prompt = f"""
        Analyze these job search results and rank them by fit:
        
        Search Results:
        {search_results}
        
        Company Contexts:
        {company_contexts}
        
        Candidate Background:
        {self.personal_agent.get_background_summary()}
        
        Provide a JSON response with:
        1. ranked_jobs: list of jobs sorted by fit
        2. fit_scores: list of match percentages
        3. key_matches: list of matching criteria
        4. company_fit_analysis: analysis of company culture fit
        """
        
        response = self.llm.generate(prompt, resp_in_json=True)
        self.save_context("Refine search results", response)
        return response 