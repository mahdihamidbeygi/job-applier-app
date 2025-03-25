from openai import OpenAI
from django.conf import settings
from typing import Dict, List

class ContentGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.MODEL_SETTINGS['GPT_MODEL']
        self.temperature = settings.MODEL_SETTINGS['TEMPERATURE']

    def generate_cover_letter(self, job_description: str, profile_data: Dict) -> str:
        """Generate a tailored cover letter based on job description and profile."""
        prompt = self._create_cover_letter_prompt(job_description, profile_data)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert cover letter writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature
        )
        
        return response.choices[0].message.content

    def analyze_job_requirements(self, job_description: str) -> Dict:
        """Analyze job requirements and extract key information."""
        prompt = f"""
        Analyze this job description and extract:
        1. Required skills
        2. Required experience
        3. Key responsibilities
        4. Required qualifications
        
        Job Description: {job_description}
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a job requirements analyzer."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature
        )
        
        return self._parse_analysis(response.choices[0].message.content)

    def match_profile_to_job(self, profile_data: Dict, job_requirements: Dict) -> Dict:
        """Match profile against job requirements and provide analysis."""
        prompt = self._create_matching_prompt(profile_data, job_requirements)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a job matching expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature
        )
        
        return self._parse_matching(response.choices[0].message.content)

    def _create_cover_letter_prompt(self, job_description: str, profile_data: Dict) -> str:
        return f"""
        Create a professional cover letter for the following job and candidate profile:
        
        Job Description:
        {job_description}
        
        Candidate Profile:
        - Skills: {profile_data.get('skills', [])}
        - Experience: {profile_data.get('experience', [])}
        - Education: {profile_data.get('education', [])}
        
        The cover letter should:
        1. Highlight relevant skills and experience
        2. Show enthusiasm for the role
        3. Be concise and professional
        4. Include specific examples from the candidate's experience
        """

    def _create_matching_prompt(self, profile_data: Dict, job_requirements: Dict) -> str:
        return f"""
        Analyze the match between this candidate profile and job requirements:
        
        Profile:
        {profile_data}
        
        Job Requirements:
        {job_requirements}
        
        Provide:
        1. Match percentage
        2. Matching skills
        3. Missing skills
        4. Recommendations for improvement
        """

    def _parse_analysis(self, content: str) -> Dict:
        # Implement parsing logic for job analysis
        # This is a placeholder - implement actual parsing
        return {
            'skills': [],
            'experience': [],
            'responsibilities': [],
            'qualifications': []
        }

    def _parse_matching(self, content: str) -> Dict:
        # Implement parsing logic for matching analysis
        # This is a placeholder - implement actual parsing
        return {
            'match_percentage': 0,
            'matching_skills': [],
            'missing_skills': [],
            'recommendations': []
        } 