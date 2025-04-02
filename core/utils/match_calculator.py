import re
from typing import Dict, List, Set

from django.db.models import F

from core.models import JobListing, Skill, UserProfile


class MatchCalculator:
    def __init__(self, job_listing: JobListing, user_profile: UserProfile):
        self.job_listing = job_listing
        self.user_profile = user_profile
        self.weights = {
            'skills': 0.4,
            'experience': 0.3,
            'education': 0.2,
            'location': 0.1
        }
        
    def calculate_skills_match(self) -> float:
        """Calculate match score based on skills."""
        # Get job required skills
        job_skills = set(self.job_listing.required_skills.all().values_list('name', flat=True))
        user_skills = set(self.user_profile.skills.all().values_list('name', flat=True))
        
        if not job_skills:
            return 0.0
            
        # Calculate matches
        matching_skills = job_skills.intersection(user_skills)
        skills_score = len(matching_skills) / len(job_skills)
        
        return skills_score
        
    def calculate_experience_match(self) -> float:
        """Calculate match score based on years of experience."""
        if not self.job_listing.required_experience:
            return 1.0
            
        # Extract years from experience requirement
        required_years = self._extract_years_from_text(self.job_listing.required_experience)
        if required_years is None:
            return 0.5  # Default score if we can't determine required years
            
        # Calculate total user experience
        user_experience = sum(
            work.years_of_experience 
            for work in self.user_profile.work_experiences.all()
        )
        
        if user_experience >= required_years:
            return 1.0
        elif user_experience >= required_years * 0.7:
            return 0.8
        elif user_experience >= required_years * 0.5:
            return 0.6
        else:
            return 0.3
            
    def calculate_education_match(self) -> float:
        """Calculate match score based on education level."""
        education_levels = {
            'high school': 1,
            'associate': 2,
            'bachelor': 3,
            'master': 4,
            'phd': 5,
            'doctorate': 5
        }
        
        # Get highest education level of user
        user_education = self.user_profile.education_set.all()
        if not user_education.exists():
            return 0.0
            
        user_highest = max(
            (education_levels.get(edu.degree_level.lower(), 0) 
             for edu in user_education),
            default=0
        )
        
        # Get required education from job listing
        required_text = self.job_listing.required_education.lower()
        required_level = 0
        for level, value in education_levels.items():
            if level in required_text:
                required_level = value
                break
                
        if required_level == 0:
            return 1.0  # No specific requirement found
        elif user_highest >= required_level:
            return 1.0
        elif user_highest == required_level - 1:
            return 0.7
        else:
            return 0.4
            
    def calculate_location_match(self) -> float:
        """Calculate match score based on location preference."""
        job_location = self.job_listing.location.lower()
        preferred_locations = [
            loc.lower() for loc in 
            self.user_profile.preferred_locations.split(',')
        ]
        
        # Check for remote preferences
        if 'remote' in job_location:
            return 1.0
            
        # Check if job location matches any preferred location
        for location in preferred_locations:
            if location.strip() in job_location:
                return 1.0
                
        return 0.5  # Partial match for non-matching locations
        
    def _extract_years_from_text(self, text: str) -> int:
        """Extract number of years from text description."""
        text = text.lower()
        patterns = [
            r'(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?',
            r'(\d+)\+?\s*y\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        return None
        
    def calculate_overall_match(self) -> float:
        """Calculate overall match score."""
        scores = {
            'skills': self.calculate_skills_match(),
            'experience': self.calculate_experience_match(),
            'education': self.calculate_education_match(),
            'location': self.calculate_location_match()
        }
        
        # Calculate weighted average
        overall_score = sum(
            scores[category] * weight 
            for category, weight in self.weights.items()
        )
        
        # Convert to percentage
        return round(overall_score * 100, 2)
        
    def save_match_score(self) -> None:
        """Calculate and save match score to database."""
        score = self.calculate_overall_match()
        self.job_listing.match_score = score
        self.job_listing.save(update_fields=['match_score'])
        
def calculate_and_save_match_scores(job_listing_id: int, user_profile_id: int) -> float:
    """
    Calculate and save match scores for a job listing and user profile.
    Returns the calculated match score.
    """
    try:
        job_listing = JobListing.objects.get(id=job_listing_id)
        user_profile = UserProfile.objects.get(id=user_profile_id)
        
        calculator = MatchCalculator(job_listing, user_profile)
        calculator.save_match_score()
        
        return job_listing.match_score
        
    except (JobListing.DoesNotExist, UserProfile.DoesNotExist) as e:
        print(f"Error calculating match score: {str(e)}")
        return None 