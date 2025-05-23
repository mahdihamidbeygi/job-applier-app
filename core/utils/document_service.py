"""
Document generation service for centralizing document creation functionality.
"""

import logging
from datetime import date
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Union

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from core.models import JobListing, UserProfile, WorkExperience
from core.utils.agents.personal_agent import PersonalAgent, PersonalBackground
from core.utils.cover_letter_composition import CoverLetterComposition
from core.utils.db_utils import safe_get_or_none
from core.utils.logging_utils import log_execution_time, log_exceptions
from core.utils.resume_composition import ResumeComposition

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Service for generating and managing documents such as resumes and cover letters.
    Centralizes all document-related operations to ensure consistency and reusability.
    """

    def __init__(self, user_id: int):
        """
        Initialize the document service.

        Args:
            user_id: The ID of the user for whom to generate documents
        """
        self.user_id = user_id
        self.user = safe_get_or_none(User, id=user_id)
        if not self.user:
            raise ValueError(f"User with ID {user_id} not found")

        self.profile = safe_get_or_none(UserProfile, user=self.user)
        if not self.profile:
            raise ValueError(f"Profile for user {user_id} not found")

        self.personal_agent = None
        self.resume_composition = None
        self.cover_letter_composition = None

    @log_execution_time()
    @log_exceptions(level=logging.ERROR)
    def generate_resume(
        self,
        job_title: str,
        job_description: str,
        company: str,
        required_skills: Optional[List[str]] = None,
    ) -> BytesIO:
        """
        Generate a tailored resume for a job.

        Args:
            job_title: The title of the job
            job_description: The description of the job
            company: The company offering the job
            required_skills: Optional list of required skills

        Returns:
            BytesIO: A buffer containing the resume PDF
        """
        self._load_personal_agent()

        if self.resume_composition is None:
            self.resume_composition = ResumeComposition(self.personal_agent)

        if required_skills is None:
            required_skills = []

        return self.resume_composition.generate_tailored_resume(
            job_title=job_title,
            company=company,
            job_info=job_description,
            required_skills=required_skills,
            background=self.personal_agent.background,
        )

    @log_execution_time()
    @log_exceptions(level=logging.ERROR)
    def generate_cover_letter(
        self,
        job_title: str,
        job_description: str,
        company: str,
    ) -> BytesIO:
        """
        Generate a cover letter for a job.

        Args:
            job_title: The title of the job
            job_description: The description of the job
            company: The company offering the job

        Returns:
            BytesIO: A buffer containing the cover letter PDF
        """
        self._load_personal_agent()

        if self.cover_letter_composition is None:
            self.cover_letter_composition = CoverLetterComposition(
                user_info=self.profile,
                job_desc=job_description,
            )

        # Generate the content for the letter
        content = self._generate_cover_letter_content(
            job_title=job_title,
            job_description=job_description,
            company=company,
        )

        # Build the cover letter PDF
        return self.cover_letter_composition.build(content=content)

    def _generate_cover_letter_content(
        self, job_title: str, job_description: str, company: str
    ) -> Dict[str, str]:
        """Generate content for the cover letter."""
        # This would typically use an LLM to generate content
        # For now, we'll use a simple template
        opening = f"Dear Hiring Manager at {company},"

        main_content = (
            f"I am writing to express my interest in the {job_title} position at {company}. "
            f"With my background in {self.profile.title or 'the field'}, I believe I would "
            f"be a great fit for this role.\n\n"
            f"My experience spans across various projects and roles, which have equipped "
            f"me with the skills necessary to excel in this position. The job description "
            f"mentions requirements that align well with my expertise."
        )

        closing = (
            f"I would welcome the opportunity to discuss how my skills and experience "
            f"could benefit {company}. Thank you for considering my application."
        )

        return {
            "opening": opening,
            "main_content": main_content,
            "closing": closing,
        }

    @log_execution_time()
    @log_exceptions(level=logging.ERROR)
    def save_documents(
        self,
        job_title: str,
        company: str,
        resume_buffer: BytesIO,
        cover_letter_buffer: BytesIO,
        job_listing: Optional[JobListing] = None,
    ) -> Tuple[str, str]:
        """
        Save generated documents to storage.

        Args:
            job_title: The title of the job
            company: The company offering the job
            resume_buffer: Buffer containing the resume PDF
            cover_letter_buffer: Buffer containing the cover letter PDF
            job_listing: Optional job listing to associate documents with

        Returns:
            Tuple[str, str]: The URLs of the saved documents (resume, cover letter)
        """
        # Format the filename components
        username = self.user.username
        today = date.today().strftime("%Y%m%d")
        company_slug = company.lower().replace(" ", "_")
        job_title_slug = job_title.lower().replace(" ", "_")

        # Define the file paths
        resume_filename = f"resume_{username}_{company_slug}_{today}.pdf"
        cover_letter_filename = f"cover_letter_{username}_{company_slug}_{today}.pdf"

        resume_path = f"documents/{username}/resumes/{resume_filename}"
        cover_letter_path = f"documents/{username}/cover_letters/{cover_letter_filename}"

        # Save the files to storage
        resume_buffer.seek(0)
        cover_letter_buffer.seek(0)

        resume_url = default_storage.save(resume_path, ContentFile(resume_buffer.read()))

        cover_letter_url = default_storage.save(
            cover_letter_path, ContentFile(cover_letter_buffer.read())
        )

        # If a job listing was provided, update it with the document references
        if job_listing:
            resume_file = ContentFile(resume_buffer.getvalue())
            resume_file.name = resume_filename

            cover_letter_file = ContentFile(cover_letter_buffer.getvalue())
            cover_letter_file.name = cover_letter_filename

            job_listing.tailored_resume = resume_file
            job_listing.tailored_cover_letter = cover_letter_file
            job_listing.save(update_fields=["tailored_resume", "tailored_cover_letter"])

        return default_storage.url(resume_url), default_storage.url(cover_letter_url)

    @log_execution_time()
    @log_exceptions(level=logging.ERROR)
    def generate_and_save_documents(
        self,
        job_title: str,
        job_description: str,
        company: str,
        required_skills: Optional[List[str]] = None,
        job_listing: Optional[JobListing] = None,
    ) -> Dict[str, str]:
        """
        Generate and save both resume and cover letter in one operation.

        Args:
            job_title: The title of the job
            job_description: The description of the job
            company: The company offering the job
            required_skills: Optional list of required skills
            job_listing: Optional job listing to associate documents with

        Returns:
            Dict[str, str]: A dictionary with the URLs of the saved documents
        """
        # Generate the documents
        resume_buffer = self.generate_resume(
            job_title=job_title,
            job_description=job_description,
            company=company,
            required_skills=required_skills,
        )

        cover_letter_buffer = self.generate_cover_letter(
            job_title=job_title,
            job_description=job_description,
            company=company,
        )

        # Save the documents
        resume_url, cover_letter_url = self.save_documents(
            job_title=job_title,
            company=company,
            resume_buffer=resume_buffer,
            cover_letter_buffer=cover_letter_buffer,
            job_listing=job_listing,
        )

        return {
            "resume_url": resume_url,
            "cover_letter_url": cover_letter_url,
        }
