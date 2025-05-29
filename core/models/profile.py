"""
User profile models.
"""

from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from .base import TimestampMixin


class UserProfile(TimestampMixin):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Basic Information
    name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Full name - alternative to user.first_name and user.last_name",
    )
    title = models.CharField(max_length=100, blank=True, help_text="Professional title or role")

    # Contact Information
    phone = models.CharField(max_length=20, blank=True)

    # Location Information (consolidated)
    address = models.TextField(blank=True, help_text="Full address")
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Online Presence (consolidated)
    website = models.URLField(blank=True, help_text="Personal website URL")
    github_url = models.URLField(blank=True, help_text="GitHub profile URL")
    linkedin_url = models.URLField(blank=True, help_text="LinkedIn profile URL")

    # Professional Information
    headline = models.CharField(max_length=100, blank=True, help_text="Professional headline")
    professional_summary = models.TextField(blank=True, help_text="Professional summary or bio")
    current_position = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)

    # Resume
    resume = models.FileField(upload_to="resumes/", blank=True)
    parsed_resume_data = models.JSONField(default=dict, blank=True)

    # GitHub Data
    github_data = models.JSONField(default=dict, blank=True)
    last_github_refresh = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    def save(self, *args, **kwargs):
        # Sync user.email with email data if necessary
        if not self.user.email and self.user.email != self.user.username:
            self.user.email = self.user.username
            self.user.save(update_fields=["email"])

        # Sync name with user first_name and last_name if necessary
        if self.name and not (self.user.first_name or self.user.last_name):
            name_parts = self.name.split(" ", 1)
            if len(name_parts) > 0:
                self.user.first_name = name_parts[0]
                if len(name_parts) > 1:
                    self.user.last_name = name_parts[1]
                self.user.save(update_fields=["first_name", "last_name"])

        super().save(*args, **kwargs)

    @property
    def email(self):
        """Return the user's email address"""
        return self.user.email

    @property
    def full_name(self):
        """Return the user's full name or username if no name is set"""
        if self.name:
            return self.name
        if self.user.first_name or self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}".strip()
        return self.user.username

    @property
    def location(self):
        """Return the formatted location string"""
        location_parts = []
        if self.city:
            location_parts.append(self.city)
        if self.state:
            location_parts.append(self.state)
        if self.country and (not self.city or not self.state):
            location_parts.append(self.country)
        return ", ".join(location_parts)

    @property
    def years_of_experience(self):
        """Calculate total years of experience from work experiences"""
        if not self.work_experiences.exists():
            return 0

        total_months = 0
        for exp in self.work_experiences.all():
            start_date = exp.start_date
            end_date = (
                exp.end_date or date.today()
            )  # Use today's date if end_date is None (current job)

            # Calculate months between dates
            delta = relativedelta(end_date, start_date)
            months = delta.years * 12 + delta.months

            total_months += months

        # Convert total months to years (rounded to 1 decimal place)
        return round(total_months / 12, 1)

    def get_all_user_info(self):
        """
        Returns a comprehensive dictionary containing all user information,
        including all related data (work experiences, education, projects, etc.)

        Returns:
            dict: Complete user information
        """
        info = {
            # Basic info
            "id": self.user.id,
            "username": self.user.username,
            "email": self.email,
            "name": self.name,
            "full_name": self.full_name,
            "title": self.title,
            "phone": self.phone,
            # Location
            "location": self.location,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "postal_code": self.postal_code,
            # Online presence
            "website": self.website,
            "github_url": self.github_url,
            "linkedin_url": self.linkedin_url,
            # Professional info
            "headline": self.headline,
            "professional_summary": self.professional_summary,
            "current_position": self.current_position,
            "company": self.company,
            "years_of_experience": self.years_of_experience,
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_github_refresh": (
                self.last_github_refresh.isoformat() if self.last_github_refresh else None
            ),
            # Resume data
            "has_resume": bool(self.resume),
            "resume_url": self.resume.url if self.resume else None,
            "parsed_resume_data": self.parsed_resume_data,
            # GitHub data
            "github_data": self.github_data,
        }

        # Work experiences
        if hasattr(self, "work_experiences"):
            info["work_experiences"] = []
            for exp in self.work_experiences.all():
                info["work_experiences"].append(
                    {
                        "id": exp.id,
                        "company": exp.company,
                        "position": exp.position,
                        "location": exp.location,
                        "start_date": exp.start_date.isoformat() if exp.start_date else None,
                        "end_date": exp.end_date.isoformat() if exp.end_date else None,
                        "current": exp.current,
                        "description": exp.description,
                        "achievements": exp.achievements,
                        "technologies": exp.technologies,
                        "order": exp.order,
                        "created_at": exp.created_at.isoformat() if exp.created_at else None,
                        "updated_at": exp.updated_at.isoformat() if exp.updated_at else None,
                    }
                )

        # Education
        if hasattr(self, "education"):
            info["education"] = []
            for edu in self.education.all():
                info["education"].append(
                    {
                        "id": edu.id,
                        "institution": edu.institution,
                        "degree": edu.degree,
                        "field_of_study": edu.field_of_study,
                        "start_date": edu.start_date.isoformat() if edu.start_date else None,
                        "end_date": edu.end_date.isoformat() if edu.end_date else None,
                        "current": edu.current,
                        "gpa": float(edu.gpa) if edu.gpa else None,
                        "achievements": edu.achievements,
                        "order": edu.order,
                        "created_at": edu.created_at.isoformat() if edu.created_at else None,
                        "updated_at": edu.updated_at.isoformat() if edu.updated_at else None,
                    }
                )

        # Projects
        if hasattr(self, "projects"):
            info["projects"] = []
            for proj in self.projects.all():
                info["projects"].append(
                    {
                        "id": proj.id,
                        "title": proj.title,
                        "description": proj.description,
                        "start_date": proj.start_date.isoformat() if proj.start_date else None,
                        "end_date": proj.end_date.isoformat() if proj.end_date else None,
                        "current": proj.current,
                        "technologies": proj.technologies,
                        "github_url": proj.github_url,
                        "live_url": proj.live_url,
                        "order": proj.order,
                        "created_at": proj.created_at.isoformat() if proj.created_at else None,
                        "updated_at": proj.updated_at.isoformat() if proj.updated_at else None,
                    }
                )

        # Skills
        if hasattr(self, "skills"):
            info["skills"] = []
            # Group skills by category
            skills_by_category = {}

            for skill in self.skills.all():
                skill_info = {
                    "id": skill.id,
                    "name": skill.name,
                    "category": skill.category,
                    "category_display": dict(Skill.SKILL_CATEGORIES).get(
                        skill.category, skill.category
                    ),
                    "proficiency": skill.proficiency,
                    "proficiency_display": dict(Skill.PROFICIENCY_CHOICES).get(
                        skill.proficiency, ""
                    ),
                    "order": skill.order,
                    "created_at": skill.created_at.isoformat() if skill.created_at else None,
                    "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
                }

                info["skills"].append(skill_info)

                # Also organize skills by category for easier access
                if skill.category not in skills_by_category:
                    skills_by_category[skill.category] = []
                skills_by_category[skill.category].append(skill_info)

            info["skills_by_category"] = skills_by_category

        # Certifications
        if hasattr(self, "certifications"):
            info["certifications"] = []
            for cert in self.certifications.all():
                info["certifications"].append(
                    {
                        "id": cert.id,
                        "name": cert.name,
                        "issuer": cert.issuer,
                        "issue_date": cert.issue_date.isoformat() if cert.issue_date else None,
                        "expiry_date": cert.expiry_date.isoformat() if cert.expiry_date else None,
                        "credential_id": cert.credential_id,
                        "credential_url": cert.credential_url,
                        "order": cert.order,
                        "created_at": cert.created_at.isoformat() if cert.created_at else None,
                        "updated_at": cert.updated_at.isoformat() if cert.updated_at else None,
                    }
                )

        # Publications
        if hasattr(self, "publications"):
            info["publications"] = []
            for pub in self.publications.all():
                info["publications"].append(
                    {
                        "id": pub.id,
                        "title": pub.title,
                        "authors": pub.authors,
                        "publication_date": (
                            pub.publication_date.isoformat() if pub.publication_date else None
                        ),
                        "publisher": pub.publisher,
                        "journal": pub.journal,
                        "doi": pub.doi,
                        "url": pub.url,
                        "abstract": pub.abstract,
                        "order": pub.order,
                        "created_at": pub.created_at.isoformat() if pub.created_at else None,
                        "updated_at": pub.updated_at.isoformat() if pub.updated_at else None,
                    }
                )

        # Return the complete information dictionary
        return info

    def get_formatted_info(self):
        """
        Extends the base TimestampMixin.get_formatted_info method with profile-specific formatting.

        Returns:
            str: Formatted string with all user profile information
        """
        # Get the base formatted information from TimestampMixin
        base_info = super().get_formatted_info()

        # Add additional profile-specific sections
        additional_sections = []

        # Add user information section
        additional_sections.append("\nUSER ACCOUNT INFORMATION")
        additional_sections.append("-" * 22)
        additional_sections.append(f"Username: {self.user.username}")
        additional_sections.append(f"Email: {self.email}")
        additional_sections.append(f"Full Name: {self.full_name}")

        # Add professional information
        if self.headline or self.professional_summary or self.current_position or self.company:
            additional_sections.append("\nPROFESSIONAL DETAILS")
            additional_sections.append("-" * 19)
            if self.headline:
                additional_sections.append(f"Headline: {self.headline}")
            if self.professional_summary:
                additional_sections.append(f"Summary: {self.professional_summary}")
            if self.current_position or self.company:
                position_info = []
                if self.current_position:
                    position_info.append(self.current_position)
                if self.company:
                    position_info.append(f"at {self.company}")
                additional_sections.append(f"Current Position: {' '.join(position_info)}")
            if hasattr(self, "work_experiences") and self.work_experiences.exists():
                additional_sections.append(f"Years of Experience: {self.years_of_experience}")

        # Add contact and location information
        contact_parts = []
        if self.phone:
            contact_parts.append(f"Phone: {self.phone}")
        if self.location:
            contact_parts.append(f"Location: {self.location}")
        if contact_parts:
            additional_sections.append("\nCONTACT INFORMATION")
            additional_sections.append("-" * 19)
            additional_sections.extend(contact_parts)
            if self.address:
                additional_sections.append(f"Address: {self.address}")

        # Add online presence
        online_parts = []
        if self.website:
            online_parts.append(f"Website: {self.website}")
        if self.github_url:
            online_parts.append(f"GitHub: {self.github_url}")
        if self.linkedin_url:
            online_parts.append(f"LinkedIn: {self.linkedin_url}")
        if online_parts:
            additional_sections.append("\nONLINE PRESENCE")
            additional_sections.append("-" * 15)
            additional_sections.extend(online_parts)

        # Combine base info with additional sections
        return base_info + "\n" + "\n".join(additional_sections)

    def get_all_user_info_formatted(self):
        """
        Returns a formatted string with all user information,
        including all related data (work experiences, education, projects, etc.)

        Returns:
            str: Formatted string with all user information
        """
        # Get all user data as a dictionary
        info = self.get_all_user_info()

        # Format the output
        lines = []

        # Personal information
        lines.append("PERSONAL INFORMATION")
        lines.append("=" * 20)
        lines.append(f"Name: {info['full_name']}")
        lines.append(f"Username: {info['username']}")
        lines.append(f"Email: {info['email']}")
        if info["title"]:
            lines.append(f"Title: {info['title']}")
        if info["phone"]:
            lines.append(f"Phone: {info['phone']}")
        if info["location"]:
            lines.append(f"Location: {info['location']}")
        if info["address"]:
            lines.append(f"Address: {info['address']}")
        lines.append("")

        # Professional information
        lines.append("PROFESSIONAL INFORMATION")
        lines.append("=" * 25)
        if info["headline"]:
            lines.append(f"Headline: {info['headline']}")
        if info["professional_summary"]:
            lines.append(f"Summary: {info['professional_summary']}")
        if info["current_position"] or info["company"]:
            position_text = ""
            if info["current_position"]:
                position_text += info["current_position"]
            if info["company"]:
                position_text += f" at {info['company']}"
            lines.append(f"Current Position: {position_text}")
        lines.append(f"Years of Experience: {info['years_of_experience']}")
        lines.append("")

        # Work experience
        if "work_experiences" in info and info["work_experiences"]:
            lines.append("WORK EXPERIENCE")
            lines.append("=" * 15)
            for exp in info["work_experiences"]:
                date_range = ""
                if exp["start_date"]:
                    date_range = f"{exp['start_date'][:7]}"  # Just the YYYY-MM part
                    if exp["current"]:
                        date_range += " - Present"
                    elif exp["end_date"]:
                        date_range += f" - {exp['end_date'][:7]}"

                lines.append(f"{exp['position']} at {exp['company']} ({date_range})")
                if exp["location"]:
                    lines.append(f"Location: {exp['location']}")
                lines.append(f"{exp['description']}")
                if exp["achievements"]:
                    lines.append(f"Achievements: {exp['achievements']}")
                if exp["technologies"]:
                    lines.append(f"Technologies: {exp['technologies']}")
                lines.append("")

        # Education
        if "education" in info and info["education"]:
            lines.append("EDUCATION")
            lines.append("=" * 9)
            for edu in info["education"]:
                date_range = ""
                if edu["start_date"]:
                    date_range = f"{edu['start_date'][:7]}"
                    if edu["current"]:
                        date_range += " - Present"
                    elif edu["end_date"]:
                        date_range += f" - {edu['end_date'][:7]}"

                lines.append(f"{edu['degree']} in {edu['field_of_study']}")
                lines.append(f"{edu['institution']} ({date_range})")
                if edu["gpa"]:
                    lines.append(f"GPA: {edu['gpa']}")
                if edu["achievements"]:
                    lines.append(f"Achievements: {edu['achievements']}")
                lines.append("")

        # Projects
        if "projects" in info and info["projects"]:
            lines.append("PROJECTS")
            lines.append("=" * 8)
            for proj in info["projects"]:
                date_range = ""
                if proj["start_date"]:
                    date_range = f"{proj['start_date'][:7]}"
                    if proj["current"]:
                        date_range += " - Present"
                    elif proj["end_date"]:
                        date_range += f" - {proj['end_date'][:7]}"

                lines.append(f"{proj['title']} ({date_range})")
                lines.append(f"{proj['description']}")
                if proj["technologies"]:
                    lines.append(f"Technologies: {proj['technologies']}")
                if proj["github_url"]:
                    lines.append(f"GitHub: {proj['github_url']}")
                if proj["live_url"]:
                    lines.append(f"Live URL: {proj['live_url']}")
                lines.append("")

        # Skills
        if "skills_by_category" in info and info["skills_by_category"]:
            lines.append("SKILLS")
            lines.append("=" * 6)

            for category, skills in info["skills_by_category"].items():
                category_display = skills[0]["category_display"]
                skill_names = [f"{s['name']} ({s['proficiency_display']})" for s in skills]
                lines.append(f"{category_display}: {', '.join(skill_names)}")
            lines.append("")

        # Certifications
        if "certifications" in info and info["certifications"]:
            lines.append("CERTIFICATIONS")
            lines.append("=" * 14)
            for cert in info["certifications"]:
                date_info = ""
                if cert["issue_date"]:
                    date_info = f"Issued: {cert['issue_date'][:7]}"
                    if cert["expiry_date"]:
                        date_info += f", Expires: {cert['expiry_date'][:7]}"

                lines.append(f"{cert['name']} - {cert['issuer']} ({date_info})")
                if cert["credential_id"]:
                    lines.append(f"Credential ID: {cert['credential_id']}")
                if cert["credential_url"]:
                    lines.append(f"Credential URL: {cert['credential_url']}")
                lines.append("")

        # Publications
        if "publications" in info and info["publications"]:
            lines.append("PUBLICATIONS")
            lines.append("=" * 12)
            for pub in info["publications"]:
                lines.append(f"{pub['title']}")
                lines.append(f"Authors: {pub['authors']}")
                pub_date = (
                    f"Published: {pub['publication_date'][:7]}" if pub["publication_date"] else ""
                )
                lines.append(f"{pub_date} in {pub['publisher']}")
                if pub["journal"]:
                    lines.append(f"Journal: {pub['journal']}")
                if pub["doi"]:
                    lines.append(f"DOI: {pub['doi']}")
                if pub["url"]:
                    lines.append(f"URL: {pub['url']}")
                if pub["abstract"]:
                    lines.append(f"Abstract: {pub['abstract']}")
                lines.append("")

        # Online presence
        lines.append("ONLINE PRESENCE")
        lines.append("=" * 15)
        if info["website"]:
            lines.append(f"Website: {info['website']}")
        if info["github_url"]:
            lines.append(f"GitHub: {info['github_url']}")
        if info["linkedin_url"]:
            lines.append(f"LinkedIn: {info['linkedin_url']}")

        # Return the formatted output
        return "\n".join(lines)


