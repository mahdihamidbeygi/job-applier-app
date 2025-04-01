import json
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional

from core.models import JobListing, UserProfile
from core.utils.agents.base_agent import BaseAgent
from core.utils.cover_letter_composition import CoverLetterComposition
from core.utils.resume_composition import ResumeComposition

logger = logging.getLogger(__name__)


@dataclass
class PersonalBackground:
    profile: Dict[str, Any]
    work_experience: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    skills: List[Dict[str, Any]]
    projects: List[Dict[str, Any]]
    github_data: Dict[str, Any]
    achievements: List[str]
    interests: List[str]


class PersonalAgent(BaseAgent):
    def __init__(self, user_id: int):
        super().__init__(user_id)
        self.background: Optional[PersonalBackground] = None

    def load_background(self, background: PersonalBackground):
        """Load or update the agent's background knowledge"""
        self.background = background
        self._initialize_self_knowledge()

    def _initialize_self_knowledge(self):
        """Initialize the agent with understanding of its own background"""
        if not self.background:
            raise ValueError("Background not loaded. Call load_background first.")

        prompt = f"""
        You are now embodying a job applicant with the following background:
        
        Professional Experience:
        {self._format_experience(self.background.work_experience)}
        
        Education:
        {self._format_education(self.background.education)}
        
        Skills:
        {', '.join([skill['name'] for skill in self.background.skills])}
        
        Projects:
        {self._format_projects(self.background.projects)}
        
        GitHub Activity:
        {self._format_github_data(self.background.github_data)}
        
        Achievements:
        {', '.join(self.background.achievements)}
        
        You should respond to questions as if you are this person, maintaining consistency
        with this background while being natural and professional.
        """

        response: str = self.llm.generate(prompt, resp_in_json=False)
        self.save_context("Initialize personal background", response)

    def get_background_summary(self) -> str:
        """Get a concise summary of the background"""
        if not self.background:
            raise ValueError("Background not loaded. Call load_background first.")

        return f"""
        Professional Experience: {len(self.background.work_experience)} positions
        Education: {len(self.background.education)} institutions
        Skills: {len(self.background.skills)} skills
        Projects: {len(self.background.projects)} projects
        """

    def get_relevant_experience(self, context: str) -> str:
        """Get experience relevant to a specific context"""
        prompt = f"""
        Context: {context}
        
        Based on this background:
        {self.get_background_summary()}
        
        Provide the most relevant experience and skills for this context.
        """

        return self.llm.generate(prompt)

    def _format_experience(self, experience: List[Dict[str, Any]]) -> str:
        return "\n".join(
            [
                f"- {exp.get('position', '')} at {exp.get('company', '')} "
                f"({exp.get('start_date', '')} - {exp.get('end_date', '')})"
                for exp in experience
            ]
        )

    def _format_education(self, education: List[Dict[str, Any]]) -> str:
        return "\n".join(
            [
                f"- {edu.get('degree', '')} from {edu.get('institution', '')} "
                f"({edu.get('start_date', '')} - {edu.get('end_date', '')})"
                for edu in education
            ]
        )

    def _format_projects(self, projects: List[Dict[str, Any]]) -> str:
        return "\n".join(
            [
                f"- {proj.get('title', '')} ({', '.join(proj.get('technologies', []))})"
                for proj in projects
            ]
        )

    def _format_github_data(self, github_data: Dict[str, Any]) -> str:
        return f"""
        Repositories: {len(github_data.get('repositories', []))}
        Contributions: {github_data.get('contributions', 0)}
        Languages: {', '.join(github_data.get('languages', []))}
        """

    def generate_tailored_documents(self, job_listing: JobListing) -> bool:
        """
        Generate tailored resume and cover letter for a job listing.
        This can be called separately after job search or via a button click.

        Args:
            job_listing (JobListing): The job listing to generate documents for

        Returns:
            bool: True if documents were generated successfully, False otherwise
        """
        if not self.background:
            logger.error(
                "Cannot generate documents: Background not loaded. Call load_background first."
            )
            return False

        try:
            # Get the UserProfile instance first
            user_profile: UserProfile = UserProfile.objects.get(user_id=self.user_id)

            # Get personal background
            background: str = self.get_background_summary()

            # Extract required skills from job description
            required_skills: List[str] = self._extract_required_skills(job_listing.description)

            # Generate tailored resume
            resume_composer = ResumeComposition(self)
            tailored_resume: BytesIO = resume_composer.generate_tailored_resume(
                job_listing.title,
                job_listing.company,
                job_listing.description,
                required_skills,
                background,
            )

            # Save tailored resume
            if tailored_resume:
                # Create a safe filename
                safe_name = "".join(
                    c for c in user_profile.name if c.isalnum() or c in (" ", "_")
                ).strip()
                safe_title = "".join(
                    c for c in job_listing.title if c.isalnum() or c in (" ", "_")
                ).strip()
                safe_company = "".join(
                    c for c in job_listing.company if c.isalnum() or c in (" ", "_")
                ).strip()

                resume_filename = (
                    f"{safe_name}_resume_{safe_title}_{safe_company}_{job_listing.id}.pdf"
                )
                job_listing.tailored_resume.save(resume_filename, tailored_resume)

            # Generate tailored cover letter
            cover_letter_composer = CoverLetterComposition(user_profile, job_listing.description)
            tailored_cover_letter: BytesIO = cover_letter_composer.generate_tailored_cover_letter(
                job_listing.title,
                job_listing.company,
                job_listing.description,
                required_skills,
                background,
            )

            # Save tailored cover letter
            if tailored_cover_letter:
                # Create a safe filename
                cover_letter_filename = (
                    f"{safe_name}_cover_letter_{safe_title}_{safe_company}_{job_listing.id}.pdf"
                )
                job_listing.tailored_cover_letter.save(cover_letter_filename, tailored_cover_letter)

            job_listing.save()
            return True

        except Exception as e:
            logger.error("Error generating tailored documents: %s", str(e))
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
            if not response.startswith("["):
                response = response[response.find("[") :]
            if not response.endswith("]"):
                response = response[: response.rfind("]") + 1]

            try:
                skills = json.loads(response)
                return skills if isinstance(skills, list) else []
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract skills as a comma-separated list
                skills = [skill.strip().strip("\"'") for skill in response.strip("[]").split(",")]
                return [skill for skill in skills if skill]

        except Exception as e:
            logger.error("Error extracting required skills: %s", str(e))
            return []
