"""
Core app views.
This module imports all view functions from submodules.
"""

# Import from views modules
from .api_views import *
from .auth_views import *
from .job_views import *
from .document_views import *
from .utility_views import *

# Import from profile_views package
from .profile_views import (
    profile,
    edit_profile,
    get_profile_stats,
    add_work_experience,
    add_project,
    add_education,
    add_certification,
    add_publication,
    add_skill,
    deduplicate_skills,
    import_github_profile,
    import_resume,
    import_linkedin_profile,
    delete_item,
    bulk_delete_records,
    edit_record,
)
