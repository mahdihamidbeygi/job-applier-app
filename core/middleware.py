from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from django.http import HttpResponse


class CustomCsrfMiddleware(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        # Completely bypass CSRF for API endpoints
        if request.path.startswith("/api/"):
            return None
        return super().process_view(request, callback, callback_args, callback_kwargs)

    def process_response(self, request, response):
        # Skip CSRF cookie for API endpoints
        if request.path.startswith("/api/"):
            return response
        return super().process_response(request, response)
