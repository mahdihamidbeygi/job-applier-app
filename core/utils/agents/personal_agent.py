"""
Personal agent for user profile management.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from core.forms import (
    CertificationForm,
    EducationForm,
    ProjectForm,
    PublicationForm,
    SkillForm,
    UserProfileForm,
    WorkExperienceForm,
)
from core.models import UserProfile
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
        Professional Experience: {len(self.user_profile.work_experiences.all())} positions
        Education: {len(self.user_profile.education.all())} institutions
        Skills: {len(self.user_profile.skills.all())} skills
        Projects: {len(self.user_profile.projects.all())} projects
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

    # Profile Update Methods
    def update_profile(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update user profile using Django form

        Args:
            data: Dictionary with user profile fields to update

        Returns:
            Tuple of (bool success, str message)
        """
        if not self.user_profile:
            raise ValueError("User profile not loaded. Call load_user_profile first.")

        try:
            # Start with the existing data from the model instance
            # This ensures we don't lose existing values
            existing_data = {}
            for field in self.user_profile._meta.fields:
                field_name = field.name
                existing_data[field_name] = getattr(self.user_profile, field_name)

            # Only update fields that are provided in the input data
            # This preserves existing values for fields not in the input
            update_data = {**existing_data}
            for key, value in data.items():
                if key in update_data:
                    update_data[key] = value

            # Create form with the merged data and instance
            form = UserProfileForm(data=update_data, instance=self.user_profile)

            if form.is_valid():
                # Save the form
                self.user_profile = form.save()

                # Refresh self-knowledge with updated profile
                self._initialize_self_knowledge()

                logger.info(f"Updated user profile for user ID: {self.user_id}")
                return True, "Profile updated successfully"
            else:
                error_msg = f"Validation failed: {form.errors}"
                logger.warning(f"Form validation failed: {form.errors}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            return False, f"Failed to update profile: {str(e)}"

    def update_work_experience(
        self, exp_id: Optional[int] = None, data: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """
        Create or update work experience

        Args:
            exp_id: ID of work experience to update (None for create new)
            data: Dictionary with work experience fields

        Returns:
            Tuple of (bool success, str message)
        """
        if not self.user_profile:
            raise ValueError("User profile not loaded")

        # Get existing instance if updating
        instance = None
        if exp_id:
            try:
                instance = self.user_profile.work_experiences.get(id=exp_id)
            except:
                return False, f"Work experience with ID {exp_id} not found"

        # Add profile reference to data
        data_copy = data.copy() if data else {}
        data_copy["profile"] = self.user_profile.id

        try:
            # For updates, preserve existing data
            if instance:
                # Start with the existing data
                existing_data = {}
                for field in instance._meta.fields:
                    field_name = field.name
                    existing_data[field_name] = getattr(instance, field_name)

                # Only update fields provided in input data
                update_data = {**existing_data}
                for key, value in data_copy.items():
                    if key in update_data:
                        update_data[key] = value

                # Use the merged data for the form
                form = WorkExperienceForm(data=update_data, instance=instance)
            else:
                # For new instances, just use the provided data
                form = WorkExperienceForm(data=data_copy)

            if form.is_valid():
                # Save the form
                experience = form.save()

                action = "updated" if instance else "created"
                logger.info(f"Work experience {action} for user ID: {self.user_id}")
                return True, f"Work experience {action} successfully"
            else:
                error_msg = f"Validation failed: {form.errors}"
                logger.warning(f"Form validation failed: {form.errors}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Error updating work experience: {str(e)}")
            return False, f"Failed to update work experience: {str(e)}"

    def update_education(
        self, edu_id: Optional[int] = None, data: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """
        Create or update education

        Args:
            edu_id: ID of education to update (None for create new)
            data: Dictionary with education fields

        Returns:
            Tuple of (bool success, str message)
        """
        if not self.user_profile:
            raise ValueError("User profile not loaded")

        instance = None
        if edu_id:
            try:
                instance = self.user_profile.education.get(id=edu_id)
            except:
                return False, f"Education with ID {edu_id} not found"

        data_copy = data.copy() if data else {}
        data_copy["profile"] = self.user_profile.id

        try:
            # For updates, preserve existing data
            if instance:
                # Start with the existing data
                existing_data = {}
                for field in instance._meta.fields:
                    field_name = field.name
                    existing_data[field_name] = getattr(instance, field_name)

                # Only update fields provided in input data
                update_data = {**existing_data}
                for key, value in data_copy.items():
                    if key in update_data:
                        update_data[key] = value

                # Use the merged data for the form
                form = EducationForm(data=update_data, instance=instance)
            else:
                # For new instances, just use the provided data
                form = EducationForm(data=data_copy)

            if form.is_valid():
                education = form.save()

                action = "updated" if instance else "created"
                logger.info(f"Education {action} for user ID: {self.user_id}")
                return True, f"Education {action} successfully"
            else:
                error_msg = f"Validation failed: {form.errors}"
                logger.warning(f"Form validation failed: {form.errors}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Error updating education: {str(e)}")
            return False, f"Failed to update education: {str(e)}"

    def update_skill(
        self, skill_id: Optional[int] = None, data: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """
        Create or update skill

        Args:
            skill_id: ID of skill to update (None for create new)
            data: Dictionary with skill fields

        Returns:
            Tuple of (bool success, str message)
        """
        if not self.user_profile:
            raise ValueError("User profile not loaded")

        instance = None
        if skill_id:
            try:
                instance = self.user_profile.skills.get(id=skill_id)
            except:
                return False, f"Skill with ID {skill_id} not found"

        data_copy = data.copy() if data else {}
        data_copy["profile"] = self.user_profile.id

        try:
            # For updates, preserve existing data
            if instance:
                # Start with the existing data
                existing_data = {}
                for field in instance._meta.fields:
                    field_name = field.name
                    existing_data[field_name] = getattr(instance, field_name)

                # Only update fields provided in input data
                update_data = {**existing_data}
                for key, value in data_copy.items():
                    if key in update_data:
                        update_data[key] = value

                # Use the merged data for the form
                form = SkillForm(data=update_data, instance=instance)
            else:
                # For new instances, just use the provided data
                form = SkillForm(data=data_copy)

            if form.is_valid():
                skill = form.save()

                action = "updated" if instance else "created"
                logger.info(f"Skill {action} for user ID: {self.user_id}")
                return True, f"Skill {action} successfully"
            else:
                error_msg = f"Validation failed: {form.errors}"
                logger.warning(f"Form validation failed: {form.errors}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Error updating skill: {str(e)}")
            return False, f"Failed to update skill: {str(e)}"

    def update_project(
        self, project_id: Optional[int] = None, data: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """
        Create or update project

        Args:
            project_id: ID of project to update (None for create new)
            data: Dictionary with project fields

        Returns:
            Tuple of (bool success, str message)
        """
        if not self.user_profile:
            raise ValueError("User profile not loaded")

        instance = None
        if project_id:
            try:
                instance = self.user_profile.projects.get(id=project_id)
            except:
                return False, f"Project with ID {project_id} not found"

        data_copy = data.copy() if data else {}
        data_copy["profile"] = self.user_profile.id

        try:
            # For updates, preserve existing data
            if instance:
                # Start with the existing data
                existing_data = {}
                for field in instance._meta.fields:
                    field_name = field.name
                    existing_data[field_name] = getattr(instance, field_name)

                # Only update fields provided in input data
                update_data = {**existing_data}
                for key, value in data_copy.items():
                    if key in update_data:
                        update_data[key] = value

                # Use the merged data for the form
                form = ProjectForm(data=update_data, instance=instance)
            else:
                # For new instances, just use the provided data
                form = ProjectForm(data=data_copy)

            if form.is_valid():
                project = form.save()

                action = "updated" if instance else "created"
                logger.info(f"Project {action} for user ID: {self.user_id}")
                return True, f"Project {action} successfully"
            else:
                error_msg = f"Validation failed: {form.errors}"
                logger.warning(f"Form validation failed: {form.errors}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Error updating project: {str(e)}")
            return False, f"Failed to update project: {str(e)}"

    def update_certification(
        self, cert_id: Optional[int] = None, data: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """
        Create or update certification

        Args:
            cert_id: ID of certification to update (None for create new)
            data: Dictionary with certification fields

        Returns:
            Tuple of (bool success, str message)
        """
        if not self.user_profile:
            raise ValueError("User profile not loaded")

        instance = None
        if cert_id:
            try:
                instance = self.user_profile.certifications.get(id=cert_id)
            except:
                return False, f"Certification with ID {cert_id} not found"

        data_copy = data.copy() if data else {}
        data_copy["profile"] = self.user_profile.id

        try:
            # For updates, preserve existing data
            if instance:
                # Start with the existing data
                existing_data = {}
                for field in instance._meta.fields:
                    field_name = field.name
                    existing_data[field_name] = getattr(instance, field_name)

                # Only update fields provided in input data
                update_data = {**existing_data}
                for key, value in data_copy.items():
                    if key in update_data:
                        update_data[key] = value

                # Use the merged data for the form
                form = CertificationForm(data=update_data, instance=instance)
            else:
                # For new instances, just use the provided data
                form = CertificationForm(data=data_copy)

            if form.is_valid():
                certification = form.save()

                action = "updated" if instance else "created"
                logger.info(f"Certification {action} for user ID: {self.user_id}")
                return True, f"Certification {action} successfully"
            else:
                error_msg = f"Validation failed: {form.errors}"
                logger.warning(f"Form validation failed: {form.errors}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Error updating certification: {str(e)}")
            return False, f"Failed to update certification: {str(e)}"

    def update_publication(
        self, pub_id: Optional[int] = None, data: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """
        Create or update publication

        Args:
            pub_id: ID of publication to update (None for create new)
            data: Dictionary with publication fields

        Returns:
            Tuple of (bool success, str message)
        """
        if not self.user_profile:
            raise ValueError("User profile not loaded")

        instance = None
        if pub_id:
            try:
                instance = self.user_profile.publications.get(id=pub_id)
            except:
                return False, f"Publication with ID {pub_id} not found"

        data_copy = data.copy() if data else {}
        data_copy["profile"] = self.user_profile.id

        try:
            # For updates, preserve existing data
            if instance:
                # Start with the existing data
                existing_data = {}
                for field in instance._meta.fields:
                    field_name = field.name
                    existing_data[field_name] = getattr(instance, field_name)

                # Only update fields provided in input data
                update_data = {**existing_data}
                for key, value in data_copy.items():
                    if key in update_data:
                        update_data[key] = value

                # Use the merged data for the form
                form = PublicationForm(data=update_data, instance=instance)
            else:
                # For new instances, just use the provided data
                form = PublicationForm(data=data_copy)

            if form.is_valid():
                publication = form.save()

                action = "updated" if instance else "created"
                logger.info(f"Publication {action} for user ID: {self.user_id}")
                return True, f"Publication {action} successfully"
            else:
                error_msg = f"Validation failed: {form.errors}"
                logger.warning(f"Form validation failed: {form.errors}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Error updating publication: {str(e)}")
            return False, f"Failed to update publication: {str(e)}"

    def delete_related_item(self, model_type: str, item_id: int) -> Tuple[bool, str]:
        """
        Delete a related item (work experience, education, etc.)

        Args:
            model_type: Type of model to delete ('work_experience', 'education', etc.)
            item_id: ID of the item to delete

        Returns:
            Tuple of (bool success, str message)
        """
        if not self.user_profile:
            raise ValueError("User profile not loaded")

        type_to_relation = {
            "work_experience": self.user_profile.work_experiences,
            "education": self.user_profile.education,
            "skill": self.user_profile.skills,
            "project": self.user_profile.projects,
            "certification": self.user_profile.certifications,
            "publication": self.user_profile.publications,
        }

        if model_type not in type_to_relation:
            return False, f"Unknown model type: {model_type}"

        try:
            instance = type_to_relation[model_type].get(id=item_id)
            instance.delete()
            # Refresh self-knowledge after deletion
            self._initialize_self_knowledge()
            return True, f"{model_type.replace('_', ' ').title()} deleted successfully"
        except Exception as e:
            return False, f"Failed to delete {model_type}: {str(e)}"

    def batch_update_skills(self, skills_data: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Batch update skills - add new skills, update existing ones

        Args:
            skills_data: List of dictionaries with skill data

        Returns:
            Tuple of (bool success, str message)
        """
        if not self.user_profile:
            raise ValueError("User profile not loaded")

        success_count = 0
        error_messages = []

        for skill_data in skills_data:
            # Try to find existing skill by name
            skill_name = skill_data.get("name", "").lower().strip()
            if not skill_name:
                error_messages.append("Skill name is required")
                continue

            existing_skill = self.user_profile.skills.filter(name=skill_name).first()

            skill_data_copy = skill_data.copy()
            skill_data_copy["profile"] = self.user_profile.id

            if existing_skill:
                # Update existing skill
                try:
                    # Start with the existing data
                    existing_data = {}
                    for field in existing_skill._meta.fields:
                        field_name = field.name
                        existing_data[field_name] = getattr(existing_skill, field_name)

                    # Only update fields provided in input data
                    update_data = {**existing_data}
                    for key, value in skill_data_copy.items():
                        if key in update_data:
                            update_data[key] = value

                    # Use the merged data for the form
                    form = SkillForm(data=update_data, instance=existing_skill)

                    if form.is_valid():
                        form.save()
                        success_count += 1
                    else:
                        error_messages.append(f"Error with skill '{skill_name}': {form.errors}")
                except Exception as e:
                    error_messages.append(f"Error updating skill '{skill_name}': {str(e)}")
            else:
                # Create new skill
                try:
                    form = SkillForm(data=skill_data_copy)

                    # Mark non-provided fields as not required
                    for field_name, field in form.fields.items():
                        if field_name not in skill_data_copy:
                            form.fields[field_name].required = False

                    if form.is_valid():
                        form.save()
                        success_count += 1
                    else:
                        error_messages.append(f"Error with skill '{skill_name}': {form.errors}")
                except Exception as e:
                    error_messages.append(f"Error creating skill '{skill_name}': {str(e)}")

        if error_messages:
            return (
                (success_count > 0),
                f"Updated {success_count} of {len(skills_data)} skills. Errors: {', '.join(error_messages)}",
            )
        else:
            return True, f"Successfully updated all {success_count} skills"

    def update_full_profile(self, profile_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Update the full user profile including all related models

        Args:
            profile_data: Dictionary with all profile data including related models

        Returns:
            Tuple of (bool overall_success, Dict with detailed results)
        """
        if not self.user_profile:
            raise ValueError("User profile not loaded. Call load_user_profile first.")

        results = {
            "success": True,
            "profile": {"success": False, "message": ""},
            "work_experiences": {
                "success": False,
                "created": 0,
                "updated": 0,
                "deleted": 0,
                "errors": [],
            },
            "education": {"success": False, "created": 0, "updated": 0, "deleted": 0, "errors": []},
            "skills": {"success": False, "created": 0, "updated": 0, "deleted": 0, "errors": []},
            "projects": {"success": False, "created": 0, "updated": 0, "deleted": 0, "errors": []},
            "certifications": {
                "success": False,
                "created": 0,
                "updated": 0,
                "deleted": 0,
                "errors": [],
            },
            "publications": {
                "success": False,
                "created": 0,
                "updated": 0,
                "deleted": 0,
                "errors": [],
            },
        }

        # 1. Update the main profile - already fixed in update_profile method
        if "profile" in profile_data:
            success, message = self.update_profile(profile_data["profile"])
            results["profile"]["success"] = success
            results["profile"]["message"] = message
            if not success:
                results["success"] = False

        # 2. Process work experiences
        if "work_experiences" in profile_data:
            self._process_related_models(
                "work_experience",
                profile_data["work_experiences"],
                self.update_work_experience,
                results["work_experiences"],
            )

        # 3. Process education
        if "education" in profile_data:
            self._process_related_models(
                "education", profile_data["education"], self.update_education, results["education"]
            )

        # 4. Process skills - use batch update for more efficiency
        if "skills" in profile_data:
            if profile_data["skills"]:
                success, message = self.batch_update_skills(profile_data["skills"])
                results["skills"]["success"] = success
                results["skills"]["created_or_updated"] = len(profile_data["skills"])
                if not success:
                    results["skills"]["errors"].append(message)
                    results["success"] = False

        # 5. Process projects
        if "projects" in profile_data:
            self._process_related_models(
                "project", profile_data["projects"], self.update_project, results["projects"]
            )

        # 6. Process certifications
        if "certifications" in profile_data:
            self._process_related_models(
                "certification",
                profile_data["certifications"],
                self.update_certification,
                results["certifications"],
            )

        # 7. Process publications
        if "publications" in profile_data:
            self._process_related_models(
                "publication",
                profile_data["publications"],
                self.update_publication,
                results["publications"],
            )

        # After all updates, refresh self-knowledge
        self._initialize_self_knowledge()

        return results["success"], results

    def _process_related_models(self, model_type, items_data, update_method, results_dict):
        """
        Helper method to process related models (create, update, delete)

        Args:
            model_type: Type of model being processed (e.g., 'work_experience')
            items_data: List of dictionaries with model data
            update_method: Method to call for updating/creating items
            results_dict: Dictionary to store results
        """
        # Track IDs to identify items to delete
        processed_ids = set()
        replace_all = False

        if isinstance(items_data, dict) and "replace_all" in items_data:
            replace_all = items_data.pop("replace_all")
            items_list = items_data.get("items", [])
        else:
            items_list = items_data if isinstance(items_data, list) else []

        # Process new and existing items
        for item in items_list:
            item_id = item.get("id")

            # If ID is provided, try to update
            if item_id:
                processed_ids.add(item_id)
                success, message = update_method(item_id, item)
                if success:
                    results_dict["updated"] += 1
                else:
                    results_dict["errors"].append(message)
                    results_dict["success"] = False
            # If no ID, create new
            else:
                success, message = update_method(None, item)
                if success:
                    results_dict["created"] += 1
                else:
                    results_dict["errors"].append(message)
                    results_dict["success"] = False

        # If replace_all flag is set, delete items not in the provided list
        if replace_all:
            type_to_relation = {
                "work_experience": self.user_profile.work_experiences,
                "education": self.user_profile.education,
                "skill": self.user_profile.skills,
                "project": self.user_profile.projects,
                "certification": self.user_profile.certifications,
                "publication": self.user_profile.publications,
            }

            existing_items = type_to_relation[model_type].all()
            for item in existing_items:
                if item.id not in processed_ids:
                    try:
                        item.delete()
                        results_dict["deleted"] += 1
                    except Exception as e:
                        results_dict["errors"].append(
                            f"Failed to delete {model_type} ID {item.id}: {str(e)}"
                        )
                        results_dict["success"] = False

        # Set success flag if no errors
        if not results_dict["errors"]:
            results_dict["success"] = True

    def get_structured_background(self) -> PersonalBackground:
        """Get the background of the user as a structured PersonalBackground object"""
        profile_data = self.user_profile.get_all_user_info()

        work_experiences = [exp.to_dict() for exp in self.user_profile.work_experiences.all()]
        education = [edu.to_dict() for edu in self.user_profile.education.all()]
        skills = [skill.to_dict() for skill in self.user_profile.skills.all()]
        projects = [project.to_dict() for project in self.user_profile.projects.all()]

        # Assuming these fields exist or can be derived
        github_data = (
            self.user_profile.github_profile.to_dict()
            if hasattr(self.user_profile, "github_profile")
            else {}
        )
        achievements = [ach.description for ach in self.user_profile.achievements.all()]
        interests = [interest.name for interest in self.user_profile.interests.all()]

        return PersonalBackground(
            profile=profile_data,
            work_experience=work_experiences,
            education=education,
            skills=skills,
            projects=projects,
            github_data=github_data,
            achievements=achievements,
            interests=interests,
        )
