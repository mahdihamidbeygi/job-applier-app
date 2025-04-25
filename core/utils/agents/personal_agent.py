import hashlib
import json
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional

from core.models import JobListing, UserProfile
from core.utils.agents.base_agent import BaseAgent

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
    def __init__(self, user_id: int) -> None:
        super().__init__(user_id)
        self.load_user_profile()

    def load_user_profile(self) -> None:
        self.user_profile: UserProfile = UserProfile.objects.get(user_id=self.user_id)
        self._initialize_self_knowledge()

    def _initialize_self_knowledge(self):
        """Initialize the agent with understanding of its own background"""
        if not self.user_profile:
            raise ValueError("User profile not loaded. Call load_user_profile first.")

        prompt: str = f"""
        You are now embodying a job applicant with the following background:
        
        User Profile: {self.user_profile.get_all_user_info()}
        
        You should respond to questions as if you are this person, maintaining consistency
        with this background while being natural and professional.
        """

        response: str = self.llm.generate_text(prompt, temperature=0.0)
        self.save_context("Initialize personal background", response)

    def get_background_summary(self) -> str:
        """Get a concise summary of the background"""
        if not self.user_profile:
            raise ValueError("Background not loaded. Call load_user_profile first.")

        return f"""
        Professional Experience: {len(getattr(self.user_profile, 'work_experiences', []))} positions
        Education: {len(getattr(self.user_profile, 'education', []))} institutions
        Skills: {len(getattr(self.user_profile, 'skills', []))} skills
        Projects: {len(getattr(self.user_profile, 'projects', []))} projects
        """

    def get_background_str(self) -> str:
        """Get the background of the user"""

        if not self.get_memory():
            self._initialize_self_knowledge()
        return self.get_memory()

    def get_formatted_background(self) -> Dict[str, Any]:
        """Get the background of the user"""
        return self.user_profile.get_all_user_info()

    def get_relevant_experience(self, context: str) -> str:
        """Get experience relevant to a specific context"""
        prompt = f"""
        Context: {context}
        
        Based on this background:
        {self.get_background_str()}
        
        Provide the most relevant experience and skills for this context.
        """

        return self.llm.generate_text(prompt)

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

    def _format_skills(self, skills: List[Dict[str, Any]]) -> str:
        return "\n".join(
            [f"- {skill.get('name', '')} ({skill.get('level', '')})" for skill in skills]
        )

    def _format_github_data(self, github_data: Dict[str, Any]) -> str:
        return f"""
        Repositories: {len(github_data.get('repositories', []))}
        Contributions: {github_data.get('contributions', 0)}
        Languages: {', '.join(github_data.get('languages', []))}
        """

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

            response = self.llm.generate_structured_output(prompt, {"skills": list[str]})
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