class WorkExperience(TimestampMixin):
    profile = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="work_experiences"
    )
    company = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True, blank=True)
    current = models.BooleanField(default=False)
    description = models.TextField(null=True)
    achievements = models.TextField(blank=True, null=True)
    technologies = models.TextField(blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-start_date", "-order"]

    def __str__(self):
        return f"{self.position} at {self.company}"


class Project(TimestampMixin):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    current = models.BooleanField(default=False)
    technologies = models.TextField(null=True, blank=True)
    github_url = models.URLField(null=True, blank=True)
    live_url = models.URLField(null=True, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-start_date", "-order"]

    def __str__(self):
        return str(self.title)


class Education(TimestampMixin):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="education")
    institution = models.CharField(max_length=200, null=True, blank=True)
    degree = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    current = models.BooleanField(default=False, null=True, blank=True)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    achievements = models.TextField(null=True, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-start_date", "-order"]

    def __str__(self):
        return f"{self.degree} in {self.field_of_study}"


class Certification(TimestampMixin):
    profile = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="certifications"
    )
    name = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200, null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=100, null=True, blank=True)
    credential_url = models.URLField(null=True, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-issue_date", "-order"]

    def __str__(self):
        return f"{self.name} from {self.issuer}"


class Publication(TimestampMixin):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="publications")
    title = models.CharField(max_length=500)
    authors = models.TextField(blank=True, null=True)
    publication_date = models.DateField(blank=True, null=True)
    publisher = models.CharField(max_length=200, null=True, blank=True)
    journal = models.CharField(max_length=200, null=True, blank=True)
    doi = models.CharField(max_length=100, null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    abstract = models.TextField(null=True, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-publication_date", "-order"]

    def __str__(self):
        return str(self.title)


class Skill(TimestampMixin):
    SKILL_CATEGORIES = [
        ("programming", "Programming Languages"),
        ("frameworks", "Frameworks & Libraries"),
        ("databases", "Databases"),
        ("tools", "Tools & Technologies"),
        ("soft_skills", "Soft Skills"),
        ("languages", "Languages"),
        ("other", "Other"),
    ]

    PROFICIENCY_CHOICES = [
        (1, "Beginner"),
        (2, "Elementary"),
        (3, "Intermediate"),
        (4, "Advanced"),
        (5, "Expert"),
    ]

    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=100, db_index=True)
    category = models.CharField(max_length=20, choices=SKILL_CATEGORIES)
    proficiency = models.IntegerField(choices=PROFICIENCY_CHOICES, default=3)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["category", "-proficiency", "name"]

    def save(self, *args, **kwargs):
        # Clean up skill name (lowercase, strip whitespace)
        self.name = self.name.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    @property
    def proficiency_display_with_max(self):
        """
        Returns the proficiency display name along with the numeric value out of the maximum.
        Example: "Intermediate (3/5)"
        """
        if not self.PROFICIENCY_CHOICES:
            return f"{self.proficiency}"  # Fallback if choices are somehow empty
        max_proficiency_value = max(choice[0] for choice in self.PROFICIENCY_CHOICES)
        return f"({self.proficiency}/{max_proficiency_value})"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved"""
    instance.userprofile.save()
