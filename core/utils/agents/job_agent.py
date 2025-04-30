"""
Job agent for each job listing.
"""

import datetime
import json
import logging
from typing import Any, Dict, Optional

from django.shortcuts import get_object_or_404

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
            logger.info(
                "JobAgent initialized by extracting details from text (new JobListing created)"
            )
        else:
            # If neither job_id nor text is provided, raise an error
            raise ValueError("Either job_id or text must be provided to JobAgent")

    def _validate_and_clean_job_data(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates and cleans the job data dictionary extracted by the LLM
        before saving it to the JobListing model.

        Args:
            job_data: The dictionary returned by the LLM.

        Returns:
            A cleaned and validated dictionary, ready for model creation.
            Raises ValueError if critical validation fails.
        """
        if not isinstance(job_data, dict):
            logger.error(
                f"LLM structured output was not a dictionary, but {type(job_data)}. Cannot validate."
            )
            raise TypeError("LLM structured output was not a dictionary.")

        cleaned_data = job_data.copy()  # Work on a copy

        # --- 1. Handle Required Fields (Based on JobListing model) ---
        required_text_fields = {
            "description": "No description provided",
            # Add other fields from JobListing that are NOT nullable/blankable
        }

        for field, default_value in required_text_fields.items():
            value = cleaned_data.get(field)
            if not value or not isinstance(value, str) or not value.strip():
                logger.warning(
                    f"LLM did not extract required field '{field}' or it was empty. Setting to default: '{default_value}'."
                )
                cleaned_data[field] = default_value
            else:
                cleaned_data[field] = value.strip()  # Trim whitespace

        # --- 2. Clean Specific Field Types ---
        for key, value in cleaned_data.items():
            # Trim other string fields
            if isinstance(value, str):
                cleaned_data[key] = value.strip()

            # Clean date fields (remove "None" strings, etc.)
            # Note: The JobListing model uses DateField, not DateTimeField.
            # Let the model handle actual date parsing from string if possible.
            elif (
                "date" in key.lower()
                and isinstance(value, str)
                and ("None" in value or not value.strip())
            ):
                cleaned_data[key] = None  # Set to None for the model

            # Ensure list fields (skills) are lists
            elif key in ["required_skills", "preferred_skills"]:
                if isinstance(value, str):
                    try:
                        # Try parsing if it looks like JSON list
                        if value.strip().startswith("[") and value.strip().endswith("]"):
                            parsed_list = json.loads(value)
                            cleaned_data[key] = parsed_list if isinstance(parsed_list, list) else []
                        # Try splitting if comma-separated
                        elif "," in value:
                            cleaned_data[key] = [
                                item.strip() for item in value.split(",") if item.strip()
                            ]
                        # Otherwise, treat as single item list if not empty
                        elif value.strip():
                            cleaned_data[key] = [value.strip()]
                        else:
                            cleaned_data[key] = []
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse string '{value}' as list for field '{key}'. Defaulting to empty list."
                        )
                        cleaned_data[key] = []
                elif value is None:
                    cleaned_data[key] = []  # Ensure None becomes empty list
                elif not isinstance(value, list):
                    logger.warning(
                        f"Field '{key}' was not a list or string ({type(value)}). Converting to list."
                    )
                    # Attempt conversion, default to empty list on failure
                    try:
                        cleaned_data[key] = [str(value)] if value is not None else []
                    except:
                        cleaned_data[key] = []

        # --- 3. Ensure Default Empty Lists for JSONFields ---
        # If skills fields are missing entirely, default them to empty lists
        for key in ["required_skills", "preferred_skills"]:
            if key not in cleaned_data or cleaned_data[key] is None:
                cleaned_data[key] = []
            # Final check to ensure it's a list
            elif not isinstance(cleaned_data[key], list):
                logger.error(
                    f"Post-cleaning, field '{key}' is still not a list ({type(cleaned_data[key])}). Forcing empty list."
                )
                cleaned_data[key] = []

        # --- 4. Add any other model-specific validation ---
        # Example: Check length constraints if needed (though DB handles this)
        max_len = JobListing._meta.get_field("title").max_length
        if len(cleaned_data.get("title", "")) > max_len:
            logger.warning(f"Field 'title' exceeds max length {max_len}. Truncating.")
            cleaned_data["title"] = cleaned_data["title"][:max_len]

        logger.debug(f"Validated and cleaned job data: {cleaned_data}")
        return cleaned_data

    def _extract_job_details_from_text(self, text: str) -> None:
        """
        Extract the job details from the text and create a new JobListing.
        """
        # --- Step 1: Log Input Text ---
        logger.debug(
            f"Attempting to extract job details from text for user {self.user_id}. Text length: {len(text)}"
        )
        logger.debug(f"Input text snippet: {text[:500]}...")

        # --- Step 2: Prepare Schema and Prompt ---
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
            # 'posted_date', # Keep posted_date if LLM can extract it
        }
        for field in fields_to_exclude:
            job_details_schema.pop(field, None)

        # Updated prompt (as used before)
        prompt: str = f"""Extract the job details from the text below based on the provided schema.
            Ensure the output is a single, valid JSON object matching the schema structure.
            **IMPORTANT: For any date fields like 'posted_date', use the 'YYYY-MM-DD' format.**
            For other empty fields, use null or an appropriate empty value (e.g., "", []).

            Schema properties expected: {list(job_details_schema.keys())}

            Text:
            {text}

            Valid JSON Output:"""

        try:
            # --- Step 3: Call LLM ---
            logger.debug("Calling LLM generate_structured_output...")
            raw_job_record_dict: Dict[str, Any] = self.llm.generate_structured_output(
                prompt=prompt,
                output_schema=job_details_schema,
                temperature=0.0,
            )
            logger.debug(f"LLM raw structured output received (type: {type(raw_job_record_dict)}).")

            # --- Step 4: Validate and Clean Data ---
            job_record_dict = self._validate_and_clean_job_data(raw_job_record_dict)

            # --- Step 5: Add User ID and Create Record ---
            job_record_dict["user_id"] = self.user_id
            logger.debug(f"Attempting to create JobListing with cleaned data: {job_record_dict}")
            self.job_record = JobListing.objects.create(**job_record_dict)
            logger.info(f"New JobListing created with ID: {self.job_record.id}")

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as parse_err:  # Catch validation errors too
            logger.exception(
                f"Error parsing, validating, or processing LLM output for user {self.user_id}: {parse_err}."
            )
            self.job_record = None
            # Re-raise as ValueError to be caught by the calling tool function
            raise ValueError(
                f"LLM failed to produce valid/processable structured output. Error: {parse_err}"
            ) from parse_err
        except Exception as e:
            logger.exception(
                f"Error extracting job details or creating JobListing for user {self.user_id}"
            )
            self.job_record = None
            raise e  # Re-raise other exceptions

    def get_formatted_info(self) -> str:
        """Returns formatted job information string."""
        if self.job_record:
            return self.job_record.get_formatted_info()  # Assuming JobListing has this method
        return "No job record loaded."
