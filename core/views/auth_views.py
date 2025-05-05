"""
Authentication related views for the core app.
"""

import logging

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import AbstractUser
from django.http import HttpResponse, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import redirect, render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

logger: logging.Logger = logging.getLogger(__name__)


def register(request) -> HttpResponseRedirect | HttpResponsePermanentRedirect | HttpResponse:
    """Register a new user"""
    if request.method == "POST":
        form: UserCreationForm = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully!")
            return redirect("core:login")
    else:
        form = UserCreationForm()
    return render(request, "core/register.html", {"form": form})


@api_view(["POST"])
@permission_classes([AllowAny])
def get_token(request) -> Response:
    """
    Get JWT token for a user
    """
    try:
        username: str = request.data.get("username", "")
        password: str = request.data.get("password", "")

        user: AbstractUser | None = authenticate(username=username, password=password)

        if user is not None:
            refresh: RefreshToken = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user_id": user.id,
                    "username": user.username,
                }
            )
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        logger.error(f"Error in get_token: {str(e)}")
        return Response(
            {"error": "Authentication failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
