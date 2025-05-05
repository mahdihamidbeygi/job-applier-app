import os
import sys
import django
import json
import traceback

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_applier.settings")
django.setup()

from core.utils.profile_importers import GitHubProfileImporter


def debug_github_import(github_username):
    """Test GitHub profile import functionality"""
    try:
        print(f"Initializing importer for username: {github_username}")
        with GitHubProfileImporter(github_username) as importer:
            print("Getting profile info...")
            profile_info = importer.get_profile_info(github_username)
            print(f"Profile info: {json.dumps(profile_info, indent=2)}")

            print("\nGetting contribution data...")
            contribution_data = importer.get_contribution_data(github_username)
            print(f"Contribution data: {json.dumps(contribution_data, indent=2)}")

            print("\nGetting repository info...")
            repo_info = importer.get_repository_info()
            print(f"Found {len(repo_info)} repositories")

            print("\nImporting full profile...")
            profile_data = importer.import_profile(github_username)
            profile_json = json.loads(profile_data)

            if "error" in profile_json:
                print(f"ERROR: {profile_json['error']}")
            else:
                print("Successfully imported GitHub profile")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        github_username = sys.argv[1]
    else:
        # Using a smaller GitHub account with fewer repos for faster testing
        github_username = "defunkt"  # GitHub co-founder with fewer repos

    debug_github_import(github_username)
