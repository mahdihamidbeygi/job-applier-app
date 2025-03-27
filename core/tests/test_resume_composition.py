import unittest
import os
from datetime import datetime
from core.utils.resume_composition import ResumeComposition

class TestResumeComposition(unittest.TestCase):
    def setUp(self):
        # Create test data
        self.user_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '(555) 123-4567',
            'location': 'San Francisco, CA',
            'linkedin': 'linkedin.com/in/johndoe',
            'headline': 'Mahdi Hamidbeygi',
            'title': 'Software Engineer',
            'professional_summary': 'Experienced software engineer with expertise in Python and web development.',
            'work_experience': [
                {
                    'company': 'Tech Corp',
                    'position': 'Senior Software Engineer',
                    'location': 'San Francisco, CA',
                    'start_date': '2020-01-01',
                    'end_date': '2023-12-31',
                    'description': 'Led development of key features and improvements.',
                    'bullet_points': [
                        'Developed and maintained core systems',
                        'Led team of 5 developers',
                        'Improved system performance by 40%'
                    ]
                }
            ],
            'projects': [
                {
                    'title': 'E-commerce Platform',
                    'start_date': '2021-01-01',
                    'end_date': '2021-12-31',
                    'description': 'Built a full-stack e-commerce platform.',
                    'technologies': ['Python', 'Django', 'React', 'PostgreSQL']
                }
            ],
            'certifications': [
                {
                    'name': 'AWS Certified Solutions Architect',
                    'issuer': 'Amazon Web Services',
                    'date': '2022-01-01'
                }
            ],
            'education': [
                {
                    'school': 'University of California, Berkeley',
                    'degree': 'Bachelor of Science',
                    'field_of_study': 'Computer Science',
                    'graduation_date': '2019-05-15'
                }
            ]
        }
        
        # Create output directory if it doesn't exist
        self.output_dir = 'test_output'
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
    def test_resume_creation(self):
        """Test creating a resume with all sections."""
        output_path = os.path.join(self.output_dir, 'test_resume.pdf')
        resume = ResumeComposition(self.user_data)
        resume.build(output_path)
        
        # Check if file was created
        self.assertTrue(os.path.exists(output_path))
        
        # Check file size
        self.assertGreater(os.path.getsize(output_path), 0)
                
    # def tearDown(self):
    #     # Clean up test files
    #     for file in os.listdir(self.output_dir):
    #         os.remove(os.path.join(self.output_dir, file))
    #     os.rmdir(self.output_dir)

if __name__ == '__main__':
    unittest.main() 