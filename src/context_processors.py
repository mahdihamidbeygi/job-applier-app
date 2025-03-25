from django.conf import settings

def common_context(request):
    """
    Add common variables to all templates.
    """
    context = {
        'SITE_NAME': 'Job Applier',
        'SITE_DESCRIPTION': 'Track your job applications and manage your career',
        'SITE_URL': request.build_absolute_uri('/').rstrip('/'),
        'SITE_EMAIL': settings.EMAIL_HOST_USER,
    }
    return context
