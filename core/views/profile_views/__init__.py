"""
Profile-related views module.
This package contains all views related to user profiles and their components.
"""

from .base_views import edit_profile, get_profile_stats, profile
from .certification_views import add_certification
from .education_views import add_education
from .experience_views import add_work_experience
from .import_views import import_github_profile, import_linkedin_profile, import_resume
from .project_views import add_project
from .publication_views import add_publication
from .skill_views import add_skill, deduplicate_skills
from .utility_views import bulk_delete_records, delete_item, edit_record, generate_profile_bio

__all__ = [
    "profile",
    "edit_profile",
    "get_profile_stats",
    "add_work_experience",
    "add_project",
    "add_education",
    "add_certification",
    "add_publication",
    "add_skill",
    "deduplicate_skills",
    "import_github_profile",
    "import_resume",
    "import_linkedin_profile",
    "delete_item",
    "bulk_delete_records",
    "edit_record",
    "generate_profile_bio",
]
