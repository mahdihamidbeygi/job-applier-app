import logging
import os
import sys

import django

# --- Add Django Setup ---
# Add the project root directory to Python path if running script directly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_applier.settings")
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)
# --- End Django Setup ---


from unittest.mock import patch

import pytest

# Note: The `client` fixture used below is a common pattern in web framework testing
# (e.g., Flask, Django with pytest). You'll need to have this set up in your
# conftest.py or test setup.
#
# Example for Flask:
#
# In your conftest.py or at the top of your test file:
# from your_application_module import app as flask_app # or however you create your app
#
# @pytest.fixture
# def client():
#     flask_app.config['TESTING'] = True
#     with flask_app.test_client() as client:
#         yield client
#
# For Django, you might use Django's `APIClient` or `TestCase.client`.
# The `mocker` fixture is provided by the `pytest-mock` plugin.
from core.tests.conftest import client
from core.utils.profile_importers import GitHubProfileImporter

# def test_import_from_github_missing_url(client):
#     """
#     Tests that POSTing to /profile/import/github/ without a GitHub URL
#     in the payload results in a 400 Bad Request error.
#     This directly reflects the scenario from the provided logs.
#     """
#     # Assuming the endpoint expects a JSON payload, e.g., {"github_url": "..."}
#     # Sending an empty JSON payload or one missing the 'github_url' key.
#     response = client.post("/profile/import/github/", json={})

#     assert (
#         response.status_code == 400
#     ), f"Expected status code 400 but got {response.status_code}. Response data: {response.data.decode(errors='ignore')}"

#     # Based on your log `400 35`, the error message is likely short.
#     # Adjust the assertion below to match your actual error message format and content.
#     # For example, if your API returns JSON: {"error": "No GitHub URL provided"}
#     # Or if it's plain text: b"No GitHub URL provided"

#     expected_error_fragment = b"No GitHub URL provided"  # Adjust to your API's actual error message

#     # Check if the expected error message is part of the response body
#     assert (
#         expected_error_fragment in response.data
#     ), f"Expected fragment '{expected_error_fragment.decode()}' not found in response data: '{response.data.decode(errors='ignore')}'"

#     # Given the log indicated a response size of 35 bytes, you might also check length:
#     # assert len(response.data) == 35 # Or a small range


# def test_import_from_github_success(client, mocker=None):
#     """
#     Tests that POSTing to /profile/import/github/ with a valid GitHub URL
#     results in a successful response (e.g., 200 OK).
#     """
#     valid_github_url = "https://github.com/mahdihamidbeygi"

#     # If the import process involves external calls or complex database operations,
#     # you might want to mock those to keep the test focused and fast.
#     # For example, if there's a service function that does the actual import:
#     # mock_perform_import = mocker.patch('/opt/your_project/services/importer_service.perform_actual_github_import')
#     # mock_perform_import.return_value = {"status": "success", "imported_items": 5}

#     response = client.post("/profile/import/github/", json={"github_url": valid_github_url})

#     assert (
#         response.status_code == 200
#     ), f"Expected status code 200 but got {response.status_code}. Response data: {response.data.decode(errors='ignore')}"

#     # Add assertions for the success response content, e.g., checking for a success message or specific data.
#     # For example, if it returns JSON:
#     # assert response.json.get("message") == "Import initiated successfully"
#     assert b"Import successful" in response.data  # Adjust to your actual success message/response


# test_import_from_github_missing_url(client)
# test_import_from_github_success(client)


def test_githubprofileimporter_import_profile():
    github_username = "mahdihamidbeygi"
    github_importer = GitHubProfileImporter(github_username=github_username)
    user_profile: str = github_importer.import_profile()
    print("User Profile: \n ", user_profile)


def test_analyze_code_typescript_fallback_to_llm():
    """
    Tests that analyze_python_code falls back to LLM for non-Python code (TypeScript)
    and returns the LLM's analysis.
    """
    github_username = "mahdihamidbeygi"  # Dummy username for instantiation
    importer = GitHubProfileImporter(github_username=github_username)

    typescript_code_snippet = """
    import { Component } from '@angular/core';

    interface UserProfile {
      name: string;
      email: string;
    }

    export class MyComponent {
      user: UserProfile;

      constructor() {
        this.user = { name: 'Test', email: 'test@example.com' };
      }

      greet(message: string): string {
        return `${message}, ${this.user.name}`;
      }
    }

    function utilityFunction(): void {
      console.log('Utility function called');
    }
    """

    expected_llm_output = {
        "functions": ["greet", "utilityFunction"],
        "classes": ["MyComponent"],  # Or "UserProfile", "MyComponent" depending on LLM
        "imports": ["@angular/core"],
        "analyzed_by": "llm",
    }

    # Mock the LLM client's method within the GitHubProfileImporter instance
    with patch.object(
        importer.client, "generate_structured_output", return_value=expected_llm_output
    ) as mock_llm_call:
        result = importer.analyze_python_code(typescript_code_snippet)

        # Assert that the LLM was called
        mock_llm_call.assert_called_once()

        # Assert that the result matches the expected LLM output
        assert result == expected_llm_output
        assert result.get("analyzed_by") == "llm"
        assert "greet" in result.get("functions", [])
        assert "@angular/core" in result.get("imports", [])
