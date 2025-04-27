"""
Application agent for processing job applications.
"""

from io import BytesIO
import logging
from typing import Any, Dict, List, Optional
from datetime import date

from core.utils.agents.base_agent import BaseAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.agents.job_agent import JobAgent
from core.utils.rag.job_knowledge import JobKnowledgeBase
from core.utils.logging_utils import log_exceptions
from core.utils.resume_composition import ResumeComposition
from core.utils.cover_letter_composition import CoverLetterComposition
from core.models.jobs import JobListing
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.text import slugify

logger = logging.getLogger(__name__)


class ApplicationAgent(BaseAgent):
    """
    Agent for assisting with job applications, including form-filling
    and question answering.
    """

    def __init__(
        self,
        user_id: int,
        personal_agent: Optional[PersonalAgent] = None,
        job_agent: Optional[JobAgent] = None,
    ):
        """
        Initialize the application agent.

        Args:
            user_id: The ID of the user
            personal_agent: Optional personal agent that can provide user background
        """
        super().__init__(user_id=user_id)
        self.personal_agent: PersonalAgent = personal_agent
        self.knowledge_base = JobKnowledgeBase()
        self.job_agent: JobAgent = job_agent

    @log_exceptions(level=logging.ERROR)
    def generate_answer(self, question: str) -> str:
        """
        Generate an answer to a job application question.

        Args:
            question: The question to answer

        Returns:
            The generated answer
        """
        if not self.personal_agent:
            logger.error("Personal agent not loaded")
            return "Error: Personal agent not loaded."

        # Prepare prompt for the model
        prompt = self._prepare_answer_prompt(question)

        # Generate the answer
        response = self.llm.generate_text(
            prompt=prompt,
            max_tokens=500,
            temperature=0.2,
        )

        return response or "Unable to generate an answer."

    @log_exceptions(level=logging.ERROR)
    def fill_text_field(self, field_label: str) -> str:
        """
        Fill a text field based on the field label.

        Args:
            field_label: The label of the field

        Returns:
            The value to fill in the field
        """

        # Map common field labels to user data
        field_label_lower = field_label.lower()

        # Handle name fields
        if any(name in field_label_lower for name in ["first name", "firstname", "given name"]):
            return self.personal_agent.user_profile.user.first_name

        if any(
            name in field_label_lower
            for name in ["last name", "lastname", "surname", "family name"]
        ):
            return self.personal_agent.user_profile.user.last_name

        if "full name" in field_label_lower or "name" == field_label_lower:
            return self.personal_agent.user_profile.full_name

        # Handle contact information
        if "email" in field_label_lower:
            return self.personal_agent.user_profile.email

        if any(phone in field_label_lower for phone in ["phone", "mobile", "cell"]):
            return self.personal_agent.user_profile.phone

        # Handle location fields
        if any(loc in field_label_lower for loc in ["address", "street"]):
            return self.personal_agent.user_profile.address

        if "city" in field_label_lower:
            return self.personal_agent.user_profile.city

        if any(state in field_label_lower for state in ["state", "province"]):
            return self.personal_agent.user_profile.state

        if "country" in field_label_lower:
            return self.personal_agent.user_profile.country

        if any(code in field_label_lower for code in ["zip", "postal", "postcode"]):
            return self.personal_agent.user_profile.postal_code

        # Handle professional fields
        if "resume" in field_label_lower:
            # This should be handled specially for file uploads
            return self.personal_agent.get_background_str()

        if any(summary in field_label_lower for summary in ["summary", "profile", "about", "bio"]):
            return self.personal_agent.user_profile.professional_summary

        if "linkedin" in field_label_lower:
            return self.personal_agent.user_profile.linkedin_url

        if "website" in field_label_lower or "portfolio" in field_label_lower:
            return self.personal_agent.user_profile.website

        if "github" in field_label_lower:
            return self.personal_agent.user_profile.github_url

        # If we don't have a direct match, use LLM to generate an answer
        prompt = self._prepare_field_prompt(field_label)
        response = self.llm.generate_text(
            prompt=prompt,
            max_tokens=100,
            temperature=0.3,
        )

        return response or ""

    def fill_text_field_with_llm(self, field_labels: List[Dict[str, Any]]) -> str:
        """
        Fill a text field based on the field label.

        Args:
            field_labels: The labels of the fields

        Returns:
        """
        prompt: str = f"""
        You are an expert at filling out job application forms. Let's say that you are a person applying for
        the role of {self.job_agent.job_record.title} at {self.job_agent.job_record.company}.
        
        Here is information about me:
        {self.personal_agent.get_formatted_background()}

        Here is the job information:
        {self.job_agent.job_record.get_formatted_info() if self.job_agent.job_record else 'Not provided'}

        Here is the field labels:
        {field_labels} 

        Please fill out the fields based on the information provided.
        Rules:
        1. Directly answer the field
        2. Demonstrate relevant experience
        3. Align with job requirements
        4. Maintain professional tone
        5. Reflect company culture
        6. keep the format of the field labels
        7. fill out the field inputs
        8. return the fields with the filled values as aDict[str, Any]
        """

        response: str = self.llm.generate_text(
            prompt=prompt,
            max_tokens=100,
            temperature=0.3,
        )

        return response

    @log_exceptions(level=logging.ERROR)
    def select_option(self, field_label: str, options: List[str]) -> str:
        """
        Select the most appropriate option from a list based on the field label.

        Args:
            field_label: The label of the field
            options: The available options

        Returns:
            The selected option
        """
        if not options:
            return ""

        # For education level fields
        field_label_lower = field_label.lower()
        if any(edu in field_label_lower for edu in ["education", "degree", "qualification"]):
            education_order = [
                "high school",
                "secondary",
                "diploma",
                "associate",
                "bachelor",
                "undergraduate",
                "graduate",
                "master",
                "doctorate",
                "phd",
                "postgraduate",
            ]

            # Find the user's highest education level
            highest_education = None
            if self.personal_agent.user_profile.education:
                for edu in education_order:
                    for user_edu in self.personal_agent.user_profile.education.all():
                        if edu in user_edu.get("degree", "").lower():
                            highest_education = edu

            # Select the closest option
            if highest_education:
                for option in options:
                    option_lower = option.lower()
                    for edu in education_order[education_order.index(highest_education) :]:
                        if edu in option_lower:
                            return option

        # For years of experience fields
        if "experience" in field_label_lower and "year" in field_label_lower:
            years_of_experience = 0
            if self.personal_agent.user_profile.work_experiences:
                # Calculate total years of experience from work experiences
                pass  # Implementation depends on data structure

            # Select the closest option
            for option in options:
                option_lower = option.lower()
                for i in range(20):  # Check for 0-20 years
                    if str(i) in option_lower:
                        if i <= years_of_experience <= i + 2:
                            return option

        # For general cases, use LLM to select the best option
        prompt = self._prepare_option_prompt(field_label, options)
        response = self.llm.generate_text(
            prompt=prompt,
            max_tokens=50,
            temperature=0.1,
        )

        # Ensure the response is one of the options
        for option in options:
            if option.lower() in response.lower():
                return option

        # Default to first option if no match
        return options[0]

    @log_exceptions(level=logging.ERROR)
    def select_checkboxes(self, field_label: str, options: List[str]) -> List[str]:
        """
        Select appropriate checkboxes from a list based on the field label.

        Args:
            field_label: The label of the field
            options: The available options

        Returns:
            List of selected options
        """
        if not options:
            return []

        # For skills
        field_label_lower = field_label.lower()
        if "skill" in field_label_lower:
            selected_skills: List[str] = []
            user_skills: List[str] = []

            if self.personal_agent.user_profile.skills:
                user_skills: List[str] = [
                    skill.get("name", "").lower()
                    for skill in self.personal_agent.user_profile.skills
                ]

            for option in options:
                option_lower = option.lower()
                if any(skill in option_lower for skill in user_skills):
                    selected_skills.append(option)

            # If we found matches, return them
            if selected_skills:
                return selected_skills

        # For general cases, use LLM to select options
        prompt = self._prepare_checkboxes_prompt(field_label, options)
        response = self.llm.generate_text(
            prompt=prompt,
            max_tokens=100,
            temperature=0.1,
        )

        # Parse the response to find options
        selected_options = []
        for option in options:
            if option.lower() in response.lower():
                selected_options.append(option)

        return selected_options

    @log_exceptions(level=logging.ERROR)
    def fill_date_field(self, field_label: str) -> str:
        """
        Fill a date field based on the field label.

        Args:
            field_label: The label of the field

        Returns:
            The date value in YYYY-MM-DD format
        """
        field_label_lower = field_label.lower()

        # Handle common date fields
        if "birth" in field_label_lower:
            # This is sensitive info - leave blank
            return ""

        if "start" in field_label_lower:
            # Get most recent work experience start date
            if self.personal_agent.user_profile.work_experience:
                for exp in sorted(
                    self.personal_agent.user_profile.work_experience,
                    key=lambda x: x.get("start_date", ""),
                    reverse=True,
                ):
                    if "start_date" in exp:
                        return str(exp["start_date"])

        if "end" in field_label_lower:
            # Typically this is for availability - set to today or a future date
            from datetime import date

            today = date.today()
            return today.strftime("%Y-%m-%d")

        # Default to empty for unknown date fields
        return ""

    def _prepare_answer_prompt(self, question: str) -> str:
        """
        Prepare a prompt for generating an answer to a job application question.

        Args:
            question: The job application question

        Returns:
            The prompt for the LLM
        """
        background_info: str = self._format_background_for_prompt()

        return f"""
        I need to answer a job application question for the role of {self.job_agent.job_record.title} at {self.job_agent.job_record.company}.
        
        Here is information about me:
        {background_info}
        
        Here is the job information:
        {self.job_agent.job_record.get_formatted_info() if self.job_agent.job_record else 'Not provided'}
        
        The question is: {question}
        
        Please provide a detailed, professional answer that highlights my relevant experience and skills.
        The answer should be concise but thorough, and it should be tailored to the specific job requirements.
        just return the answer, no other text.
        """

    def _prepare_field_prompt(self, field_label: str) -> str:
        """
        Prepare a prompt for generating a field value.

        Args:
            field_label: The label of the field

        Returns:
            The prompt for the LLM
        """
        background_info = self._format_background_for_prompt()

        return f"""
        You are an expert at filling out job application forms. Let's say that you are a person applying for
        the role of {self.job_agent.job_record.title} at {self.job_agent.job_record.company}.
        
        Here is information about me:
        {background_info}
        
        The field label is: {field_label}
        
        Please provide a short, appropriate value for this field based on my background. 
        Keep it concise and relevant. Do not use more than a sentence or two.
        """

    def _prepare_option_prompt(self, field_label: str, options: List[str]) -> str:
        """
        Prepare a prompt for selecting an option.

        Args:
            field_label: The label of the field
            options: The available options

        Returns:
            The prompt for the LLM
        """
        background_info = self._format_background_for_prompt()
        options_text = "\n".join([f"- {option}" for option in options])

        return f"""
        You are an expert at filling out job application forms. Let's say that you are a person applying for
        the role of {self.job_agent.job_record.title} at {self.job_agent.job_record.company}.
        
        Here is information about me:
        {background_info}
        
        The field label is: {field_label}
        
        Available options are:
        {options_text}
        
        Please select the single most appropriate option from the list based on my background and the field label.
        Your response should be exactly one of the options listed above, with no modifications.
        """

    def _prepare_checkboxes_prompt(self, field_label: str, options: List[str]) -> str:
        """
        Prepare a prompt for selecting checkboxes.

        Args:
            field_label: The label of the field
            options: The available options

        Returns:
            The prompt for the LLM
        """
        background_info = self._format_background_for_prompt()
        options_text = "\n".join([f"- {option}" for option in options])

        return f"""
        You are an expert at filling out job application forms. Let's say that you are a person applying for
        the role of {self.job_agent.job_record.title} at {self.job_agent.job_record.company}.
        
        Here is information about me:
        {background_info}
        
        The field label is: {field_label}
        
        Available options are:
        {options_text}
        
        Please select all appropriate options from the list based on my background and the field label.
        Your response should list each selected option, each on a separate line, exactly as written in the options above.
        """

    def _format_background_for_prompt(self) -> str:
        """
        Format background information for inclusion in prompts.

        Returns:
            Formatted background information
        """
        # Get background info as dictionary, then format it as string
        background_info = self.personal_agent.get_formatted_background()

        return "\n".join([f"{k}: {v}" for k, v in background_info.items() if v])

    def fill_application_form(
        self, form_fields: List[Dict[str, Any]], job_description: str
    ) -> Dict[str, Any]:
        """Fills out job application forms"""
        # Get company context
        company_context = self.knowledge_base.get_company_context(
            job_description.split("\n")[0]  # Assuming first line contains company name
        )

        responses = {}
        for field in form_fields:
            prompt = f"""
            Field: {field['label']}
            Type: {field['type']}
            Job Context: {job_description[:100]}...
            
            Company Context:
            {company_context}
            
            Relevant Experience:
            {self.personal_agent.get_relevant_experience(field['label'])}
            
            Generate appropriate response that:
            1. Directly answers the field
            2. Demonstrates relevant experience
            3. Aligns with job requirements
            4. Maintains professional tone
            5. Reflects company culture
            """

            response: str = self.llm.generate_text(prompt)
            responses[field["id"]] = response
            self.save_context(f"Fill field: {field['label']}", response)

        return responses

    def handle_screening_questions(
        self, questions: List[str], job_context: str
    ) -> List[Dict[str, Any]]:
        """Handles pre-screening questions"""
        # Get relevant interview questions from knowledge base
        relevant_questions = self.knowledge_base.get_relevant_interview_questions(
            job_context.split("\n")[0]  # Assuming first line contains job title
        )

        responses = []
        for question in questions:
            # Get relevant experience for this question
            relevant_background = self.personal_agent.get_relevant_experience(question)

            # Find similar questions in knowledge base
            similar_questions = [
                q for q in relevant_questions if q.get("question", "").lower() in question.lower()
            ]

            prompt = f"""
            Question: {question}
            Job Context: {job_context}
            
            Similar Questions Found:
            {similar_questions}
            
            Relevant Experience:
            {relevant_background}
            
            Provide a concise, focused response (2-3 sentences maximum) that:
            1. Directly answers the question
            2. Demonstrates relevant experience
            3. Aligns with job requirements
            4. Maintains consistency with previous answers
            5. Incorporates insights from similar questions
            """

            response: str = self.llm.generate_text(prompt)
            responses.append({"question": question, "answer": response})
            self.save_context(f"Answer question: {question[:50]}...", response)

        return responses

    def generate_cover_letter(self) -> str:
        """Generates a tailored cover letter"""
        # # Get company context
        # company_context = self.knowledge_base.get_company_context(
        #     self.job_agent.job_record.description.split("\n")[
        #         0
        #     ]  # Assuming first line contains company name
        # )

        # prompt = f"""
        # Job Description:
        # {self.job_agent.job_record.get_formatted_info()}

        # Company Context:
        # {company_context}

        # Candidate Background:
        # {self.personal_agent.get_background_str()}

        # GitHub Profile:
        # {self.personal_agent._format_github_data(self.personal_agent.user_profile.github_data if hasattr(self.personal_agent, 'user_profile') else {})}

        # Generate a professional cover letter that:
        # 1. Opens with a strong hook
        # 2. Highlights relevant experience and GitHub contributions
        # 3. Demonstrates understanding of the role
        # 4. Shows enthusiasm for the company
        # 5. Closes with a call to action
        # 6. Reflects company culture and values
        # 7. References specific GitHub projects or contributions when relevant

        # Format Requirements:
        # 1. Start with "Dear Hiring Manager," on its own line
        # 2. Add a blank line after the salutation
        # 3. Write exactly 3 paragraphs:
        #    - First paragraph: Introduction and hook
        #    - Second paragraph: Relevant experience, GitHub contributions, and skills
        #    - Third paragraph: Closing and call to action
        # 4. End with "Sincerely," followed by a blank line and the candidate's name
        # 5. Each paragraph must be unique - do not repeat any sentences or content
        # 6. Keep paragraphs focused and concise

        # Return ONLY the formatted cover letter text, with no additional commentary.
        # """

        # response: str = self.llm.generate_text(prompt)

        # # Clean up formatting
        # # Split into paragraphs and remove empty lines
        # paragraphs = [p.strip() for p in response.split("\n") if p.strip()]

        # # Remove any duplicate paragraphs while preserving order
        # seen = set()
        # unique_paragraphs = []
        # for p in paragraphs:
        #     normalized_p = " ".join(p.lower().split())  # Normalize for comparison
        #     if normalized_p not in seen and p not in ["Dear Hiring Manager,", "Sincerely,"]:
        #         seen.add(normalized_p)
        #         unique_paragraphs.append(p)

        # # Ensure proper structure
        # formatted_parts = []
        # formatted_parts.append("Dear Hiring Manager,")  # Salutation
        # formatted_parts.extend(unique_paragraphs[:3])  # Main paragraphs (limit to 3)
        # formatted_parts.append("Sincerely,")  # Closing
        # formatted_parts.append(getattr(self.personal_agent.user_profile, "name", ""))  # Name

        # # Join with double line breaks
        # formatted_letter = "\n\n".join(formatted_parts)

        cover_letter_composition = CoverLetterComposition(
            personal_agent=self.personal_agent,
            job_agent=self.job_agent,
        )

        cover_letter_buffer: BytesIO = cover_letter_composition.build()

        # Format the filename components
        username: Any | str = self.personal_agent.user_profile.user.get_full_name().replace(
            " ", "_"
        )
        today: str = date.today().strftime("%Y%m%d")
        company_slug: str = self.job_agent.job_record.company.lower().replace(" ", "_")
        job_title_slug = self.job_agent.job_record.title.lower().replace(" ", "_")

        # Define the file paths
        cover_letter_filename: str = (
            f"cover_letter_{username}_{company_slug}_{job_title_slug}_{today}.pdf"
        )

        cover_letter_path = f"documents/{username}/{cover_letter_filename}"

        # Save the files to storage
        cover_letter_buffer.seek(0)

        cover_letter_url = default_storage.save(
            cover_letter_path, ContentFile(cover_letter_buffer.read())
        )

        # If a job listing was provided, update it with the document references
        if self.job_agent.job_record:
            cover_letter_file = ContentFile(cover_letter_buffer.getvalue())
            cover_letter_file.name = cover_letter_filename

            self.job_agent.job_record.tailored_cover_letter = cover_letter_file
            self.job_agent.job_record.save(update_fields=["tailored_cover_letter"])

        return default_storage.url(cover_letter_url)

    def prepare_interview_responses(self) -> List[Dict[str, Any]]:
        """Prepares potential interview responses"""
        # Get relevant interview questions
        relevant_questions = self.knowledge_base.get_relevant_interview_questions(
            self.job_agent.job_record.description.split("\n")[
                0
            ]  # Assuming first line contains job title
        )

        prompt = f"""
        Job Description:
        {self.job_agent.job_record.get_formatted_info()}
        
        Candidate Background:
        {self.personal_agent.get_background_str()}
        
        Relevant Interview Questions:
        {relevant_questions}
        
        Generate a JSON response with:
        1. common_questions: list of likely interview questions
        2. responses: list of prepared responses using STAR method
        3. key_points: list of key points to emphasize
        4. questions_to_ask: list of questions for the interviewer
        5. company_specific_prep: company-specific preparation tips
        """

        response: str = self.llm.generate_text(prompt)
        self.save_context("Prepare interview responses", response)
        return response

    def generate_resume(self) -> BytesIO:
        """Generates a tailored resume"""

        resume_composition = ResumeComposition(self.personal_agent)
        resume_buffer: BytesIO = resume_composition.generate_tailored_resume(
            self.job_agent.job_record.get_formatted_info()
        )

        # Format the filename components
        username: Any | str = self.personal_agent.user_profile.user.get_full_name().replace(
            " ", "_"
        )
        today: str = date.today().strftime("%Y%m%d")
        company_slug: str = self.job_agent.job_record.company.lower().replace(" ", "_")
        job_title_slug = self.job_agent.job_record.title.lower().replace(" ", "_")

        # Define the file paths
        resume_filename: str = f"resume_{username}_{company_slug}_{job_title_slug}_{today}.pdf"

        resume_path: str = f"documents/{username}/{resume_filename}"

        # Save the files to storage
        resume_buffer.seek(0)

        resume_url: str = default_storage.save(resume_path, ContentFile(resume_buffer.read()))

        # If a job listing was provided, update it with the document references
        if self.job_agent.job_record:
            resume_file = ContentFile(resume_buffer.getvalue())
            resume_file.name = resume_filename

            self.job_agent.job_record.tailored_resume = resume_file
            self.job_agent.job_record.save(update_fields=["tailored_resume"])

        return default_storage.url(resume_url)
