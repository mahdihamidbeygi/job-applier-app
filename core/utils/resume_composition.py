import json
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, LiteralString, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from django.core.files.storage import default_storage

from core.utils.agents.personal_agent import PersonalAgent
from core.utils.local_llms import GoogleClient, OllamaClient


class ResumeComposition:
    def __init__(self, personal_agent: PersonalAgent):
        """
        Initialize the ResumeComposition class.

        Args:
            personal_agent (PersonalAgent): The personal agent containing user data
        """
        self.personal_agent: PersonalAgent = personal_agent
        self.styles: StyleSheet1 = getSampleStyleSheet()
        self._setup_styles()
        self.elements = []
        self.ollama_client = OllamaClient(model="llama3:latest", temperature=0.0)
        self.google_client = GoogleClient()
        self.professional_summary: str = ""
        self.projects: str = ""
        self.skills: str = ""

    def _setup_styles(self):
        # Header style
        self.styles.add(
            ParagraphStyle(
                name="ResumeHeader",
                fontName="Helvetica-Bold",
                fontSize=24,
                spaceAfter=20,
                alignment=TA_CENTER,
            )
        )

        # Job title bold style
        self.styles.add(
            ParagraphStyle(
                name="ResumeJobTitleBold",
                fontName="Helvetica-Bold",
                fontSize=12,
                leftIndent=4,  # Very slight indent for main line
                firstLineIndent=0,
                spaceAfter=2,
            )
        )

        # Contact info style
        self.styles.add(
            ParagraphStyle(
                name="ResumeContact",
                fontName="Helvetica",
                fontSize=12,
                spaceAfter=10,
                leading=15,
                alignment=TA_CENTER,
            )
        )

        # Role title style
        self.styles.add(
            ParagraphStyle(
                name="ResumeRole",
                fontName="Helvetica-Bold",
                fontSize=16,
                spaceAfter=15,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#2c3e50"),
            )
        )

        # Section header style
        self.styles.add(
            ParagraphStyle(
                name="ResumeSectionHeader",
                fontName="Helvetica-Bold",
                fontSize=16,
                spaceBefore=10,
                spaceAfter=10,
                leftIndent=0,
                textColor=colors.HexColor("#2c3e50"),
            )
        )

        # Company name style
        self.styles.add(
            ParagraphStyle(
                name="ResumeCompany", fontName="Helvetica-Bold", fontSize=14, spaceAfter=2
            )
        )

        # Job title style
        self.styles.add(
            ParagraphStyle(name="ResumeJobTitle", fontName="Helvetica", fontSize=13, spaceAfter=2)
        )

        # Date style
        self.styles.add(
            ParagraphStyle(
                name="ResumeDate", fontName="Helvetica", fontSize=11, textColor=colors.gray
            )
        )

        # Location style
        self.styles.add(
            ParagraphStyle(
                name="ResumeLocation",
                fontName="Helvetica",
                fontSize=11,
                textColor=colors.gray,
                alignment=TA_RIGHT,
            )
        )

        # Bullet point style with increased indent
        self.styles.add(
            ParagraphStyle(
                name="ResumeBullet",
                fontName="Helvetica",
                fontSize=12,
                leftIndent=8,  # More indent than the main line
                firstLineIndent=0,
                leading=14,
                spaceAfter=2,
            )
        )

        # Summary style
        self.styles.add(
            ParagraphStyle(
                name="ResumeSummary",
                fontName="Helvetica",
                fontSize=12,
                spaceAfter=10,
                alignment=4,
                leading=16,
            )
        )

        # Project title style
        self.styles.add(
            ParagraphStyle(
                name="ResumeProjectTitle", fontName="Helvetica-Bold", fontSize=13, spaceAfter=2
            )
        )

        # Project description style
        self.styles.add(
            ParagraphStyle(
                name="ResumeProjectDesc",
                fontName="Helvetica",
                fontSize=12,
                spaceAfter=2,
                leading=14,
            )
        )

        # Education style
        self.styles.add(
            ParagraphStyle(name="ResumeEducation", fontName="Helvetica", fontSize=12, spaceAfter=2)
        )

        # Certification style
        self.styles.add(
            ParagraphStyle(
                name="ResumeCertification", fontName="Helvetica", fontSize=12, spaceAfter=2
            )
        )

    def _create_header(self):
        # Name
        self.elements.append(
            Paragraph(self.personal_agent.user_profile.name, self.styles["ResumeHeader"])
        )

        # Title/Role
        if self.personal_agent.user_profile.title:
            self.elements.append(
                Paragraph(self.personal_agent.user_profile.title, self.styles["ResumeRole"])
            )

        # Contact info
        contact_info = []
        if self.personal_agent.user_profile.email:
            contact_info.append(self.personal_agent.user_profile.email)
        if self.personal_agent.user_profile.phone:
            # Extract only numbers from phone string
            phone = "".join(
                char for char in str(self.personal_agent.user_profile.phone) if char.isdigit()
            )
            if len(phone) >= 10:  # Only format if we have enough digits
                if phone.startswith("1") and len(phone) > 10:  # Handle country code 1
                    # Format as +1 XXX XXX XXXX
                    formatted_phone = f"+1 {phone[1:4]} {phone[4:7]} {phone[7:11]}"
                else:
                    # Format as XXX XXX XXXX
                    formatted_phone = f"{phone[:3]} {phone[3:6]} {phone[6:10]}"
                contact_info.append(formatted_phone)
        if self.personal_agent.user_profile.location:
            contact_info.append(self.personal_agent.user_profile.location)
        if self.personal_agent.user_profile.linkedin_url:
            contact_info.append(self.personal_agent.user_profile.linkedin_url)
        if self.personal_agent.user_profile.github_url:
            contact_info.append(self.personal_agent.user_profile.github_url)

        if contact_info:
            self.elements.append(Paragraph(" | ".join(contact_info), self.styles["ResumeContact"]))

        self.elements.append(Spacer(1, 5))

    def _format_date(self, date_str):
        if not date_str:
            return "Present"
        try:
            if isinstance(date_str, str):
                date = datetime.strptime(date_str, "%Y-%m-%d")
            else:  # Assuming it's already a datetime.date object
                date = datetime.combine(date_str, datetime.min.time())
            return date.strftime("%m/%Y").lstrip("0")  # Remove leading zero from month
        except (ValueError, TypeError):
            return str(date_str)

    def _convert_description_to_bullets(self, description):
        """Convert a paragraph description into bullet points."""
        if not description:
            return []

        # Split on periods and semicolons, common sentence separators
        sentences = [s.strip() for s in description.replace(";", ".").split(".") if s.strip()]

        # Convert each sentence into an action-oriented bullet point
        bullet_points = []
        for sentence in sentences:
            # Remove common filler words at the start
            cleaned = sentence.lower()
            for filler in ["i ", "also ", "additionally ", "furthermore ", "moreover "]:
                if cleaned.startswith(filler):
                    sentence = sentence[len(filler) :].strip()
                    break

            # Capitalize first letter
            if sentence:
                bullet_points.append(sentence[0].upper() + sentence[1:])

        return bullet_points

    def _create_experience_section(self):
        """Create the experience section of the resume."""
        if not getattr(self.personal_agent.user_profile, "work_experiences", None):
            return

        self.elements.append(
            Paragraph("PROFESSIONAL EXPERIENCE", self.styles["ResumeSectionHeader"])
        )
        # Sort experiences by start date (most recent first)
        sorted_experiences = sorted(
            getattr(self.personal_agent.user_profile, "work_experiences", []),
            key=lambda x: x.get("start_date", "1900-01-01").strftime("%Y-%m-%d"),
            reverse=True,
        )
        for exp in sorted_experiences:
            # Title, Company, Location and Date in one row
            position_text = f"<b>{exp['position']}</b>"
            if exp.get("company"):
                position_text += f", {exp['company']}"
            if exp.get("location"):
                position_text += f", {exp['location']}"

            start_date: str = self._format_date(exp.get("start_date"))
            end_date: str = self._format_date(exp.get("end_date"))
            date_text: str = f"{start_date}-{end_date}"

            experience_data: List[List[Paragraph]] = [
                [
                    Paragraph(position_text, self.styles["ResumeJobTitleBold"]),
                    Paragraph(date_text, self.styles["ResumeDate"]),
                ]
            ]

            experience_table = Table(experience_data, colWidths=[460, 100])
            experience_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (0, 0), "LEFT"),
                        ("ALIGN", (-1, -1), (-1, -1), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (0, 0), 0),  # Remove left padding for first column
                        (
                            "RIGHTPADDING",
                            (-1, -1),
                            (-1, -1),
                            0,
                        ),  # Remove right padding for last column
                    ]
                )
            )
            self.elements.append(experience_table)

            # Convert description to bullet points if it exists
            if exp.get("description"):
                additional_bullets: List[str] = self._convert_description_to_bullets(
                    exp["description"]
                )
                if additional_bullets:
                    exp.setdefault("bullet_points", []).extend(additional_bullets)

            # Bullet points
            for bullet in exp.get("bullet_points", []):
                if not bullet.startswith("•"):
                    bullet = f"• {bullet}"
                self.elements.append(Paragraph(bullet, self.styles["ResumeBullet"]))

            self.elements.append(Spacer(1, 2))

    def _score_project_relevance(self, project, job_description):
        """Score a project's relevance to the job description."""
        if not job_description:
            return 1.0  # If no job description, treat all projects as relevant

        vectorizer = CountVectorizer(stop_words="english")

        # Combine project title, description and technologies
        project_text = f"{project.get('title', '')} {project.get('description', '')} {' '.join(project.get('technologies', []))}"

        try:
            # Create document vectors
            vectors = vectorizer.fit_transform([project_text, job_description])
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            return similarity
        except Exception:
            return 0.0

    def _create_projects_section(self, job_description=None, max_projects=10):
        if not getattr(self.personal_agent.user_profile, "projects", None):
            return

        # Score and sort projects by relevance
        scored_projects: List[Tuple[float, Dict[str, Any]]] = []
        for project in getattr(self.personal_agent.user_profile, "projects", []):
            # Clean the project title by removing anything in parentheses
            title: str = project.get("title", "")
            cleaned_title = title.split("(")[0].strip()
            project["title"] = cleaned_title

            score = self._score_project_relevance(project, job_description)
            scored_projects.append((score, project))

        # Sort by score (descending) and limit to max_projects
        sorted_projects: List[Tuple[float, Dict[str, Any]]] = sorted(
            scored_projects, key=lambda x: (-x[0], x[1].get("title", ""))
        )
        relevant_projects: List[Dict[str, Any]] = [
            proj for _, proj in sorted_projects[:max_projects]
        ]

        if not relevant_projects:
            return

        self.elements.append(Paragraph("PROJECTS", self.styles["ResumeSectionHeader"]))

        for project in relevant_projects:
            # Project title and dates row
            title_text = f"<b>{project['title']}</b>"
            # TODO: Add technologies to project title
            # if project.get('technologies'):
            #     title_text += f" ({', '.join(project['technologies'])})"

            start_date: str = self._format_date(project.get("start_date"))
            end_date: str = self._format_date(project.get("end_date"))
            date_text: str = f"{start_date}-{end_date}"

            project_data: List[List[Paragraph]] = [
                [
                    Paragraph(title_text, self.styles["ResumeProjectTitle"]),
                    Paragraph(date_text, self.styles["ResumeDate"]),
                ]
            ]

            project_table = Table(project_data, colWidths=[460, 100])
            project_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (0, 0), "LEFT"),
                        ("ALIGN", (-1, -1), (-1, -1), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (0, 0), 0),  # Remove left padding for first column
                        (
                            "RIGHTPADDING",
                            (-1, -1),
                            (-1, -1),
                            0,
                        ),  # Remove right padding for last column
                    ]
                )
            )
            self.elements.append(project_table)

            # Convert description to bullet points
            if project.get("description"):
                bullets = self._convert_description_to_bullets(project["description"])
                for bullet in bullets:
                    self.elements.append(Paragraph(f"• {bullet}", self.styles["ResumeBullet"]))

            self.elements.append(Spacer(1, 2))

    def _create_certifications_section(self):
        if not getattr(self.personal_agent.user_profile, "certifications", None):
            return

        self.elements.append(Paragraph("CERTIFICATIONS", self.styles["ResumeSectionHeader"]))

        for cert in getattr(self.personal_agent.user_profile, "certifications", []):
            cert_text: str = f"{cert['name']}"
            if cert.get("issuer"):
                cert_text += f" - {cert['issuer']}"
            if cert.get("date"):
                cert_text += f" ({self._format_date(cert['date'])})"
            self.elements.append(Paragraph(cert_text, self.styles["ResumeCertification"]))

        self.elements.append(Spacer(1, 2))

    def _create_education_section(self):
        """Create the education section of the resume."""
        if not getattr(self.personal_agent.user_profile, "education", None):
            return

        self.elements.append(Paragraph("EDUCATION", self.styles["ResumeSectionHeader"]))

        for edu in getattr(self.personal_agent.user_profile, "education", []):
            edu_text: str = f"{edu['institution']}"
            if edu.get("degree"):
                edu_text += f" - {edu['degree']}"
            if edu.get("field_of_study"):
                edu_text += f" in {edu['field_of_study']}"
            if edu.get("graduation_date"):
                edu_text += f" ({self._format_date(edu['graduation_date'])})"
            self.elements.append(Paragraph(edu_text, self.styles["ResumeEducation"]))

        self.elements.append(Spacer(1, 2))

    def _create_skills_section(self, job_info: str):
        """Create the skills section of the resume."""
        if not getattr(self.personal_agent.user_profile, "skills", None):
            return

        self.elements.append(Paragraph("SKILLS", self.styles["ResumeSectionHeader"]))

        # Get unique skills and their highest proficiency level
        # Use lowercase name as key to ensure case-insensitive uniqueness
        skill_levels = {}
        for skill in getattr(self.personal_agent.user_profile, "skills", []):
            name = skill.get("name", "").strip()
            name_lower = name.lower()
            level = skill.get("level", 0)
            # Keep the version with highest proficiency, or the original case if same proficiency
            if name_lower and (
                name_lower not in skill_levels or level > skill_levels[name_lower][1]
            ):
                skill_levels[name_lower] = (name, level)  # Store original name and level

        # Use AI to analyze and score skills based on job description
        prompt = f"""
        Analyze the job description and extract relevant skills from the candidate's work experiences.
        Return a JSON array of strings containing only the relevant skill names.

        Job information:
        {job_info}
        
        Candidate's Work Experiences:
        {', '.join([f"{exp.get('position', '')} at {exp.get('company', '')}: {exp.get('description', '')}" for exp in getattr(self.personal_agent.user_profile, "work_experiences", [])])}

        ⚠️ STRICT RESPONSE FORMAT REQUIREMENTS ⚠️
        Your response must be EXACTLY in this format, with no additional text:
        ["skill_name1", "skill_name2", ...]

        Rules:
        - Only return skills that are directly mentioned in the job description
        - Only return skills that are demonstrated in the candidate's work experiences
        - Prioritize technical skills over soft skills
        - Return skills in order of relevance to the job
        - Maximum 15 skills
        - DO NOT include any explanatory text before or after the JSON array
        - DO NOT include any notes or comments
        - DO NOT include any "Here is" or similar phrases
        - ONLY return the JSON array, nothing else

        ❌ FORBIDDEN:
        1. NO introductory text
        2. NO explanatory text
        3. NO notes or comments
        4. NO "Here is" or similar phrases
        5. NO additional context

        ✅ REQUIRED:
        1. Response must start with [ and end with ]
        2. Response must be valid JSON
        3. Response must contain only the array of skill names
        4. Response must be parseable by a JSON parser
        """

        # Get AI analysis of skills
        response: str = self.google_client.generate_text(prompt)

        # Remove any extra text or whitespace
        response = response.strip()

        # Find the first '[' and last ']' to extract just the JSON array
        start_idx = response.find("[")
        end_idx = response.rfind("]")

        if start_idx == -1 or end_idx == -1:
            raise ValueError("No valid JSON array found in response")

        # Extract just the JSON array part
        json_str = response[start_idx : end_idx + 1]

        # Parse the JSON
        relevant_skills = json.loads(json_str)

        # Validate and clean the skills
        if not isinstance(relevant_skills, list):
            raise ValueError("Response is not a list")

        # Use the skills directly from the model's response
        top_skills = relevant_skills[:15]

        # Create a single line of skills
        skills_text: LiteralString = " | ".join(top_skills)
        self.elements.append(Paragraph(skills_text, self.styles["ResumeBullet"]))
        self.elements.append(Spacer(1, 2))

    def tailor_to_job(self, job_info: str = "") -> None:
        """
        Tailors the resume content based on the job description by:
        1. Analyzing keywords in job description
        2. Reordering work experiences based on relevance
        3. Highlighting matching skills
        4. Adjusting professional summary

        Args:
            job_info (str): The job information to tailor against
        """
        # Prepare comprehensive prompt for tailoring the summary
        prompt: str = f"""
        You are a professional resume writer. Create a tailored professional summary that highlights the candidate's relevant experience and skills for this job.

        Job Description:
        {job_info}
        
        Candidate Background Summary:
        {self.personal_agent.get_background_str()}   
                     
        Applicant Skills:
        {', '.join([skill.get('name', '') for skill in getattr(self.personal_agent.user_profile, "skills", [])])}

        Instructions:
        1. Analyze the job description and identify key requirements and skills
        2. Review the candidate's background, GitHub profile, and identify relevant experience
        3. Create a compelling 2-3 sentence summary that:
           - Maintains the candidate's authentic voice and style
           - Highlights relevant experience and skills from their background
           - Emphasizes alignment with the job requirements
           - Uses specific examples from their work history and GitHub contributions
           - Incorporates relevant technical skills naturally
        4. Keep the tone professional but engaging
        5. Focus on achievements and impact rather than just responsibilities

        ⚠️ STRICT RESPONSE FORMAT REQUIREMENTS ⚠️
        Your response must be EXACTLY in this format, with no additional text:
        {{"summary": "Your tailored summary here",
        "skills": ["skill1", "skill2", ...],
        "projects": ["project1", "project2", ...]}}


        Remember: Your entire response should be a single JSON object, nothing more, nothing less.
        """
        # Get tailored summary from Ollama
        response: str = self.google_client.generate_text(prompt)
        response_dict = json.loads(response)
        self.professional_summary = response_dict["summary"].strip()
        self.projects = response_dict["projects"].strip()
        self.skills = response_dict["skills"].strip()

    def build(self, output_path, job_info: str) -> None:
        """Build the resume PDF, optionally tailoring it to a job description."""

        # Clear any existing elements
        self.elements = []

        self.tailor_to_job(job_info)

        # Create header
        self._create_header()
        # Add professional summary
        if self.professional_summary:
            self.elements.append(
                Paragraph("PROFESSIONAL SUMMARY", self.styles["ResumeSectionHeader"])
            )
            self.elements.append(Paragraph(self.professional_summary, self.styles["ResumeSummary"]))

        # Add skills section
        self._create_skills_section(job_info)
        # Add experience section
        self._create_experience_section()
        # Add relevant projects section
        self._create_projects_section(job_info)
        # Add certifications section
        self._create_certifications_section()
        # Add education section
        self._create_education_section()
        # Create PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=20,
            leftMargin=20,
            topMargin=15,
            bottomMargin=20,
        )
        doc.build(self.elements)

    def generate_tailored_resume(
        self,
        job_info: str,
    ) -> BytesIO:
        """
        Generate a tailored resume for a specific job.

        Args:
            job_title (str): The job title
            company (str): The company name
            job_description (str): The job description
            required_skills (List[str]): List of required skills

        Returns:
            BytesIO: The generated resume PDF
        """
        # Create a buffer for the PDF
        buffer = BytesIO()

        # Build the resume
        self.build(buffer, job_info)

        # Reset buffer position
        buffer.seek(0)

        return buffer
