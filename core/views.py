"""
Views for the core app.
This file re-exports all views from the views package for backward compatibility.
DEPRECATED: Use the specific view modules directly instead of importing from here.
"""

# This file is maintained for backward compatibility only
# Please import directly from the appropriate view modules

# Print a deprecation warning
import warnings

# Base permission classes
# API viewsets
from core.views.api_views import (
    CertificationViewSet,
    EducationViewSet,
    IsOwnerOrReadOnly,
    ProjectViewSet,
    PublicationViewSet,
    SkillViewSet,
    UserProfileViewSet,
    WorkExperienceViewSet,
)

# Auth views
from core.views.auth_views import get_token, register

# Document generation views
from core.views.document_views import (
    ManualSubmissionView,
    fill_form,
    generate_answers,
    generate_documents,
    process_job_application,
)

# Job views
from core.views.job_views import (
    apply_to_job,
    generate_job_documents,
    get_job_documents,
    job_apply,
    job_detail,
    job_platform_preferences,
    jobs_page,
    remove_job,
    search_jobs,
)

# Profile views
from core.views.profile_views import (
    add_certification,
    add_education,
    add_project,
    add_publication,
    add_skill,
    add_work_experience,
    bulk_delete_records,
    deduplicate_skills,
    delete_item,
    edit_record,
    get_profile_stats,
    import_github_profile,
    import_linkedin_profile,
    import_resume,
    profile,
)

# Utility views
from core.views.utility_views import home, load_user_background, parse_pdf_resume, test_s3

warnings.warn(
    "Importing from core.views is deprecated. "
    "Please import directly from the appropriate view modules.",
    DeprecationWarning,
    stacklevel=2,
)
