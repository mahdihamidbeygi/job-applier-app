"""
Views for the core app.
This file re-exports all views from the views package for backward compatibility.
DEPRECATED: Use the specific view modules directly instead of importing from here.
"""

# This file is maintained for backward compatibility only
# Please import directly from the appropriate view modules

# Auth views
from core.views.auth_views import register, get_token

# Profile views
from core.views.profile_views import (
    profile,
    add_work_experience,
    add_project,
    add_education,
    add_certification,
    add_publication,
    add_skill,
    delete_item,
    import_github_profile,
    import_resume,
    import_linkedin_profile,
    bulk_delete_records,
    edit_record,
    get_profile_stats,
    deduplicate_skills,
)

# Job views
from core.views.job_views import (
    jobs_page,
    job_detail,
    job_apply,
    search_jobs,
    generate_job_documents,
    get_job_documents,
    apply_to_job,
    job_platform_preferences,
    remove_job,
)

# Document generation views
from core.views.document_views import (
    generate_documents,
    generate_answers,
    process_job_application,
    fill_form,
    ManualSubmissionView,
)

# API viewsets
from core.views.api_views import (
    UserProfileViewSet,
    WorkExperienceViewSet,
    ProjectViewSet,
    EducationViewSet,
    CertificationViewSet,
    PublicationViewSet,
    SkillViewSet,
)

# Utility views
from core.views.utility_views import (
    home,
    test_s3,
    parse_pdf_resume,
    load_user_background,
)

# Base permission classes
from core.views.api_views import IsOwnerOrReadOnly

# Print a deprecation warning
import warnings

warnings.warn(
    "Importing from core.views is deprecated. "
    "Please import directly from the appropriate view modules.",
    DeprecationWarning,
    stacklevel=2,
)
