# GitHub Import Fix

## Issue
The application was experiencing errors when importing profiles from GitHub URLs. The main issues were:

1. **Temporary Directory Management**: The GitHubProfileImporter class wasn't properly cleaning up temporary directories when cloning multiple repositories from the same GitHub user.

2. **File Access Permissions**: On Windows systems, Git repository files were remaining locked during operation, preventing proper cleanup and causing subsequent operations to fail.

3. **Error Handling**: The importer was not gracefully handling failures during the repository cloning process.

## Solution

The following fixes were implemented:

1. **Improved Temporary Directory Management**:
   - Created more unique temporary directories with a descriptive prefix (`github_import_`)
   - Used Python's context manager pattern properly to ensure cleanup after operations

2. **Better Error Handling for File Access**:
   - Added `ignore_errors=True` to the `shutil.rmtree()` calls
   - Created fallback paths when directory cleanup fails
   - Converted error logs to warnings when handling expected Windows file permission issues

3. **Unique Repository Paths**:
   - Generated unique paths for repositories when directory cleanup fails
   - Used `tempfile.mktemp()` to ensure uniqueness

## Testing

The fix was tested with a debug script that:
1. Fetches GitHub profile information
2. Gets contribution data
3. Retrieves repository information
4. Imports the complete profile

The debugging showed that the GitHub API now works correctly when the rate limits are respected.

## Implementation Details

The key changes were in the `core/utils/profile_importers.py` file:

```python
# Create a fresh temporary directory with a descriptive prefix
self.temp_dir = tempfile.mkdtemp(prefix="github_import_")

# Better error handling for directory cleanup
try:
    # On Windows, we might get access denied errors when trying to delete git objects
    # Just try to continue and let Git handle it or create a new path
    shutil.rmtree(repo_path, ignore_errors=True)
    if os.path.exists(repo_path):
        # If the directory still exists, create a new unique path
        repo_path = os.path.join(self.temp_dir, f"{name}_{tempfile.mktemp(prefix='', dir='', suffix='').replace('.', '')}")
except Exception as e:
    # Log but continue with a new unique path
    logger.warning(f"Error cleaning up existing repo directory {repo_path}: {str(e)}")
    repo_path = os.path.join(self.temp_dir, f"{name}_{tempfile.mktemp(prefix='', dir='', suffix='').replace('.', '')}")
```

## Notes for Developers

1. When using the GitHub API, be aware of rate limits (60 requests per hour for unauthenticated users)
2. Consider adding GitHub API token authentication to increase the rate limit for production use
3. On Windows systems, Git repositories may leave locked files that can't be deleted immediately 