import os
import unittest
from datetime import date  # Use date for consistency if models use DateField
from io import BytesIO
from unittest.mock import Mock, patch  # Import Mock and patch

from core.utils.resume_composition import ResumeComposition


# Helper function to create mock model instances with attributes
def create_mock_model(**kwargs):
    mock = Mock()
    for key, value in kwargs.items():
        setattr(mock, key, value)
    return mock


class TestResumeComposition(unittest.TestCase):
    def setUp(self):
        # Keep user_data dictionary for reference if needed, but mocks will be primary
        self.user_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "5551234567",  # Store as digits for easier mocking/formatting
            "location": "San Francisco, CA",
            "linkedin_url": "linkedin.com/in/johndoe",  # Match expected attribute name
            "github_url": "github.com/johndoe",  # Match expected attribute name
            "title": "Software Engineer",
            "professional_summary": "Experienced software engineer with expertise in Python and web development.",
            "work_experience": [
                {
                    "company": "Tech Corp",
                    "position": "Senior Software Engineer",
                    "location": "San Francisco, CA",
                    "start_date": date(2020, 1, 1),  # Use date objects
                    "end_date": date(2023, 12, 31),
                    "description": "Led development of key features and improvements.",
                    "bullet_points": [
                        "Developed and maintained core systems",
                        "Led team of 5 developers",
                        "Improved system performance by 40%",
                    ],
                }
            ],
            "projects": [
                {
                    "title": "E-commerce Platform",
                    "start_date": date(2021, 1, 1),
                    "end_date": date(2021, 12, 31),
                    "description": "Built a full-stack e-commerce platform.",
                    "technologies": [
                        "Python",
                        "Django",
                        "React",
                        "PostgreSQL",
                    ],  # Assuming this is stored/accessed
                }
            ],
            "certifications": [
                {
                    "name": "AWS Certified Solutions Architect",
                    "issuer": "Amazon Web Services",
                    "date": date(2022, 1, 1),
                }
            ],
            "education": [
                {
                    "institution": "University of California, Berkeley",  # Match expected attribute name
                    "degree": "Bachelor of Science",
                    "field_of_study": "Computer Science",
                    "graduation_date": date(2019, 5, 15),
                }
            ],
            "skills": [
                {"name": "Python", "level": 5},
                {"name": "Django", "level": 4},
                {"name": "JavaScript", "level": 3},
            ],
        }

        # Create output directory if it doesn't exist (optional if using BytesIO)
        self.output_dir = "test_output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    # --- NEW TEST FUNCTION ---
    def test_resume_generation_with_mock_agent(self):
        """Test creating a resume PDF using a mocked PersonalAgent."""

        # 1. Create Mock Objects mimicking Django models/managers
        mock_user_profile = Mock()
        mock_user_profile.name = self.user_data["name"]
        mock_user_profile.email = self.user_data["email"]
        mock_user_profile.phone = self.user_data["phone"]
        mock_user_profile.location = self.user_data["location"]
        mock_user_profile.linkedin_url = self.user_data["linkedin_url"]
        mock_user_profile.github_url = self.user_data["github_url"]
        mock_user_profile.title = self.user_data["title"]
        mock_user_profile.professional_summary = self.user_data["professional_summary"]
        mock_user_profile.user_id = 1  # Add a user_id for logging if needed

        # Mock related managers (.all() method)
        mock_user_profile.skills.all.return_value = [
            create_mock_model(**skill_data) for skill_data in self.user_data["skills"]
        ]
        mock_user_profile.projects.all.return_value = [
            create_mock_model(**proj_data) for proj_data in self.user_data["projects"]
        ]
        # NOTE: work_experiences in resume_composition uses dictionary access - adjust mock or code
        # For now, let's assume it expects objects like others
        mock_user_profile.work_experiences.all.return_value = [
            create_mock_model(**exp_data) for exp_data in self.user_data["work_experience"]
        ]
        # Assuming certifications and education also expect objects
        mock_user_profile.certifications.all.return_value = [
            create_mock_model(**cert_data) for cert_data in self.user_data["certifications"]
        ]
        mock_user_profile.education.all.return_value = [
            create_mock_model(**edu_data) for edu_data in self.user_data["education"]
        ]

        # 2. Create Mock PersonalAgent
        mock_personal_agent = Mock()
        mock_personal_agent.user_profile = mock_user_profile
        # Mock the get_background_str method if tailor_to_job uses it
        mock_personal_agent.get_background_str.return_value = "Mock background summary."
        mock_personal_agent.user_id = 1  # Match user_id

        # 3. Instantiate ResumeComposition with the Mock Agent
        # We need to mock the LLM client within ResumeComposition as well
        with patch("core.utils.resume_composition.GoogleClient") as MockGoogleClient:
            # Configure the mock LLM client instance
            mock_llm_instance = MockGoogleClient.return_value
            # Mock the generate_structured_output call used in tailor_to_job
            mock_llm_instance.generate_structured_output.return_value = {
                "summary": "Tailored mock summary.",
                "skills": ["Python", "Django"],  # Mock tailored skills
                "projects": ["E-commerce Platform"],  # Mock tailored projects
            }

            resume = ResumeComposition(mock_personal_agent)

            # 4. Use BytesIO instead of writing to a file
            buffer = BytesIO()
            job_info_str = "Sample job description requiring Python and Django."  # Provide job info for tailoring
            resume.build(buffer, job_info=job_info_str)

            # 5. Assertions
            buffer.seek(0)
            pdf_content = buffer.read()

            self.assertTrue(len(pdf_content) > 0, "PDF buffer should not be empty")
            # Basic check for PDF header
            self.assertTrue(pdf_content.startswith(b"%PDF-"), "Output should be a PDF file")

            # Check if LLM was called correctly (optional)
            mock_llm_instance.generate_structured_output.assert_called_once()
            call_args, call_kwargs = mock_llm_instance.generate_structured_output.call_args
            self.assertIn("Job Description:", call_kwargs["prompt"])
            self.assertIn("Applicant Skills (Full List):", call_kwargs["prompt"])
            self.assertEqual(call_kwargs["output_schema"]["summary"], "string")

    # Optional: Keep the original test if you want to visually inspect output
    # def test_resume_creation_visual_inspection(self):
    #     """Test creating a resume with all sections for visual check."""
    #     # This test would need modification to use mocks like the one above
    #     # or setup a test DB / mock the DB layer.
    #     # For now, focusing on the mocked test.
    #     pass

    # def tearDown(self):
    #     # Clean up test files if not using BytesIO
    #     # If using BytesIO, no file cleanup needed unless you save it somewhere
    #     if os.path.exists(self.output_dir):
    #         for file in os.listdir(self.output_dir):
    #             try:
    #                 os.remove(os.path.join(self.output_dir, file))
    #             except OSError:
    #                 pass # Ignore if file is already gone
    #         try:
    #             os.rmdir(self.output_dir)
    #         except OSError:
    #             pass # Ignore if dir is already gone


if __name__ == "__main__":
    unittest.main()
