import json
import logging
from io import BytesIO
from typing import Any, Dict, List

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from core.utils.agents.job_agent import JobAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.llm_clients import GoogleClient, GrokClient
from django.conf import settings

logger = logging.getLogger(__name__)


class CoverLetterComposition:
    def __init__(self, personal_agent: PersonalAgent, job_agent: JobAgent):
        """
        Initialize the CoverLetterComposition class.

        Args:
            user_info (Dict[str, Any]): Dictionary containing user information
            company_info (Dict[str, Any]): Dictionary containing company and job information
        """
        self.personal_agent: PersonalAgent = personal_agent
        self.job_agent: JobAgent = job_agent
        self.buffer = BytesIO()
        self.styles = self._setup_styles()
        self.llm = GoogleClient()

    def _setup_styles(self) -> Dict[str, ParagraphStyle]:
        """Set up custom styles for the cover letter."""
        styles = getSampleStyleSheet()

        # Salutation style
        styles.add(
            ParagraphStyle(
                name="Salutation",
                fontSize=11,
                leading=13,
                spaceBefore=0,
                spaceAfter=12,
                alignment=0,  # Left alignment for salutation
            )
        )

        # Body style
        styles.add(
            ParagraphStyle(
                name="Body",
                fontSize=11,
                leading=13,
                spaceBefore=6,
                spaceAfter=6,
                alignment=4,  # Full justification for body paragraphs
                firstLineIndent=36,  # 0.5 inch indent for paragraphs
            )
        )

        # Closing style
        styles.add(
            ParagraphStyle(
                name="Closing",
                fontSize=11,
                leading=13,
                spaceBefore=12,
                spaceAfter=6,  # Reduced from 36 to 6
                alignment=0,  # Left alignment for closing
            )
        )

        # Signature style
        styles.add(
            ParagraphStyle(
                name="Signature",
                fontSize=11,
                leading=13,
                spaceBefore=0,  # No space before signature
                spaceAfter=0,
                alignment=0,  # Left alignment for signature
            )
        )

        return styles

    def _create_body(self, content: Dict[str, str]) -> List[Any]:
        """Create the body of the cover letter."""
        elements = []

        # Opening paragraph
        if content.get("opening"):
            elements.append(Paragraph(str(content["opening"]), self.styles["Body"]))
            elements.append(Spacer(1, 12))  # Add space after opening paragraph

        # Main paragraphs
        if content.get("main_content"):
            # Convert to string if it's not already
            main_content = str(content["main_content"])
            # Split into paragraphs (handle both \n\n and single \n)
            paragraphs = [p.strip() for p in main_content.replace("\n\n", "\n").split("\n")]
            # Filter out empty paragraphs and add each non-empty one
            for paragraph in paragraphs:
                if paragraph:
                    elements.append(Paragraph(paragraph, self.styles["Body"]))
                    elements.append(Spacer(1, 12))  # Add space between paragraphs

        # Closing paragraph
        if content.get("closing"):
            elements.append(Paragraph(str(content["closing"]), self.styles["Body"]))
            elements.append(Spacer(1, 12))  # Add space after closing paragraph

        return elements

    def build(self) -> BytesIO:
        """
        Build the cover letter with the specified content.
        """
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=letter,
            rightMargin=1.0 * inch,
            leftMargin=1.0 * inch,
            topMargin=1.0 * inch,
            bottomMargin=1.0 * inch,
        )

        story = []
        content: Dict[str, str] = {}  # Initialize content dictionary

        # Generate cover letter content using LLM
        prompt: str = f"""Generate a professional cover letter based on the following information.

                Job Info: {self.job_agent.job_record.get_formatted_info()}

                Candidate Information:
                {self.personal_agent.get_background_str()}

                Instructions:
                Provide the content as a JSON object with five string fields:
                1. "greeting": A professional salutation (e.g., "Dear Hiring Manager," or "Dear [Company Name] Team,"). Use a generic greeting if a specific contact is unknown.
                2. "opening": A compelling opening paragraph introducing the candidate and expressing interest.
                3. "main_content": One or two paragraphs for the main body, highlighting relevant experience, skills, and achievements aligned with the job, demonstrating company/role understanding.
                4. "closing": A strong closing paragraph expressing enthusiasm and call to action.
                5. "closing_phrase": A standard professional closing phrase (e.g., "Sincerely," or "Best regards,").

                Ensure the body content ("opening", "main_content", "closing") is specific, professional, engaging, and matches the candidate's background to the job requirements.
                Strictly adhere to the JSON format with only the specified keys.
                """
        try:
            # --- FIX 1: Define schema as a dictionary with string descriptions ---
            output_schema: Dict[str, str] = {
                "greeting": "string",
                "opening": "string",
                "main_content": "string",
                "closing": "string",
                "closing_phrase": "string",
            }
            logger.debug("Calling LLM generate_structured_output for cover letter...")
            # --- FIX 2: Assign directly to 'content' (it should return a dict) ---
            content: Dict[str, Any] = self.llm.generate_structured_output(
                prompt, output_schema=output_schema
            )
            logger.debug(f"Received structured output for cover letter: {content}")

            if not isinstance(content, dict) or not all(k in content for k in output_schema.keys()):
                logger.error(
                    f"LLM structured output is not a valid dictionary or missing keys. Output: {content}"
                )
                raise ValueError("LLM failed to return the expected cover letter structure.")

            # --- ADD GREETING TO STORY ---
            greeting_text = content.get("greeting", "Dear Hiring Manager,")  # Default fallback
            story.append(Paragraph(greeting_text, self.styles["Salutation"]))
            story.append(Spacer(1, 12))  # Space after greeting

            # Add body using the dictionary directly
            story.extend(
                self._create_body(content)
            )  # _create_body handles opening, main_content, closing

            # --- ADD CLOSING PHRASE TO STORY ---
            closing_phrase_text = content.get("closing_phrase", "Sincerely,")  # Default fallback
            story.append(Paragraph(closing_phrase_text, self.styles["Closing"]))
            # No extra spacer needed here as _create_closing adds the signature right after

            # Add signature (using the modified _create_closing)
            story.extend(self._create_closing())

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.exception(f"Failed to generate or parse cover letter content: {e}")
            error_message = "Error: Could not generate cover letter content."
            # Optionally add greeting/signature even on error? Or just the error.
            story.append(Paragraph(error_message, self.styles["Body"]))
        except Exception as e:
            logger.exception(f"An unexpected error occurred during cover letter generation: {e}")
            error_message = "Error: An unexpected issue occurred while generating the cover letter."
            story.append(Paragraph(error_message, self.styles["Body"]))

        # Build the PDF
        try:
            doc.build(story)
        except Exception as e:
            logger.exception(f"Failed to build cover letter PDF: {e}")
            self.buffer.seek(0)
            self.buffer.truncate()
            self.buffer.write(f"Failed to build PDF: {e}".encode("utf-8"))

        # Reset buffer position
        self.buffer.seek(0)
        return self.buffer

    def _create_closing(self) -> List[Any]:
        """Create the letter signature."""
        elements = []

        # Use name from UserProfile if available
        user_name = (
            self.personal_agent.user_profile.user.get_full_name() or "Applicant Name"
        )  # Default fallback
        elements.append(Paragraph(user_name, self.styles["Signature"]))
        return elements
