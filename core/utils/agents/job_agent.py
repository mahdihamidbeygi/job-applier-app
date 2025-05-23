"""
Job agent for each job listing.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from _collections_abc import dict_items
from django.shortcuts import get_object_or_404

from core.forms import JobListingForm
from core.models.jobs import JobListing
from core.utils.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class JobAgent(BaseAgent):
    """
    Agent for assisting with job applications, including form-filling
    and question answering.
    """

    def __init__(
        self, user_id: int, job_id: Optional[int] = None, text: Optional[str] = None, **kwargs
    ) -> None:
        super().__init__(user_id=user_id, **kwargs)
        self.job_record: Optional[JobListing] = None  # Initialize job_record as Optional

        if job_id is not None:
            # Load existing job listing if job_id is provided
            try:
                # Ensure the job belongs to the user
                self.job_record = get_object_or_404(JobListing, id=job_id, user_id=user_id)
                logger.info(f"JobAgent initialized with existing JobListing ID: {job_id}")
            except Exception as e:
                logger.error(f"JobListing with ID {job_id} not found for user {user_id}: {e}")
                # Decide how to handle: raise error or proceed with None job_record
                raise ValueError(
                    f"JobListing with ID {job_id} not found or does not belong to user {user_id}."
                )
        elif text is not None:
            # Extract details and create a new job listing if only text is provided
            # Ensure user_id is passed to _extract_job_details_from_text if needed, or set here
            self._extract_job_details_from_text(text)
        else:
            # If neither job_id nor text is provided, raise an error
            raise ValueError("Either job_id or text must be provided to JobAgent")

    def _validate_and_clean_job_data(
        self, job_data: Dict[str, Any], is_update: bool = False
    ) -> Dict[str, Any]:
        """
        Validates and cleans the job data dictionary extracted by the LLM
        before saving it to the JobListing model.

        Args:
            job_data: The dictionary returned by the LLM.
            is_update: Boolean flag, True if called during an update operation.

        Returns:
            A cleaned and validated dictionary, ready for model creation.
            Raises ValueError if critical validation fails.
        """
        if not isinstance(job_data, dict):
            logger.error(
                f"LLM structured output was not a dictionary, but {type(job_data)}. Cannot validate."
            )
            raise TypeError("LLM structured output was not a dictionary.")

        # For updates, we only want to process fields present in job_data.
        # For creates, job_data comes from LLM and might need defaults for missing required fields.
        processed_data: Dict[str, Any] = {}

        # Fields to iterate over: if update, only those in job_data. If create, all potential fields from schema.
        # However, simpler to iterate job_data and then add defaults for create if missing.

        # Initial population of processed_data for iteration
        # This ensures we only operate on fields intended for update, or all fields from LLM for create.
        source_data_iterator: dict_items[str, Any] = job_data.items()

        for field_name, raw_value in source_data_iterator:
            cleaned_value = raw_value

            if isinstance(cleaned_value, str):
                cleaned_value = cleaned_value.strip()

            # Clean date fields (remove "None" strings, etc.)
            # Note: The JobListing model uses DateField, not DateTimeField.
            # Let the model handle actual date parsing from string if possible.
            elif (
                "date" in field_name.lower()
                and isinstance(cleaned_value, str)
                and ("None" in cleaned_value or not cleaned_value.strip())
            ):
                cleaned_value = None  # Set to None for the model

            # Ensure list fields (skills) are lists
            elif field_name in ["required_skills", "preferred_skills"]:
                if isinstance(cleaned_value, str):
                    try:
                        # Try parsing if it looks like JSON list
                        if cleaned_value.strip().startswith("[") and cleaned_value.strip().endswith(
                            "]"
                        ):
                            parsed_list = json.loads(cleaned_value)
                            cleaned_value = parsed_list if isinstance(parsed_list, list) else []
                        # Try splitting if comma-separated
                        elif "," in cleaned_value:
                            cleaned_value = [
                                item.strip() for item in cleaned_value.split(",") if item.strip()
                            ]
                        # Otherwise, treat as single item list if not empty
                        elif cleaned_value.strip():
                            cleaned_value = [cleaned_value.strip()]
                        else:
                            cleaned_value = []
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse string '{raw_value}' as list for field '{field_name}'. Defaulting to empty list."
                        )
                        cleaned_value = []
                elif cleaned_value is None:  # If explicitly passed as None (e.g. in an update)
                    cleaned_value = []
                elif not isinstance(cleaned_value, list):
                    logger.warning(
                        f"Field '{field_name}' was not a list, string, or None ({type(raw_value)}). Attempting conversion."
                    )
                    # Attempt conversion, default to empty list on failure
                    try:
                        cleaned_value = [str(cleaned_value)] if cleaned_value is not None else []
                    except:
                        cleaned_value = []

            processed_data[field_name] = cleaned_value

        # For create operations (not updates), apply defaults for critical missing fields
        if not is_update:
            if (
                "description" not in processed_data
                or not processed_data.get("description", "").strip()
            ):
                logger.warning(
                    "LLM did not extract 'description' or it was empty. Setting to default."
                )
                processed_data["description"] = "No description provided by LLM."

            for skill_field in ["required_skills", "preferred_skills"]:
                if skill_field not in processed_data or processed_data[skill_field] is None:
                    processed_data[skill_field] = []
                elif not isinstance(processed_data[skill_field], list):  # Ensure it became a list
                    logger.warning(
                        f"Field '{skill_field}' was not a list after initial pass. Forcing to empty list for creation."
                    )
                    processed_data[skill_field] = []

        # --- 4. Add any other model-specific validation ---
        # Example: Check length constraints if needed (though DB handles this)
        if "title" in processed_data:  # Only if title is being processed
            max_len = JobListing._meta.get_field("title").max_length
            if len(processed_data.get("title", "")) > max_len:
                logger.warning(f"Field 'title' exceeds max length {max_len}. Truncating.")
                processed_data["title"] = processed_data["title"][:max_len]
        elif not is_update and (
            "title" not in processed_data or not processed_data.get("title", "").strip()
        ):
            logger.warning("LLM did not extract 'title'. Setting to default for creation.")
            processed_data["title"] = "Untitled Job"

        return processed_data

    def _extract_job_details_from_text(self, text: str) -> None:
        """
        Extract the job details from the text and create a new JobListing.
        """
        logger.debug(
            f"Attempting to extract job details from text for user {self.user_id}. Text length: {len(text)}"
        )

        job_details_schema: Dict[str, Any] = JobListing.get_schema()["properties"]
        fields_to_exclude = {
            "id",
            "user",
            "created_at",
            "updated_at",
            "tailored_resume",
            "tailored_cover_letter",
            "applied",
            "application_date",
            "application_status",
            "match_score",
            "is_active",
        }
        for field in fields_to_exclude:
            job_details_schema.pop(field, None)

        # Update the prompt to enforce strict JSON formatting
        prompt: str = f"""
            You are an excellent job detail extractor from text.
            Extract the job details from the text below based on the provided schema.
            Title, company name and description are necessary. It's possible that title or company name isn't explicitly mentioned.
            
            **CRITICAL: Your output MUST be a single, valid JSON object with ALL property names enclosed in double quotes.**
            Do not include any explanation, commentary, or additional text before or after the JSON.
            Format dates like 'posted_date' using the 'YYYY-MM-DD' format.
            Use null for empty fields, "" for empty strings, and [] for empty arrays.
            
            Schema properties expected: {list(job_details_schema.keys())}
            
            Text:
            {text}
            
            Output (VALID JSON ONLY):
        """

        try:
            # Add error handling for the LLM response
            raw_response = self.llm.generate_text(
                prompt=prompt,
                temperature=0.0,
            )

            # Try to extract just the JSON part if there's any surrounding text
            try:
                import re

                json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                else:
                    json_text = raw_response.strip()

                raw_job_record_dict = json.loads(json_text)
            except json.JSONDecodeError:
                # If that fails, try a direct structured output approach
                raw_job_record_dict = self.llm.generate_structured_output(
                    prompt=prompt,
                    output_schema=job_details_schema,
                    temperature=0.0,
                )

            # Rest of the method remains the same
            job_record_dict: Dict[str, Any] = self._validate_and_clean_job_data(
                raw_job_record_dict, is_update=False
            )
            job_record_dict["user_id"] = self.user_id
            self.job_record = JobListing.objects.create(**job_record_dict)
            logger.info(f"New JobListing created with ID: {self.job_record.id}")

        except (json.JSONDecodeError, TypeError, ValueError) as parse_err:
            logger.error(
                f"Error parsing, validating, or processing LLM output for user {self.user_id}: {parse_err}"
            )
            self.job_record = None
            raise ValueError(
                f"LLM failed to produce valid/processable structured output. Error: {parse_err}"
            ) from parse_err
        except Exception as e:
            logger.exception(
                f"Error extracting job details or creating JobListing for user {self.user_id}"
            )
            self.job_record = None
            raise e

    def get_formatted_info(self) -> str:
        """Returns formatted job information string."""
        if self.job_record:
            return self.job_record.get_formatted_info()  # Assuming JobListing has this method
        return "No job record loaded."

    def update_job_listing(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update job listing using Django form (partial update)

        Args:
            data: Dictionary with job listing fields to update

        Returns:
            Tuple of (bool success, str message)
        """
        if not self.job_record:
            raise ValueError("No job record loaded.")

        try:
            # Start with the existing data from the model instance
            # This ensures we don't lose existing values
            existing_data = {}
            for field in self.job_record._meta.fields:
                field_name = field.name
                existing_data[field_name] = getattr(self.job_record, field_name)

            # Only update fields that are provided in the input data
            # This preserves existing values for fields not in the input
            update_data = {**existing_data}
            for key, value in data.items():
                if key in update_data:
                    update_data[key] = value

            # Create form with the merged data and instance
            form = JobListingForm(data=update_data, instance=self.job_record)

            if form.is_valid():
                # Save the form
                self.job_record = form.save(commit=False)

                # Ensure user relationship is maintained
                if self.user_id:
                    self.job_record.user_id = self.user_id

                # Save the record
                self.job_record.save()

                logger.info(f"Updated JobListing ID: {self.job_record.id}")
                return True, "Job listing updated successfully"
            else:
                error_msg = f"Validation failed: {form.errors}"
                logger.warning(f"Form validation failed: {form.errors}")
                return False, error_msg

        except Exception as e:
            logger.error(f"Error updating job listing: {str(e)}")
            return False, f"Failed to update job listing: {str(e)}"

    def calculate_match_score(self, user_background: str) -> tuple[int, str]:
        """
        Calculates a matching score between the user's background and the current job record.

        This method uses deterministic rules and rubrics to analyze the job's criteria
        against the user's provided background information. It extracts a numerical match score,
        identifies strengths (matching skills/experiences), and potential gaps.
        The calculated score and details are then saved to the job record.

        Args:
            user_background: A string (typically JSON formatted) representing the user's professional
                            background, skills, and experiences.

        Returns:
            A tuple containing:
                - int: The calculated match score (0-100).
                - str: A detailed explanation of the match, including strengths and gaps.
        """
        # Parse user background if it's a string
        if isinstance(user_background, str):
            try:
                user_data = json.loads(user_background)
            except json.JSONDecodeError:
                # If it's not valid JSON, keep it as a string
                user_data = user_background
        else:
            user_data = user_background

        # Extract job requirements and skills
        required_skills = (
            self.job_record.required_skills if hasattr(self.job_record, "required_skills") else []
        )
        preferred_skills = (
            self.job_record.preferred_skills if hasattr(self.job_record, "preferred_skills") else []
        )
        job_description = self.job_record.description

        # Create a deterministic scoring rubric
        scoring_rubric = {
            "required_skills_match": {"weight": 45, "score": 0},  # 45% weight
            "preferred_skills_match": {"weight": 25, "score": 0},  # 25% weight
            "experience_match": {"weight": 20, "score": 0},  # 20% weight
            "education_match": {"weight": 10, "score": 0},  # 10% weight
        }

        # Extract user skills from background
        user_skills = []
        if isinstance(user_data, dict):
            # Try to extract skills from structured data
            user_skills = user_data.get("skills", [])
            if isinstance(user_skills, str):
                user_skills = [s.strip() for s in user_skills.split(",")]

        # Match required skills
        required_matches = []
        required_gaps = []

        if required_skills:
            for skill in required_skills:
                skill_lower = skill.lower()
                # Check if skill is in user's explicit skills list
                skill_found = False

                # Direct match in skills list
                if isinstance(user_skills, list):
                    for user_skill in user_skills:
                        if isinstance(user_skill, str) and skill_lower in user_skill.lower():
                            required_matches.append(skill)
                            skill_found = True
                            break

                # If still not found, check in the entire background
                if not skill_found:
                    if (isinstance(user_data, str) and skill_lower in user_data.lower()) or (
                        isinstance(user_data, dict)
                        and any(
                            skill_lower in str(val).lower() for val in user_data.values() if val
                        )
                    ):
                        required_matches.append(skill)
                    else:
                        required_gaps.append(skill)

        # Calculate required skills score (higher weight)
        if required_skills:
            scoring_rubric["required_skills_match"]["score"] = (
                len(required_matches) / len(required_skills)
            ) * 100
        else:
            scoring_rubric["required_skills_match"][
                "score"
            ] = 100  # No required skills = full score

        # Match preferred skills (similar approach)
        preferred_matches = []
        preferred_gaps = []

        if preferred_skills:
            for skill in preferred_skills:
                skill_lower = skill.lower()
                # Check if skill is in user's explicit skills list
                skill_found = False

                # Direct match in skills list
                if isinstance(user_skills, list):
                    for user_skill in user_skills:
                        if isinstance(user_skill, str) and skill_lower in user_skill.lower():
                            preferred_matches.append(skill)
                            skill_found = True
                            break

                # If still not found, check in the entire background
                if not skill_found:
                    if (isinstance(user_data, str) and skill_lower in user_data.lower()) or (
                        isinstance(user_data, dict)
                        and any(
                            skill_lower in str(val).lower() for val in user_data.values() if val
                        )
                    ):
                        preferred_matches.append(skill)
                    else:
                        preferred_gaps.append(skill)

        # Calculate preferred skills score (less weight)
        if preferred_skills:
            scoring_rubric["preferred_skills_match"]["score"] = (
                len(preferred_matches) / len(preferred_skills)
            ) * 100
        else:
            scoring_rubric["preferred_skills_match"][
                "score"
            ] = 100  # No preferred skills = full score

        # Education match - simplified for deterministic approach
        education_required = False
        education_level_required = "none"

        # Look for education requirements in description
        edu_terms = ["bachelor", "master", "phd", "degree", "diploma", "certification"]
        edu_found = False

        for term in edu_terms:
            if term in job_description.lower():
                education_required = True
                if "bachelor" in job_description.lower():
                    education_level_required = "bachelor"
                elif "master" in job_description.lower() or "mba" in job_description.lower():
                    education_level_required = "master"
                elif "phd" in job_description.lower() or "doctorate" in job_description.lower():
                    education_level_required = "phd"
                edu_found = True
                break

        # Check user education
        has_education = False
        education_level = "none"

        if isinstance(user_data, dict) and "education" in user_data:
            has_education = True
            user_education = user_data["education"]

            # Check education level
            if isinstance(user_education, list) and user_education:
                # Use the highest education level if multiple entries
                for edu in user_education:
                    edu_str = str(edu).lower()
                    if "phd" in edu_str or "doctorate" in edu_str:
                        education_level = "phd"
                        break
                    elif "master" in edu_str or "mba" in edu_str:
                        education_level = "master"
                        # Keep looking for PhD
                    elif "bachelor" in edu_str or "bs" in edu_str or "ba" in edu_str:
                        education_level = "bachelor"
                        # Keep looking for higher degrees
            elif isinstance(user_education, str):
                edu_str = user_education.lower()
                if "phd" in edu_str or "doctorate" in edu_str:
                    education_level = "phd"
                elif "master" in edu_str or "mba" in edu_str:
                    education_level = "master"
                elif "bachelor" in edu_str or "bs" in edu_str or "ba" in edu_str:
                    education_level = "bachelor"

        # Score education match
        education_score = 0
        if not education_required:
            education_score = 100
        else:
            education_levels = {"none": 0, "bachelor": 60, "master": 80, "phd": 100}
            required_level_score = education_levels.get(education_level_required, 0)
            user_level_score = education_levels.get(education_level, 0)

            # If user education meets or exceeds requirement
            if user_level_score >= required_level_score:
                education_score = 100
            else:
                # Partial credit
                education_score = (
                    (user_level_score / required_level_score) * 100
                    if required_level_score > 0
                    else 0
                )

        scoring_rubric["education_match"]["score"] = education_score

        # Experience match - looking for years of experience
        import re

        # Extract years of experience required from job description
        experience_required = 0
        experience_patterns = [
            r"(\d+)[\+]?\s*(?:years|yrs)(?:\s+of)?\s+experience",
            r"experience\D+(\d+)[\+]?\s*(?:years|yrs)",
            r"minimum\s+of\s+(\d+)[\+]?\s*(?:years|yrs)",
        ]

        for pattern in experience_patterns:
            match = re.search(pattern, job_description.lower())
            if match:
                experience_required = int(match.group(1))
                break

        # Extract user's years of experience
        user_experience = 0
        if isinstance(user_data, dict):
            if "experience" in user_data:
                # If it's a list of experience entries
                if isinstance(user_data["experience"], list):
                    # Sum up years in each experience entry, or count number of entries as a proxy
                    for exp in user_data["experience"]:
                        if isinstance(exp, dict) and "years" in exp:
                            try:
                                user_experience += float(exp["years"])
                            except (ValueError, TypeError):
                                # If years can't be parsed, count as 1 year per entry
                                user_experience += 1
                        else:
                            # Count each entry as 1 year if no explicit duration
                            user_experience += 1
                elif isinstance(user_data["experience"], (int, float)):
                    user_experience = float(user_data["experience"])
                elif isinstance(user_data["experience"], str):
                    # Try to extract years from a string like "5 years of experience"
                    match = re.search(
                        r"(\d+)[\+]?\s*(?:years|yrs)", user_data["experience"].lower()
                    )
                    if match:
                        user_experience = int(match.group(1))
                    else:
                        # If no years mentioned, count as 1 year
                        user_experience = 1

        # Calculate experience score
        if experience_required == 0:
            experience_score = 100  # No experience required = full score
        else:
            # Calculate percentage, max out at 100%
            experience_score = min(100, (user_experience / experience_required) * 100)

        scoring_rubric["experience_match"]["score"] = experience_score

        # Calculate weighted average score
        total_score = sum(item["weight"] * item["score"] / 100 for item in scoring_rubric.values())

        # Round to the nearest integer
        match_score = round(total_score)

        # Format detailed explanation
        strengths = []
        gaps = []

        # Add required skills matches to strengths
        for skill in required_matches:
            strengths.append(f"Matches required skill: {skill}")

        # Add preferred skills matches to strengths
        for skill in preferred_matches:
            strengths.append(f"Matches preferred skill: {skill}")

        # Add education strength if applicable
        if education_required and education_score > 50:
            strengths.append(f"Education requirement met: {education_level}")

        # Add experience strength if applicable
        if experience_score > 50:
            strengths.append(
                f"Experience requirement met: {user_experience} years (required: {experience_required})"
            )

        # Add required skills gaps
        for skill in required_gaps:
            gaps.append(f"Missing required skill: {skill}")

        # Add preferred skills gaps
        for skill in preferred_gaps:
            gaps.append(f"Missing preferred skill: {skill}")

        # Add education gap if applicable
        if education_required and education_score <= 50:
            gaps.append(f"Education gap: {education_level_required} degree required")

        # Add experience gap if applicable
        if experience_score <= 50 and experience_required > 0:
            gaps.append(
                f"Experience gap: {experience_required} years required, {user_experience} years found"
            )

        # If no specific strengths identified
        if not strengths:
            strengths = ["No specific strengths identified."]

        # If no specific gaps identified
        if not gaps:
            gaps = ["No specific gaps identified."]

        # Format details
        details = "Strengths:\n"
        for strength in strengths:
            details += f"- {strength}\n"

        details += "\nPotential Gaps:\n"
        for gap in gaps:
            details += f"- {gap}\n"

        # Add scoring breakdown for transparency
        details += "\nScoring Breakdown:\n"
        for category, data in scoring_rubric.items():
            details += f"- {category.replace('_', ' ').title()}: {data['score']:.1f}% (Weight: {data['weight']}%)\n"
        details += f"- Overall Match Score: {match_score}%\n"

        # Save detailed match information to the job listing
        details_json = json.dumps(
            {
                "strengths": strengths,
                "gaps": gaps,
                "scoring_rubric": {
                    k: {"score": v["score"], "weight": v["weight"]}
                    for k, v in scoring_rubric.items()
                },
            }
        )

        self.update_job_listing({"match_score": match_score, "match_details": details_json})

        return (match_score, details)
