"""
Profile-related views module.
This package contains all views related to user profiles and their components.
"""

from .base_views import profile, edit_profile, get_profile_stats
from .experience_views import add_work_experience
from .project_views import add_project
from .education_views import add_education
from .certification_views import add_certification
from .publication_views import add_publication
from .skill_views import add_skill, deduplicate_skills
from .import_views import import_github_profile, import_resume, import_linkedin_profile
from .utility_views import delete_item, bulk_delete_records, edit_record

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
]
