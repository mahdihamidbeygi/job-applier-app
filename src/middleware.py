from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from .models.user import User

class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add user to request context
        request.user = request.user

        # Check if user is authenticated for protected URLs
        if not request.user.is_authenticated and request.path.startswith('/applications/'):
            messages.warning(request, 'Please log in to access this page.')
            return redirect(reverse('login') + f'?next={request.path}')

        response = self.get_response(request)
        return response

class MessageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add messages to request context
        request.messages = messages.get_messages(request)

        response = self.get_response(request)
        return response

class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request
        if request.user.is_authenticated:
            # Update last activity
            request.user.last_activity = timezone.now()
            request.user.save(update_fields=['last_activity'])

        # Get response
        response = self.get_response(request)
        return response

class SiteSettingsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add site settings to request
        request.site_name = settings.SITE_NAME
        request.site_description = settings.SITE_DESCRIPTION
        request.site_email = settings.SITE_EMAIL

        # Get response
        response = self.get_response(request)
        return response
