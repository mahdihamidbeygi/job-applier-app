from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from datetime import datetime
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter

class ResumeComposition:
    def __init__(self, user_data):
        self.user_data = self._convert_to_dict(user_data)
        print(self.user_data['phone'])
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        self.elements = []
        
    def _convert_to_dict(self, user_data):
        """Convert UserProfile model instance to dictionary format"""
        if hasattr(user_data, 'user'):  # If it's a UserProfile model instance
            return {
                'name': user_data.user.get_full_name() or user_data.user.username,
                'email': user_data.user.email,
                'phone': ''.join(char for char in getattr(user_data, 'phone', '') if char.isdigit() or char == '+'),
                'location': getattr(user_data, 'location', ''),
                'linkedin': getattr(user_data, 'linkedin', ''),
                'github': getattr(user_data, 'github', ''),
                'title': getattr(user_data, 'title', ''),
                'headline': getattr(user_data, 'headline', ''),
                'professional_summary': getattr(user_data, 'professional_summary', ''),
                'work_experience': [
                    {
                        'company': exp.company,
                        'position': exp.position,
                        'location': exp.location,
                        'start_date': exp.start_date.strftime('%Y-%m-%d') if exp.start_date else None,
                        'end_date': exp.end_date.strftime('%Y-%m-%d') if exp.end_date else None,
                        'description': exp.description,
                        'bullet_points': exp.achievements.split('\n') if exp.achievements else []
                    }
                    for exp in user_data.work_experiences.all()
                ],
                'projects': [
                    {
                        'title': proj.title,
                        'description': proj.description,
                        'technologies': proj.technologies.split(', ') if proj.technologies else [],
                        'start_date': proj.start_date.strftime('%Y-%m-%d') if proj.start_date else None,
                        'end_date': proj.end_date.strftime('%Y-%m-%d') if proj.end_date else None
                    }
                    for proj in user_data.projects.all()
                ],
                'certifications': [
                    {
                        'name': cert.name,
                        'issuer': cert.issuer,
                        'date': cert.issue_date.strftime('%Y-%m-%d') if cert.issue_date else None
                    }
                    for cert in user_data.certifications.all()
                ],
                'education': [
                    {
                        'school': edu.institution,
                        'degree': edu.degree,
                        'field_of_study': edu.field_of_study,
                        'graduation_date': edu.end_date.strftime('%Y-%m-%d') if edu.end_date else None
                    }
                    for edu in user_data.education.all()
                ],
                'skills': [
                    {
                        'name': skill.name,
                        'level': skill.proficiency
                    }
                    for skill in user_data.skills.all()
                ]
            }
        return user_data  # If it's already a dictionary, return as is

    def _setup_styles(self):
        # Header style
        self.styles.add(ParagraphStyle(
            name='ResumeHeader',
            fontName='Helvetica-Bold',
            fontSize=24,
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        # Job title bold style
        self.styles.add(ParagraphStyle(
            name='ResumeJobTitleBold',
            fontName='Helvetica-Bold',
            fontSize=12,
            leftIndent=4,  # Very slight indent for main line
            firstLineIndent=0,
            spaceAfter=2
        ))
        
        # Contact info style
        self.styles.add(ParagraphStyle(
            name='ResumeContact',
            fontName='Helvetica',
            fontSize=12,
            spaceAfter=10,
            leading=15,
            alignment=TA_CENTER
        ))
        
        # Role title style
        self.styles.add(ParagraphStyle(
            name='ResumeRole',
            fontName='Helvetica-Bold',
            fontSize=16,
            spaceAfter=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50')
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='ResumeSectionHeader',
            fontName='Helvetica-Bold',
            fontSize=16,
            spaceBefore=10,
            spaceAfter=10,
            leftIndent=0,
            textColor=colors.HexColor('#2c3e50')
        ))
        
        # Company name style
        self.styles.add(ParagraphStyle(
            name='ResumeCompany',
            fontName='Helvetica-Bold',
            fontSize=14,
            spaceAfter=2
        ))
        
        # Job title style
        self.styles.add(ParagraphStyle(
            name='ResumeJobTitle',
            fontName='Helvetica',
            fontSize=13,
            spaceAfter=2
        ))
        
        # Date style
        self.styles.add(ParagraphStyle(
            name='ResumeDate',
            fontName='Helvetica',
            fontSize=11,
            textColor=colors.gray
        ))
        
        # Location style
        self.styles.add(ParagraphStyle(
            name='ResumeLocation',
            fontName='Helvetica',
            fontSize=11,
            textColor=colors.gray,
            alignment=TA_RIGHT
        ))
        
        # Bullet point style with increased indent
        self.styles.add(ParagraphStyle(
            name='ResumeBullet',
            fontName='Helvetica',
            fontSize=12,
            leftIndent=8,  # More indent than the main line
            firstLineIndent=0,
            spaceAfter=2
        ))
        
        # Summary style
        self.styles.add(ParagraphStyle(
            name='ResumeSummary',
            fontName='Helvetica',
            fontSize=12,
            spaceAfter=10,
            alignment=4,
            leading=16
        ))
        
        # Project title style
        self.styles.add(ParagraphStyle(
            name='ResumeProjectTitle',
            fontName='Helvetica-Bold',
            fontSize=13,
            spaceAfter=2
        ))
        
        # Project description style
        self.styles.add(ParagraphStyle(
            name='ResumeProjectDesc',
            fontName='Helvetica',
            fontSize=12,
            spaceAfter=2,
            leading=14,

        ))
        
        # Education style
        self.styles.add(ParagraphStyle(
            name='ResumeEducation',
            fontName='Helvetica',
            fontSize=12,
            spaceAfter=2
        ))
        
        # Certification style
        self.styles.add(ParagraphStyle(
            name='ResumeCertification',
            fontName='Helvetica',
            fontSize=12,
            spaceAfter=2
        ))

    def _create_header(self):
        # Name
        self.elements.append(Paragraph(self.user_data['headline'], self.styles['ResumeHeader']))

        # Title/Role
        if self.user_data.get('title'):
            self.elements.append(Paragraph(self.user_data['title'], self.styles['ResumeRole']))

        # Contact info
        contact_info = []
        if self.user_data.get('email'):
            contact_info.append(self.user_data['email'])
        if self.user_data.get('phone'):
            phone = self.user_data['phone']
            if phone.startswith('+'):
                # Format as +X XXX XXX XXXX
                formatted_phone = f"{phone[:2]} {phone[2:5]} {phone[5:8]} {phone[8:]}"
            else:
                # Format as XXX XXX XXXX
                formatted_phone = f"{phone[:3]} {phone[3:6]} {phone[6:]}"
            contact_info.append(formatted_phone)
        if self.user_data.get('location'):
            contact_info.append(self.user_data['location'])
        if self.user_data.get('linkedin'):
            contact_info.append(self.user_data['linkedin'])
        if self.user_data.get('github'):
            contact_info.append(self.user_data['github'])
            
        if contact_info:
            self.elements.append(Paragraph(' | '.join(contact_info), self.styles['ResumeContact']))
            
        self.elements.append(Spacer(1, 5))

    def _format_date(self, date_str):
        if not date_str:
            return "Present"
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            return date.strftime("%m/%Y").lstrip('0')  # Remove leading zero from month
        except ValueError:
            return date_str

    def _convert_description_to_bullets(self, description):
        """Convert a paragraph description into bullet points."""
        if not description:
            return []
            
        # Split on periods and semicolons, common sentence separators
        sentences = [s.strip() for s in description.replace(';', '.').split('.') if s.strip()]
        
        # Convert each sentence into an action-oriented bullet point
        bullet_points = []
        for sentence in sentences:
            # Remove common filler words at the start
            cleaned = sentence.lower()
            for filler in ['i ', 'also ', 'additionally ', 'furthermore ', 'moreover ']:
                if cleaned.startswith(filler):
                    sentence = sentence[len(filler):].strip()
                    break
            
            # Capitalize first letter
            if sentence:
                bullet_points.append(sentence[0].upper() + sentence[1:])
                
        return bullet_points

    def _create_experience_section(self):
        if not self.user_data.get('work_experience'):
            return
            
        self.elements.append(Paragraph("PROFESSIONAL EXPERIENCE", self.styles['ResumeSectionHeader']))
        
        # Sort experiences by start date (most recent first)
        sorted_experiences = sorted(
            self.user_data['work_experience'],
            key=lambda x: datetime.strptime(x.get('start_date', '1900-01-01'), '%Y-%m-%d'),
            reverse=True
        )
        
        for exp in sorted_experiences:
            # Title, Company, Location and Date in one row
            position_text = f"<b>{exp['position']}</b>"
            if exp.get('company'):
                position_text += f", {exp['company']}"
            if exp.get('location'):
                position_text += f", {exp['location']}"
                
            start_date = self._format_date(exp.get('start_date'))
            end_date = self._format_date(exp.get('end_date'))
            date_text = f"{start_date}-{end_date}"
            
            experience_data = [
                [Paragraph(position_text, self.styles['ResumeJobTitleBold']),
                 Paragraph(date_text, self.styles['ResumeDate'])]
            ]
            
            experience_table = Table(experience_data, colWidths=[460, 100])
            experience_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (-1, -1), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (0, 0), 0),  # Remove left padding for first column
                ('RIGHTPADDING', (-1, -1), (-1, -1), 0),  # Remove right padding for last column
            ]))
            self.elements.append(experience_table)
            
            # Convert description to bullet points if it exists
            if exp.get('description'):
                additional_bullets = self._convert_description_to_bullets(exp['description'])
                if additional_bullets:
                    exp.setdefault('bullet_points', []).extend(additional_bullets)
            
            # Bullet points
            for bullet in exp.get('bullet_points', []):
                if not bullet.startswith('•'):
                    bullet = f"• {bullet}"
                self.elements.append(Paragraph(bullet, self.styles['ResumeBullet']))
            
            self.elements.append(Spacer(1, 2))

    def _score_project_relevance(self, project, job_description):
        """Score a project's relevance to the job description."""
        if not job_description:
            return 1.0  # If no job description, treat all projects as relevant
            
        vectorizer = CountVectorizer(stop_words='english')
        
        # Combine project title, description and technologies
        project_text = f"{project.get('title', '')} {project.get('description', '')} {' '.join(project.get('technologies', []))}"
        
        try:
            # Create document vectors
            vectors = vectorizer.fit_transform([project_text, job_description])
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            return similarity
        except Exception:
            return 0.0

    def _create_projects_section(self, job_description=None, max_projects=3):
        if not self.user_data.get('projects'):
            return
            
        # Score and sort projects by relevance
        scored_projects = []
        for project in self.user_data['projects']:
            score = self._score_project_relevance(project, job_description)
            scored_projects.append((score, project))
            
        # Sort by score (descending) and limit to max_projects
        sorted_projects = sorted(scored_projects, key=lambda x: (-x[0], x[1].get('title', '')))
        relevant_projects = [proj for _, proj in sorted_projects[:max_projects]]
        
        if not relevant_projects:
            return
            
        self.elements.append(Paragraph("PROJECTS", self.styles['ResumeSectionHeader']))
        
        for project in relevant_projects:
            # Project title and dates row
            title_text = f"<b>{project['title']}</b>"
            if project.get('technologies'):
                title_text += f" ({', '.join(project['technologies'])})"
                
            start_date = self._format_date(project.get('start_date'))
            end_date = self._format_date(project.get('end_date'))
            date_text = f"{start_date}-{end_date}"
            
            project_data = [
                [Paragraph(title_text, self.styles['ResumeProjectTitle']),
                 Paragraph(date_text, self.styles['ResumeDate'])]
            ]
            
            project_table = Table(project_data, colWidths=[460, 100])
            project_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (-1, -1), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (0, 0), 0),  # Remove left padding for first column
                ('RIGHTPADDING', (-1, -1), (-1, -1), 0),  # Remove right padding for last column
            ]))
            self.elements.append(project_table)
            
            # Convert description to bullet points
            if project.get('description'):
                bullets = self._convert_description_to_bullets(project['description'])
                for bullet in bullets:
                    self.elements.append(Paragraph(f"• {bullet}", self.styles['ResumeBullet']))
            
            self.elements.append(Spacer(1, 2))

    def _create_certifications_section(self):
        if not self.user_data.get('certifications'):
            return
            
        self.elements.append(Paragraph("CERTIFICATIONS", self.styles['ResumeSectionHeader']))
        
        for cert in self.user_data['certifications']:
            cert_text = f"{cert['name']}"
            if cert.get('issuer'):
                cert_text += f" - {cert['issuer']}"
            if cert.get('date'):
                cert_text += f" ({self._format_date(cert['date'])})"
            self.elements.append(Paragraph(cert_text, self.styles['ResumeCertification']))
            
        self.elements.append(Spacer(1, 2))

    def _create_education_section(self):
        if not self.user_data.get('education'):
            return
            
        self.elements.append(Paragraph("EDUCATION", self.styles['ResumeSectionHeader']))
        
        for edu in self.user_data['education']:
            edu_text = f"{edu['school']}"
            if edu.get('degree'):
                edu_text += f" - {edu['degree']}"
            if edu.get('field_of_study'):
                edu_text += f" in {edu['field_of_study']}"
            if edu.get('graduation_date'):
                edu_text += f" ({self._format_date(edu['graduation_date'])})"
            self.elements.append(Paragraph(edu_text, self.styles['ResumeEducation']))
            
        self.elements.append(Spacer(1, 2))

    def _create_skills_section(self):
        if not self.user_data.get('skills'):
            return
            
        self.elements.append(Paragraph("SKILLS", self.styles['ResumeSectionHeader']))
        
        # Get unique skills and their highest proficiency level
        skill_levels = {}
        for skill in self.user_data['skills']:
            name = skill.get('name', '').strip()
            level = skill.get('level', 0)
            if name and (name not in skill_levels or level > skill_levels[name]):
                skill_levels[name] = level
        
        # Sort skills by proficiency level (descending) and name
        sorted_skills = sorted(skill_levels.items(), key=lambda x: (-x[1], x[0]))
        
        # Take top skills (around 10-15 most relevant)
        top_skills = [skill for skill, _ in sorted_skills[:15]]
        
        # Create a single line of skills
        skills_text = " | ".join(top_skills)
        self.elements.append(Paragraph(skills_text, self.styles['ResumeBullet']))
        
        self.elements.append(Spacer(1, 2))

    def tailor_to_job(self, job_description):
        """
        Tailors the resume content based on the job description by:
        1. Analyzing keywords in job description
        2. Reordering work experiences based on relevance
        3. Highlighting matching skills
        4. Adjusting professional summary
        
        Args:
            job_description (str): The job description to tailor against
        """
        # Extract keywords from job description
        vectorizer = CountVectorizer(stop_words='english')
        job_matrix = vectorizer.fit_transform([job_description])
        job_terms = vectorizer.get_feature_names_out()
        
        # Score work experiences based on keyword matches
        scored_experiences = []
        for exp in self.user_data.get('work_experience', []):
            exp_text = f"{exp.get('position', '')} {exp.get('description', '')} {' '.join(exp.get('bullet_points', []))}"
            exp_matrix = vectorizer.transform([exp_text])
            similarity = cosine_similarity(job_matrix, exp_matrix)[0][0]
            scored_experiences.append((similarity, exp))
        
        # Sort experiences by relevance
        self.user_data['work_experience'] = [
            exp for _, exp in sorted(scored_experiences, 
                                   key=lambda x: (-x[0], x[1].get('position', '')))
        ]
        
        # Identify key skills from job description
        job_skills = set(job_terms).intersection(
            skill.get('name', '').lower() 
            for skill in self.user_data.get('skills', [])
        )
        
        # Reorder skills to prioritize matching ones
        scored_skills = []
        for skill in self.user_data.get('skills', []):
            score = 1.0 if skill.get('name', '').lower() in job_skills else 0.0
            scored_skills.append((score, skill))
        
        self.user_data['skills'] = [
            skill for _, skill in sorted(scored_skills, 
                                      key=lambda x: (-x[0], x[1].get('name', '')))
        ]
        
        # Update professional summary to include key terms
        if self.user_data.get('professional_summary'):
            summary_matrix = vectorizer.transform([self.user_data['professional_summary']])
            summary_terms = set(vectorizer.inverse_transform(summary_matrix)[0])
            missing_key_terms = set(job_terms) - summary_terms
            
            if missing_key_terms:
                key_terms_str = ', '.join(list(missing_key_terms)[:3])  # Top 3 missing terms
                self.user_data['professional_summary'] = (
                    f"{self.user_data['professional_summary']} "
                    f"Experienced in {key_terms_str} and related technologies."
                )

        # Reorder projects based on relevance
        scored_projects = []
        for proj in self.user_data.get('projects', []):
            proj_text = f"{proj.get('title', '')} {proj.get('description', '')} {' '.join(proj.get('technologies', []))}"
            proj_matrix = vectorizer.transform([proj_text])
            similarity = cosine_similarity(job_matrix, proj_matrix)[0][0]
            scored_projects.append((similarity, proj))
        
        self.user_data['projects'] = [
            proj for _, proj in sorted(scored_projects, 
                                    key=lambda x: (-x[0], x[1].get('title', '')))
        ]

    def build(self, output_path, job_description=None):
        """Build the resume PDF, optionally tailoring it to a job description."""

        if job_description:
            self.tailor_to_job(job_description)
        
        # Create header
        self._create_header()
        
        # Add professional summary
        if self.user_data.get('professional_summary'):
            self.elements.append(Paragraph("PROFESSIONAL SUMMARY", self.styles['ResumeSectionHeader']))
            self.elements.append(Paragraph(self.user_data['professional_summary'], 
                                         self.styles['ResumeSummary']))
        
        # Add skills section
        self._create_skills_section()
        
        # Add experience section
        self._create_experience_section()
        
        # Add relevant projects section
        self._create_projects_section(job_description)
        
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
            bottomMargin=20
        )
        doc.build(self.elements)