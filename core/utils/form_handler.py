"""
Form handling utilities for standardizing form processing.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, Union

from django import forms
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.utils.logging_utils import log_exceptions

logger = logging.getLogger(__name__)

# Type variables for generics
T = TypeVar("T")  # For model instances
FormT = TypeVar("FormT", bound=forms.ModelForm)  # For form classes


class FormHandler:
    """
    Generic handler for processing forms with consistent error handling and validation.

    This class can be used to standardize form processing across the application,
    reducing repetitive code in views and ensuring consistent error handling.
    """

    @staticmethod
    @log_exceptions(level=logging.ERROR)
    def process_form(
        request: HttpRequest,
        form_class: Type[FormT],
        template_name: str,
        success_url: str,
        instance: Optional[T] = None,
        extra_context: Optional[Dict[str, Any]] = None,
        initial_data: Optional[Dict[str, Any]] = None,
        success_message: Optional[str] = None,
        form_kwargs: Optional[Dict[str, Any]] = None,
        pre_save_callback: Optional[Callable[[FormT], None]] = None,
        post_save_callback: Optional[Callable[[T], None]] = None,
    ) -> HttpResponse:
        """
        Process a form submission with standardized error handling.

        Args:
            request: The HTTP request
            form_class: The form class to use
            template_name: The template to render
            success_url: The URL to redirect to on success
            instance: Optional instance for edit forms
            extra_context: Optional additional context for the template
            initial_data: Optional initial data for the form
            success_message: Optional success message to display
            form_kwargs: Optional additional kwargs for the form
            pre_save_callback: Optional callback to run before saving the form
            post_save_callback: Optional callback to run after saving the form

        Returns:
            HttpResponse: The response object
        """
        form_kwargs = form_kwargs or {}
        if instance:
            form_kwargs["instance"] = instance

        if initial_data:
            form_kwargs["initial"] = initial_data

        if request.method == "POST":
            form_kwargs.update(
                {
                    "data": request.POST,
                    "files": request.FILES,
                }
            )
            form = form_class(**form_kwargs)

            if form.is_valid():
                try:
                    # Run pre-save callback if provided
                    if pre_save_callback:
                        pre_save_callback(form)

                    # Save the form
                    obj = form.save()

                    # Run post-save callback if provided
                    if post_save_callback:
                        post_save_callback(obj)

                    # Add success message if provided
                    if success_message:
                        messages.success(request, success_message)

                    return redirect(success_url)
                except Exception as e:
                    logger.error(f"Error saving form: {str(e)}")
                    form.add_error(None, f"Error saving form: {str(e)}")
        else:
            form = form_class(**form_kwargs)

        context = {
            "form": form,
        }

        if extra_context:
            context.update(extra_context)

        return render(request, template_name, context)

    @staticmethod
    @log_exceptions(level=logging.ERROR)
    def process_ajax_form(
        request: HttpRequest,
        form_class: Type[FormT],
        instance: Optional[T] = None,
        form_kwargs: Optional[Dict[str, Any]] = None,
        pre_save_callback: Optional[Callable[[FormT], None]] = None,
        post_save_callback: Optional[Callable[[T], Dict[str, Any]]] = None,
    ) -> JsonResponse:
        """
        Process an AJAX form submission with standardized error handling.

        Args:
            request: The HTTP request
            form_class: The form class to use
            instance: Optional instance for edit forms
            form_kwargs: Optional additional kwargs for the form
            pre_save_callback: Optional callback to run before saving the form
            post_save_callback: Optional callback to run after saving the form

        Returns:
            JsonResponse: The JSON response object
        """
        if request.method != "POST":
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"__all__": ["Only POST requests are allowed"]},
                },
                status=405,
            )

        form_kwargs = form_kwargs or {}
        if instance:
            form_kwargs["instance"] = instance

        # Handle both JSON and form data
        if request.content_type == "application/json":
            import json

            try:
                data = json.loads(request.body)
                form_kwargs["data"] = data
            except json.JSONDecodeError:
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {"__all__": ["Invalid JSON data"]},
                    },
                    status=400,
                )
        else:
            form_kwargs.update(
                {
                    "data": request.POST,
                    "files": request.FILES,
                }
            )

        form = form_class(**form_kwargs)

        if form.is_valid():
            try:
                # Run pre-save callback if provided
                if pre_save_callback:
                    pre_save_callback(form)

                # Save the form
                obj = form.save()

                # Run post-save callback if provided
                extra_data = {}
                if post_save_callback:
                    extra_data = post_save_callback(obj) or {}

                return JsonResponse(
                    {
                        "success": True,
                        "message": "Form saved successfully",
                        **extra_data,
                    }
                )
            except Exception as e:
                logger.error(f"Error saving form: {str(e)}")
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {"__all__": [f"Error saving form: {str(e)}"]},
                    },
                    status=500,
                )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "errors": form.errors,
                },
                status=400,
            )

    @staticmethod
    @log_exceptions(level=logging.ERROR)
    def handle_delete(
        request: HttpRequest,
        model_class: Type[T],
        object_id: Union[int, str],
        success_url: str,
        success_message: Optional[str] = None,
        permission_check: Optional[Callable[[HttpRequest, T], bool]] = None,
        pre_delete_callback: Optional[Callable[[T], None]] = None,
        post_delete_callback: Optional[Callable[[], None]] = None,
    ) -> HttpResponse:
        """
        Handle object deletion with standardized error handling.

        Args:
            request: The HTTP request
            model_class: The model class
            object_id: The ID of the object to delete
            success_url: The URL to redirect to on success
            success_message: Optional success message to display
            permission_check: Optional function to check if user has permission
            pre_delete_callback: Optional callback to run before deletion
            post_delete_callback: Optional callback to run after deletion

        Returns:
            HttpResponse: The response object
        """
        obj = get_object_or_404(model_class, pk=object_id)

        # Check permissions if callback provided
        if permission_check and not permission_check(request, obj):
            messages.error(request, "You don't have permission to delete this object")
            return redirect(success_url)

        try:
            # Run pre-delete callback if provided
            if pre_delete_callback:
                pre_delete_callback(obj)

            # Delete the object
            obj.delete()

            # Run post-delete callback if provided
            if post_delete_callback:
                post_delete_callback()

            # Add success message if provided
            if success_message:
                messages.success(request, success_message)

            return redirect(success_url)
        except Exception as e:
            logger.error(f"Error deleting object: {str(e)}")
            messages.error(request, f"Error deleting object: {str(e)}")
            return redirect(success_url)

    @staticmethod
    @log_exceptions(level=logging.ERROR)
    def handle_ajax_delete(
        request: HttpRequest,
        model_class: Type[T],
        object_id: Union[int, str],
        permission_check: Optional[Callable[[HttpRequest, T], bool]] = None,
        pre_delete_callback: Optional[Callable[[T], None]] = None,
        post_delete_callback: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> JsonResponse:
        """
        Handle AJAX object deletion with standardized error handling.

        Args:
            request: The HTTP request
            model_class: The model class
            object_id: The ID of the object to delete
            permission_check: Optional function to check if user has permission
            pre_delete_callback: Optional callback to run before deletion
            post_delete_callback: Optional callback to run after deletion

        Returns:
            JsonResponse: The JSON response object
        """
        if request.method != "POST" and request.method != "DELETE":
            return JsonResponse(
                {
                    "success": False,
                    "message": "Only POST and DELETE requests are allowed",
                },
                status=405,
            )

        try:
            obj = get_object_or_404(model_class, pk=object_id)

            # Check permissions if callback provided
            if permission_check and not permission_check(request, obj):
                return JsonResponse(
                    {
                        "success": False,
                        "message": "You don't have permission to delete this object",
                    },
                    status=403,
                )

            # Run pre-delete callback if provided
            if pre_delete_callback:
                pre_delete_callback(obj)

            # Delete the object
            obj.delete()

            # Run post-delete callback if provided
            extra_data = {}
            if post_delete_callback:
                extra_data = post_delete_callback() or {}

            return JsonResponse(
                {
                    "success": True,
                    "message": "Object deleted successfully",
                    **extra_data,
                }
            )
        except Exception as e:
            logger.error(f"Error deleting object: {str(e)}")
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Error deleting object: {str(e)}",
                },
                status=500,
            )
