"""
Core app models package.
This module imports all models to maintain Django's models discovery.
"""

# Base models
from .base import TimestampMixin

# User profile models
from .profile import (
    UserProfile,
    WorkExperience,
    Project,
    Education,
    Certification,
    Publication,
    Skill,
)

# Job-related models
from .jobs import JobListing, JobPlatformPreference

__all__ = [
    "TimestampMixin",
    "UserProfile",
    "WorkExperience",
    "Project",
    "Education",
    "Certification",
    "Publication",
    "Skill",
    "JobListing",
    "JobPlatformPreference",
]
