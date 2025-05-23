"""
Core app views.
This module imports all view functions from submodules.
"""

# Import from views modules
from .api_views import *
from .auth_views import *
from .document_views import *
from .job_views import *

# Import from profile_views package
from .profile_views import (
    add_certification,
    add_education,
    add_project,
    add_publication,
    add_skill,
    add_work_experience,
    bulk_delete_records,
    deduplicate_skills,
    delete_item,
    edit_profile,
    edit_record,
    generate_profile_bio,
    get_profile_stats,
    import_github_profile,
    import_linkedin_profile,
    import_resume,
    profile,
)
from .utility_views import *
