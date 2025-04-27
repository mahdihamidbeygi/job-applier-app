"""
Job agent for each job listing.
"""

import datetime
import logging
import json
from typing import Any, Dict, Optional

from django.shortcuts import get_object_or_404
from core.utils.agents.base_agent import BaseAgent
from core.models.jobs import JobListing

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

    def _extract_job_details_from_text(self, text: str) -> None:
        """
        Extract the job details from the text and create a new JobListing.
        """
        # --- Step 1: Log Input Text ---
        logger.debug(
            f"Attempting to extract job details from text for user {self.user_id}. Text length: {len(text)}"
        )
        # Log a snippet for easier debugging without flooding logs
        logger.debug(f"Input text snippet: {text[:500]}...")
        # --- End Logging Input ---

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
            "posted_date",
        }
        for field in fields_to_exclude:
            job_details_schema.pop(field, None)

        try:
            # Add explicit instruction for JSON output in prompt
            prompt = f"""Extract the job details from the text below based on the provided schema.
                Ensure the output is a single, valid JSON object matching the schema structure.
                **IMPORTANT: For any date fields like 'posted_date', use the 'YYYY-MM-DD' format.**
                For empty fields, use null or an appropriate empty value (e.g., "", []).

                Schema properties expected: {list(job_details_schema.keys())}

                Text:
                {text}

                Valid JSON Output:"""  # Added instruction

            logger.debug("Calling LLM generate_structured_output...")
            job_record_dict: Dict[str, Any] = self.llm.generate_structured_output(
                prompt=prompt,  # Use updated prompt
                output_schema=job_details_schema,
                temperature=0.0,  # Keep low temp for structured output
            )

            logger.debug(
                f"LLM structured output received (type: {type(job_record_dict)})."
            )  # Log success

            if not isinstance(job_record_dict, dict):
                logger.error(
                    f"LLM generate_structured_output did not return a dictionary. Got type: {type(job_record_dict)}. Value: {job_record_dict}"
                )
                raise TypeError("LLM structured output was not a dictionary.")

            # Clean up potential "None" strings from LLM output for date fields
            for key, value in job_record_dict.items():
                if "date" in key.lower() and isinstance(value, str) and "None" in value.lower():
                    job_record_dict[key] = None
                # Handle potential list fields expected by JSONField if LLM returns string
                if key in ["required_skills", "preferred_skills"] and isinstance(value, str):
                    try:
                        # Attempt to parse if it looks like a list representation
                        if value.strip().startswith("[") and value.strip().endswith("]"):
                            parsed_list = json.loads(value)
                            if isinstance(parsed_list, list):
                                job_record_dict[key] = parsed_list
                            else:  # If parsing results in non-list, default to empty list
                                job_record_dict[key] = []
                        else:  # If not list-like string, maybe comma-separated?
                            job_record_dict[key] = [
                                item.strip() for item in value.split(",") if item.strip()
                            ]
                    except json.JSONDecodeError:
                        # If parsing fails, default to empty list or handle as needed
                        job_record_dict[key] = []

            # Set the user ID
            job_record_dict["user_id"] = self.user_id

            # Create the new JobListing object
            logger.debug(f"Attempting to create JobListing with data: {job_record_dict}")
            self.job_record = JobListing.objects.create(**job_record_dict)
            logger.info(f"New JobListing created with ID: {self.job_record.id}")

        except (json.JSONDecodeError, TypeError) as parse_err:  # Catch TypeError from our check too
            logger.exception(
                f"Error parsing or validating LLM output for user {self.user_id}: {parse_err}. Check LLM output format or generate_structured_output implementation."
            )
            self.job_record = None
            raise ValueError(
                f"LLM failed to produce valid structured output. Error: {parse_err}"
            ) from parse_err
        except Exception as e:
            # Catch other potential errors (DB create, etc.)
            # Use logger.exception to include the full traceback
            logger.exception(
                f"Error extracting job details or creating JobListing for user {self.user_id}"
            )
            self.job_record = None
            # Re-raise the exception so the agent knows something went wrong
            raise e

    def get_formatted_info(self) -> str:
        """Returns formatted job information string."""
        if self.job_record:
            return self.job_record.get_formatted_info()  # Assuming JobListing has this method
        return "No job record loaded."
