import unittest
import os
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock # Import MagicMock for nested attributes

# Assuming PersonalAgent and JobAgent are importable for type hinting, but we'll mock them.
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.agents.job_agent import JobAgent
from core.utils.agents.application_agent import ApplicationAgent
from core.utils.cover_letter_composition import CoverLetterComposition
from core.models.jobs import JobListing
from django.shortcuts import get_object_or_404



class TestCoverLetterComposition(unittest.TestCase):

    user_id = 1
    job_id = 170
    
    def __init__(self):
        """Set up mock agents and data for testing."""
            # Verify the job exists and belongs to the user
        self.job_listing: JobListing = get_object_or_404(JobListing, id=self.job_id, user_id=self.user_id)

        # Initialize necessary agents for ApplicationAgent
        self.personal_agent = PersonalAgent(user_id=self.user_id)
        self.job_agent = JobAgent(user_id=self.user_id, job_id=self.job_id)  # Load by ID

        # Initialize ApplicationAgent
        self.application_agent = ApplicationAgent(
            user_id=self.user_id,
            personal_agent=self.personal_agent,
            job_agent=self.job_agent,
        )


    def test_generate_cover_letter(self):
        # Call the generation method within ApplicationAgent
        cover_letter_url = self.application_agent.generate_cover_letter()
        print(cover_letter_url)


# Standard Python entry point for running tests
if __name__ == '__main__':
    unittest.main()
