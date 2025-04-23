"""
Views package for the core app.
This module re-exports all views to maintain backwards compatibility.
"""

# Auth views
from .auth_views import register, get_token

# Profile views
from .profile_views import (
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
from .job_views import (
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
from .document_views import (
    generate_documents,
    generate_answers,
    process_job_application,
    fill_form,
    ManualSubmissionView,
)

# API viewsets
from .api_views import (
    UserProfileViewSet,
    WorkExperienceViewSet,
    ProjectViewSet,
    EducationViewSet,
    CertificationViewSet,
    PublicationViewSet,
    SkillViewSet,
)

# Utility views
from .utility_views import (
    home,
    test_s3,
    parse_pdf_resume,
    load_user_background,
)

# Base permission classes
from .api_views import IsOwnerOrReadOnly
