"""
Core app models package.
This module imports all models to maintain Django's models discovery.
"""

# Base models
from .base import TimestampMixin

# Chat models
from .chat import ChatConversation, ChatMessage

# Job-related models
from .jobs import JobListing, JobPlatformPreference

# Misc models
from .misc import LangGraphCheckpoint

# User profile models
from .profile import (
    Certification,
    Education,
    Project,
    Publication,
    Skill,
    UserProfile,
    WorkExperience,
)

__all__ = [
    "TimestampMixin",
    "ChatConversation",
    "ChatMessage",
    "UserProfile",
    "WorkExperience",
    "Project",
    "Education",
    "Certification",
    "Publication",
    "Skill",
    "JobListing",
    "JobPlatformPreference",
    "LangGraphCheckpoint",
]
