"""
Job agent for each job listing.
"""

import datetime
import logging
import json
from typing import Any, Dict

from core.utils.agents.base_agent import BaseAgent
from core.models.jobs import JobListing

logger = logging.getLogger(__name__)


class JobAgent(BaseAgent):
    """
    Agent for assisting with job applications, including form-filling
    and question answering.
    """

    def __init__(self, job_id: int | None = None, text: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.text: str | None = text
        self._extract_job_details()

    def _extract_job_details(self) -> None:
        """
        Extract the job details from the text.
        """
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
        }  # Adjust as needed
        for field in fields_to_exclude:
            job_details_schema.pop(field, None)  # Use pop with default None

        job_record_dict: Dict[str, Any] = self.llm.generate_structured_output(
            prompt=f"""Extract the job details from the text: {self.text},
        make sure to fill in all the fields including dates, 
        for empty fields, use None""",
            output_schema=job_details_schema,
            temperature=0.0,
        )
        for key, value in job_record_dict.items():
            if "date" in key.lower() and "None" in str(value):
                job_record_dict[key] = None

        self.job_record: JobListing = JobListing.objects.create(**job_record_dict)
