from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from io import BytesIO
from typing import List, Dict, Any
from core.models import UserProfile
from core.utils.local_llms import GrokClient, OllamaClient
import json
import logging

logger = logging.getLogger(__name__)

class CoverLetterComposition:
    def __init__(self, user_info: UserProfile, job_desc: str):
        """
        Initialize the CoverLetterComposition class.
        
        Args:
            user_info (Dict[str, Any]): Dictionary containing user information
            company_info (Dict[str, Any]): Dictionary containing company and job information
        """
        self.user_info: UserProfile = user_info
        self.job_description: str = job_desc
        self.buffer = BytesIO()
        self.styles = self._setup_styles()
        self.grok_client = GrokClient(model="grok-2-1212", temperature=0.0)
        self.llm = OllamaClient(model="llama3:latest", temperature=0.0)

    def _setup_styles(self) -> Dict[str, ParagraphStyle]:
        """Set up custom styles for the cover letter."""
        styles = getSampleStyleSheet()
        
        # Salutation style
        styles.add(ParagraphStyle(
            name='Salutation',
            fontSize=11,
            leading=13,
            spaceBefore=0,
            spaceAfter=12,
            alignment=0  # Left alignment for salutation
        ))
        
        # Body style
        styles.add(ParagraphStyle(
            name='Body',
            fontSize=11,
            leading=13,
            spaceBefore=6,
            spaceAfter=6,
            alignment=4,  # Full justification for body paragraphs
            firstLineIndent=36  # 0.5 inch indent for paragraphs
        ))
        
        # Closing style
        styles.add(ParagraphStyle(
            name='Closing',
            fontSize=11,
            leading=13,
            spaceBefore=12,
            spaceAfter=6,  # Reduced from 36 to 6
            alignment=0  # Left alignment for closing
        ))
        
        # Signature style
        styles.add(ParagraphStyle(
            name='Signature',
            fontSize=11,
            leading=13,
            spaceBefore=0,  # No space before signature
            spaceAfter=0,
            alignment=0  # Left alignment for signature
        ))
        
        return styles
    
    def _create_salutation(self) -> List[Any]:
        """Create the letter salutation."""
        elements = []
        
        try:
            # Generate hiring manager name
            response = self.grok_client.generate(
                f"""
                here's the job description: {self.job_description}
                return a JSON object with a single field 'hiring_manager_name' containing either the hiring manager's name from the job description 
                or 'Hiring Manager' if no name is found. Do not include any explanatory text.
                """
            )
            # Clean the response to ensure it's valid JSON
            response = response.strip()
            if response.startswith('{') and response.endswith('}'):
                hiring_manager = json.loads(response)
                salutation = f"Dear {hiring_manager.get('hiring_manager_name', 'Hiring Manager')},"
            else:
                salutation = "Dear Hiring Manager,"
        except Exception as e:
            logger.info(f"Error generating hiring manager: {str(e)}")
            salutation = "Dear Hiring Manager,"
            
        elements.append(Paragraph(salutation, self.styles['Salutation']))
        return elements
    
    def _create_body(self, content: Dict[str, str]) -> List[Any]:
        """Create the body of the cover letter."""
        elements = []
        
        # Opening paragraph
        if content.get('opening'):
            elements.append(Paragraph(str(content['opening']), self.styles['Body']))
            elements.append(Spacer(1, 12))  # Add space after opening paragraph
            
        # Main paragraphs
        if content.get('main_content'):
            # Convert to string if it's not already
            main_content = str(content['main_content'])
            # Split into paragraphs (handle both \n\n and single \n)
            paragraphs = [p.strip() for p in main_content.replace('\n\n', '\n').split('\n')]
            # Filter out empty paragraphs and add each non-empty one
            for paragraph in paragraphs:
                if paragraph:
                    elements.append(Paragraph(paragraph, self.styles['Body']))
                    elements.append(Spacer(1, 12))  # Add space between paragraphs
                    
        # Closing paragraph
        if content.get('closing'):
            elements.append(Paragraph(str(content['closing']), self.styles['Body']))
            elements.append(Spacer(1, 12))  # Add space after closing paragraph
            
        return elements
    
    def _create_closing(self) -> List[Any]:
        """Create the letter closing."""
        elements = []
        
        elements.append(Paragraph("Sincerely,", self.styles['Closing']))
        # Use name from UserProfile if available, otherwise fall back to User's full name
        user_name = self.user_info.name or self.user_info.user.get_full_name() or self.user_info.user.username
        elements.append(Paragraph(user_name, self.styles['Signature']))
        
        return elements
    
    def build(self) -> BytesIO:
        """
        Build the cover letter with the specified content.
        
        Args:
            content (Dict[str, str]): Dictionary containing the letter content sections
                - opening: Opening paragraph
                - main_content: Main body paragraphs
                - closing: Closing paragraph
        """
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=letter,
            rightMargin=1.0*inch,
            leftMargin=1.0*inch,
            topMargin=1.0*inch,
            bottomMargin=1.0*inch
        )
        
        story = []
        
        # Add salutation
        story.extend(self._create_salutation())
        # Get user's profile information
        user_profile = self.user_info
        
        if user_profile.work_experiences.exists():
            # Format work experiences
            work_experiences = []
            for exp in user_profile.work_experiences.all():
                work_experiences.append({
                    'company': exp.company,
                    'position': exp.position,
                    'start_date': exp.start_date.strftime('%Y-%m-%d') if exp.start_date else None,
                    'end_date': exp.end_date.strftime('%Y-%m-%d') if exp.end_date else None,
                    'current': exp.current,
                    'description': exp.description,
                    'technologies': exp.technologies
                })
        else:
            work_experiences = []
            
        
        if user_profile.skills.exists():
            # Format skills
            skills = []
            for skill in user_profile.skills.all():
                skills.append({
                    'name': skill.name,
                    'category': skill.category,
                    'proficiency': skill.proficiency
                    })
        else:
            skills = []
            
        if user_profile.projects.exists():
            # Format projects
            projects = []
            for proj in user_profile.projects.all():
                projects.append({
                    'title': proj.title,
                    'description': proj.description,
                    'technologies': proj.technologies,
                    'start_date': proj.start_date.strftime('%Y-%m-%d') if proj.start_date else None,
                    'end_date': proj.end_date.strftime('%Y-%m-%d') if proj.end_date else None
                })
        else:
            projects = []
        
        
        # Generate cover letter content using Grok
        prompt = f"""Generate a professional cover letter based on the following information.

                Job Description: {self.job_description}

                Candidate Information:
                - Name: {user_profile.user.get_full_name() or user_profile.user.username}
                - Professional Summary: {user_profile.professional_summary or 'Not provided'}
                - Current Position: {user_profile.current_position or 'Not specified'}
                - Years of Experience: {user_profile.years_of_experience or 'Not specified'}

                Work Experience:
                {json.dumps(work_experiences, indent=2)}

                Skills:
                {json.dumps(skills, indent=2)}

                Projects:
                {json.dumps(projects, indent=2)}

                Please provide the content in JSON format with three sections:
                1. opening : A compelling opening paragraph that introduces the candidate and expresses interest in the position
                2. main_content : one-paragraph main body of the letter that:
                - Highlights relevant work experience and projects that align with the job requirements
                - Emphasizes specific skills and achievements that match the position
                - Demonstrates understanding of the company and role
                3. closing : A strong closing paragraph that expresses enthusiasm for the opportunity

                Make the content specific to the job and company, and ensure it's professional and engaging. 
                Focus on matching the candidate's experience and skills with the job requirements.
                No Dear hiring manager, or any other salutation. No content field name in the JSON object."""

        # try:
        generated_content = self.grok_client.generate(prompt)
        # Parse the generated content as JSON
        content = json.loads(generated_content)
                
        # Add body
        story.extend(self._create_body(content))
        
        # Add closing
        story.extend(self._create_closing())
        
        # Build the PDF
        doc.build(story)
        
        # Reset buffer position
        self.buffer.seek(0)
        return self.buffer 

    def generate_tailored_cover_letter(self, job_title: str, company: str, job_description: str, required_skills: List[str], background: str) -> BytesIO:
        """
        Generate a tailored cover letter for a specific job.
        
        Args:
            job_title (str): The job title
            company (str): The company name
            job_description (str): The job description
            required_skills (List[str]): List of required skills
            background (str): User's background summary
            
        Returns:
            BytesIO: The generated cover letter PDF
        """
        try:
            # Update job description for better tailoring
            self.job_description = f"""
            Position: {job_title}
            Company: {company}
            Required Skills: {', '.join(required_skills)}
            
            Job Description:
            {job_description}
            """
            
            # Generate and return the cover letter
            return self.build()
            
        except Exception as e:
            print(f"Error generating tailored cover letter: {str(e)}")
            return None 