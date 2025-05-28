import ast
import json
import logging
import os
import random
import shutil
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import git
from google.genai.types import File
import requests
from bs4 import BeautifulSoup
from django.conf import settings

from core.utils.llm_clients import GoogleClient
from django.conf import settings
from core.models.profile import (
    UserProfile,
    WorkExperience,
    Education,
    Project,
    Certification,
    Publication,
    Skill,
)
from django.core.files.uploadedfile import UploadedFile

# For parsing pyproject.toml
try:
    import tomllib  # Python 3.11+
except ImportError:
    import toml as tomllib  # Fallback for older Python versions (requires `pip install toml`)

# Configure logging
logger = logging.getLogger(__name__)


class GitHubProfileImporter:
    def __init__(self, github_username: str):
        self.github_username = github_username
        self.client = GoogleClient(model=settings.FAST_GOOGLE_MODEL)
        # self.client_fast = GoogleClient()
        # Create a fresh temporary directory for this import session
        self.temp_dir: str = tempfile.mkdtemp(prefix="github_import_")
        self.repos = []  # Keep track of Git repo objects
        self.url_user: str = f"https://api.github.com/users/{github_username}"
        self.headers: Dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
        self.repos_url: str = self.url_user + "/repos"
        # Add GitHub token if available in settings
        if hasattr(settings, "TOKEN_GITHUB") and settings.TOKEN_GITHUB:
            self.headers["Authorization"] = f"token {settings.TOKEN_GITHUB}"
        else:
            logger.error("No GitHub token found in settings")
            raise ValueError("No GitHub token found in settings")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup temporary files and Git repositories when the importer is destroyed."""
        try:
            # Close all Git repositories first
            for repo in self.repos:
                try:
                    repo.close()
                except Exception:
                    pass

            # Then try to remove the temporary directory
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Error cleaning up temp directory: {str(e)}")
        except Exception:
            pass

    def analyze_python_code(self, code: str) -> Dict:
        """Analyze Python code and extract functions, classes, and imports."""
        try:
            tree = ast.parse(code)
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            imports = [
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            ]
            return {
                "functions": functions,
                "classes": classes,
                "imports": imports,
            }
        except SyntaxError:
            logger.info(
                f"AST parsing failed for code (likely not Python or syntax error). Attempting LLM analysis."
            )
            prompt: str = f"""Analyze the following code snippet. It may not be Python.
                        Identify function definitions, class definitions (or equivalent structures like structs), and any import or include statements.
                        Return the result as a JSON object with three keys: 'functions', 'classes', and 'imports'.
                        Each key should have a list of strings as its value, representing the names found.
                        If no items are found for a category, provide an empty list for that category.

                        Code:
                        ```
                        {code}
                        ```

                        Example of desired JSON Output:
                        {{
                        "functions": ["func_name1", "another_function"],
                        "classes": ["ClassName1", "MyStruct"],
                        "imports": ["module_a", "header.h", "library_x"]
                        }}
                        """
            output_schema: Dict[str, str] = {
                "functions": "list of strings, names of functions or equivalent callable units",
                "classes": "list of strings, names of classes, structs, or equivalent data structures",
                "imports": "list of strings, names of imported modules, included libraries/headers, or equivalent dependency statements",
            }
            try:
                llm_analysis = self.client.generate_structured_output(
                    prompt=prompt, output_schema=output_schema
                )
                # Ensure the LLM output conforms to the expected structure, providing defaults
                return {
                    "functions": llm_analysis.get("functions", []),
                    "classes": llm_analysis.get("classes", []),
                    "imports": llm_analysis.get("imports", []),
                    "analyzed_by": "llm",  # Optional: to indicate how it was analyzed
                }
            except Exception as llm_error:
                logger.error(
                    f"LLM analysis failed after AST parsing error: {llm_error}. Snippet: {code[:200]}..."
                )
                return {
                    "error": f"LLM analysis failed: {str(llm_error)}",
                    "functions": [],
                    "classes": [],
                    "imports": [],
                }
        except Exception as e:  # Catch other unexpected errors from ast.walk or elsewhere
            logger.error(f"Unexpected error analyzing code: {e}. Snippet: {code[:200]}...")
            return {
                "error": f"Failed to analyze code: {str(e)}",
                "functions": [],
                "classes": [],
                "imports": [],
            }

    def get_repository_info(self) -> List[Dict]:
        """Fetch and analyze all public repositories."""

        try:
            response: requests.Response = requests.get(
                self.repos_url, headers=self.headers, timeout=30
            )
            response.raise_for_status()
            repos = response.json()

            repo_analyses = []
            for repo in repos:
                name = repo.get("name", "")
                clone_url = repo.get("clone_url", "")
                description = repo.get("description", "")
                language = repo.get("language", "")
                stars = repo.get("stargazers_count", 0)
                forks = repo.get("forks_count", 0)
                updated_at = repo.get("updated_at", "")

                repo_path = os.path.join(self.temp_dir, name)

                # Ensure the directory is clean before cloning
                if os.path.exists(repo_path):
                    try:
                        # On Windows, we might get access denied errors when trying to delete git objects
                        # Just try to continue and let Git handle it or create a new path
                        shutil.rmtree(repo_path, ignore_errors=True)
                        if os.path.exists(repo_path):
                            # If the directory still exists, create a new unique path
                            repo_path = os.path.join(
                                self.temp_dir,
                                f"{name}_{tempfile.mktemp(prefix='', dir='', suffix='').replace('.', '')}",
                            )
                    except Exception as e:
                        # Log but continue with a new unique path
                        logger.warning(
                            f"Error cleaning up existing repo directory {repo_path}: {str(e)}"
                        )
                        repo_path = os.path.join(
                            self.temp_dir,
                            f"{name}_{tempfile.mktemp(prefix='', dir='', suffix='').replace('.', '')}",
                        )

                try:
                    git_repo: git.Repo = git.Repo.clone_from(clone_url, repo_path)
                    self.repos.append(git_repo)  # Track the repo for cleanup
                except Exception as e:
                    logger.error(f"Error cloning {name}: {str(e)}")
                    continue

                repo_summary = []
                for filepath in Path(repo_path).rglob("*"):
                    try:
                        with open(filepath, "r", encoding="utf-8") as file:
                            code = file.read()
                        analysis = self.analyze_python_code(code)
                        repo_summary.append((str(filepath.relative_to(repo_path)), analysis))
                    except Exception as e:
                        logger.error(f"Error reading {filepath}: {e}")

                # Analyze repository structure
                structure = self.analyze_repository_structure(repo_path)

                # Analyze dependencies
                dependencies = self.analyze_dependencies(repo_path)

                # Analyze commit history
                commit_history = self.analyze_commit_history(repo_path)

                repo_analyses.append(
                    {
                        "name": name,
                        "description": description,
                        "language": language,
                        "stars": stars,
                        "forks": forks,
                        "last_updated": updated_at,
                        "code_analysis": repo_summary,
                        "structure": structure,
                        "dependencies": dependencies,
                        "commit_history": commit_history,
                    }
                )

            return repo_analyses
        except Exception as e:
            logger.error(f"Error fetching repository info: {e}")
            return []

    def analyze_repository_structure(self, repo_path: str) -> Dict:
        """Analyze repository structure and organization."""
        try:
            structure = {"total_files": 0, "file_types": {}, "directories": [], "main_files": []}

            for root, dirs, files in os.walk(repo_path):
                rel_path = os.path.relpath(root, repo_path)
                if rel_path != ".":
                    structure["directories"].append(rel_path)

                for file in files:
                    structure["total_files"] += 1
                    ext = os.path.splitext(file)[1]
                    structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1

                    if file.lower() in ["readme.md", "requirements.txt", "setup.py", "main.py"]:
                        structure["main_files"].append(os.path.join(rel_path, file))

            return structure
        except Exception as e:
            logger.error(f"Error analyzing repository structure: {e}")
            return {}

    def analyze_dependencies(self, repo_path: str) -> Dict:
        """Analyze project dependencies."""
        dependencies = {"requirements": [], "setup_py": [], "pyproject_toml": [], "imports": set()}

        try:
            # Check requirements.txt
            req_path = os.path.join(repo_path, "requirements.txt")
            if os.path.exists(req_path):
                with open(req_path, "r") as f:
                    dependencies["requirements"] = [
                        line.strip() for line in f if line.strip() and not line.startswith("#")
                    ]

            # Check setup.py
            setup_path = os.path.join(repo_path, "setup.py")
            if os.path.exists(setup_path):
                with open(setup_path, "r") as f:
                    content = f.read()
                    # Simple regex to find install_requires
                    import re

                    install_requires = re.search(r"install_requires=\[(.*?)\]", content, re.DOTALL)
                    if install_requires:
                        deps = install_requires.group(1).split(",")
                        dependencies["setup_py"] = [
                            dep.strip().strip("'\"") for dep in deps if dep.strip()
                        ]
            # Check pyproject.toml
            pyproject_path = os.path.join(repo_path, "pyproject.toml")
            if os.path.exists(pyproject_path):
                try:
                    with open(pyproject_path, "rb") as f:  # tomllib expects bytes
                        data = tomllib.load(f)

                    # Standard PEP 621 dependencies
                    if "project" in data and "dependencies" in data["project"]:
                        if isinstance(data["project"]["dependencies"], list):
                            dependencies["pyproject_toml"].extend(
                                [
                                    dep.split("==")[0]
                                    .split(">=")[0]
                                    .split("<=")[0]
                                    .split("!=")[0]
                                    .split("~=")[0]
                                    .strip()
                                    for dep in data["project"]["dependencies"]
                                ]
                            )

                    # Poetry specific dependencies
                    if (
                        "tool" in data
                        and "poetry" in data["tool"]
                        and "dependencies" in data["tool"]["poetry"]
                    ):
                        if isinstance(data["tool"]["poetry"]["dependencies"], dict):
                            # Add keys (package names), ignore 'python' itself
                            dependencies["pyproject_toml"].extend(
                                [
                                    pkg
                                    for pkg in data["tool"]["poetry"]["dependencies"].keys()
                                    if pkg.lower() != "python"
                                ]
                            )
                except Exception as e:
                    logger.error(f"Error parsing {pyproject_path}: {e}")

            # Collect all imports from Python files
            for filepath in Path(repo_path).rglob("*.py"):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    dependencies["imports"].add(alias.name.split(".")[0])
                            elif isinstance(node, ast.ImportFrom):
                                if (
                                    node.module
                                ):  # For ast.ImportFrom, node.module can be None for relative imports
                                    dependencies["imports"].add(node.module.split(".")[0])
                except SyntaxError as e:
                    logger.warning(
                        f"SyntaxError analyzing imports in {filepath}: {e}. Skipping this file for import analysis."
                    )
                except (
                    Exception
                ) as e:  # Catch other potential errors during file processing or AST walking
                    logger.error(f"Error analyzing imports in {filepath}: {e}")

            dependencies["imports"] = list(dependencies["imports"])
            dependencies["pyproject_toml"] = list(set(dependencies["pyproject_toml"]))
            return dependencies
        except Exception as e:
            logger.error(f"Error analyzing dependencies: {e}")
            return {}

    def analyze_commit_history(self, repo_path: str) -> Dict:
        """Analyze repository commit history."""
        try:
            repo = git.Repo(repo_path)
            commits = list(repo.iter_commits())

            history = {
                "total_commits": len(commits),
                "first_commit": commits[-1].committed_datetime.isoformat() if commits else None,
                "last_commit": commits[0].committed_datetime.isoformat() if commits else None,
                "commit_frequency": {},
                "contributors": set(),
            }

            # Analyze commit frequency by month
            for commit in commits:
                date = commit.committed_datetime
                month_key = f"{date.year}-{date.month:02d}"
                history["commit_frequency"][month_key] = (
                    history["commit_frequency"].get(month_key, 0) + 1
                )
                history["contributors"].add(commit.author.name)

            history["contributors"] = list(history["contributors"])
            return history
        except Exception as e:
            logger.error(f"Error analyzing commit history: {e}")
            return {}

    def extract_skills(self, repo_analyses: List[Dict]) -> List[Dict]:
        """Extract skills from repository analyses."""
        try:
            # Prepare a simplified version of the repository data
            simplified_repos = []
            for repo in repo_analyses:
                simplified_repo = {
                    "name": repo.get("name", ""),
                    "description": repo.get("description", ""),
                    "languages": repo.get("languages", []),
                    "dependencies": repo.get("dependencies", {}),
                    "code_analysis": repo.get("code_analysis", []),
                }
                simplified_repos.append(simplified_repo)

            # Sort repositories by stars and update date to prioritize the most relevant ones
            simplified_repos.sort(
                key=lambda x: (x.get("stars", 0), x.get("updated_at", "")), reverse=True
            )

            # Take only the top 5 most relevant repositories to reduce input size
            top_repos = simplified_repos[:5]

            prompt = f"""Based on these GitHub repositories, extract technical skills:

Repository Data:
{json.dumps(top_repos, indent=2)}

Format as JSON:
{{
    "skills": [
        {{
            "name": "string",
            "category": "Programming Language/Framework/Tool",
            "proficiency": 3
        }}
    ]
}}"""

            # Generate response with default parameters since Ollama client doesn't support max_tokens/timeout
            response = self.client.generate_text(prompt)
            try:
                # Validate JSON response
                parsed_data = json.loads(response)
                return parsed_data.get("skills", [])
            except json.JSONDecodeError:
                # Return empty skills list if parsing fails
                return []
        except Exception as e:
            logger.error(f"Error extracting skills: {str(e)}")
            return []

    def extract_work_experience(self, repo_analyses: List[Dict]) -> str:
        """Extract work experience from repository analyses."""
        # Prepare a simplified version of the repository data
        simplified_repos = []
        for repo in repo_analyses:
            simplified_repo = {
                "name": repo.get("name", ""),
                "description": repo.get("description", ""),
                "languages": repo.get("languages", []),
                "topics": repo.get("topics", []),
                "created_at": repo.get("created_at", ""),
                "updated_at": repo.get("updated_at", ""),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
            }
            simplified_repos.append(simplified_repo)

        # Sort repositories by stars and update date to prioritize the most relevant ones
        simplified_repos.sort(key=lambda x: (x["stars"], x["updated_at"]), reverse=True)

        # Take only the top 5 most relevant repositories to reduce input size
        top_repos = simplified_repos[:5]

        prompt = f"""Based on these GitHub repositories, extract professional experience:

Repository Data:
{json.dumps(top_repos, indent=2)}

Format as JSON:
{{
    "work_experiences": [
        {{
            "company": "Personal/Open Source",
            "position": "Software Developer",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM",
            "description": "string",
            "technologies": ["string"]
        }}
    ],
    "skills": [
        {{
            "name": "string",
            "category": "Programming Language/Framework/Tool",
            "proficiency": 3
        }}
    ]
}}"""

        try:
            # Generate response with default parameters since Ollama client doesn't support max_tokens/timeout
            response = self.client.generate_text(prompt)
            try:
                # Validate JSON response
                parsed_data = json.loads(response)

                # Add repository stats
                parsed_data["total_commits"] = sum(repo.get("commits", 0) for repo in repo_analyses)
                parsed_data["total_stars"] = sum(
                    repo.get("stargazers_count", 0) for repo in repo_analyses
                )

                # Aggregate languages across all repositories
                all_languages = {}
                for repo in repo_analyses:
                    for lang, bytes_count in repo.get("languages", {}).items():
                        all_languages[lang] = all_languages.get(lang, 0) + bytes_count

                # Calculate language percentages
                total_bytes = (
                    sum(all_languages.values()) if all_languages else 1
                )  # Avoid division by zero
                parsed_data["languages"] = {
                    lang: {
                        "bytes": bytes_count,
                        "percentage": round((bytes_count / total_bytes) * 100, 2),
                    }
                    for lang, bytes_count in all_languages.items()
                }

                return json.dumps(parsed_data)
            except json.JSONDecodeError:
                # Return a minimal valid response if parsing fails
                return json.dumps(
                    {
                        "work_experiences": [],
                        "skills": [],
                        "total_commits": sum(repo.get("commits", 0) for repo in repo_analyses),
                        "total_stars": sum(
                            repo.get("stargazers_count", 0) for repo in repo_analyses
                        ),
                        "languages": {},
                    }
                )
        except Exception as e:
            raise Exception(f"Failed to extract work experience: {str(e)}")

    def get_profile_info(self) -> Dict:
        """Fetch user profile information from GitHub API."""
        try:

            response: requests.Response = requests.get(self.url_user, headers=self.headers)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.error(f"Error fetching GitHub profile info: {str(e)}")
            return {}

    def get_contribution_data(self) -> Dict:
        """Fetch contribution data from GitHub API."""
        try:
            # Get repository languages and stats

            repos_response = requests.get(self.repos_url, headers=self.headers)
            repos_response.raise_for_status()
            repos = repos_response.json()

            # Aggregate languages across repositories
            languages = {}
            total_stars = 0
            total_commits = 0

            for repo in repos:
                # Add stars
                total_stars += repo.get("stargazers_count", 0)

                # Get language data
                lang_url = repo.get("languages_url")
                if lang_url:
                    try:
                        # Use the same headers with auth token
                        lang_response = requests.get(lang_url, headers=self.headers)
                        if lang_response.status_code == 200:
                            repo_langs = lang_response.json()
                            for lang, bytes_count in repo_langs.items():
                                languages[lang] = languages.get(lang, 0) + bytes_count
                    except Exception as e:
                        logger.warning(
                            f"Error fetching language data for {repo.get('name')}: {str(e)}"
                        )
                        continue

            # Get contribution graph data (this requires authentication)
            # For now, we'll just return what we have
            return {
                "total_stars": total_stars,
                "total_commits": total_commits,  # This would require additional API calls to get accurate commit counts
                "languages": languages,
            }
        except Exception as e:
            logger.error(f"Error fetching GitHub contribution data: {str(e)}")
            return {"total_stars": 0, "total_commits": 0, "languages": {}}

    def import_profile(self) -> str:
        """Import profile data from GitHub"""
        try:
            # Get user profile info
            profile_data = self.get_profile_info()
            if not profile_data:
                return json.dumps({"error": "Failed to fetch GitHub profile data"})

            # Get repository info
            repo_data = self.get_repository_info()
            if not repo_data:
                return json.dumps({"error": "Failed to fetch repository data"})

            # Get contribution data
            contribution_data = self.get_contribution_data()
            if not contribution_data:
                return json.dumps({"error": "Failed to fetch contribution data"})

            # Extract skills from repositories
            skills = self.extract_skills(repo_data)

            # Combine all data
            combined_data = {
                "username": self.github_username,
                "profile_url": self.url_user,
                "avatar_url": profile_data.get("avatar_url"),
                "bio": profile_data.get("bio"),
                "location": profile_data.get("location"),
                "company": profile_data.get("company"),
                "blog": profile_data.get("blog"),
                "twitter_username": profile_data.get("twitter_username"),
                "public_repos": profile_data.get("public_repos", 0),
                "public_gists": profile_data.get("public_gists", 0),
                "followers": profile_data.get("followers", 0),
                "following": profile_data.get("following", 0),
                "created_at": profile_data.get("created_at"),
                "updated_at": profile_data.get("updated_at"),
                "total_commits": contribution_data.get("total_commits", 0),
                "total_stars": contribution_data.get("total_stars", 0),
                "languages": contribution_data.get("languages", {}),
                "skills": skills,
                "repositories": repo_data,
            }

            return json.dumps(combined_data)

        except Exception as e:
            logger.error(f"Error in import_profile: {str(e)}")
            return json.dumps({"error": str(e)})

    def transform_repos_to_projects(self, repo_data: List[Dict], user_profile) -> List[Dict]:
        """
        Transform GitHub repositories into project records.

        Args:
            repo_data (List[Dict]): List of repository data from GitHub
            user_profile: The UserProfile instance to associate projects with

        Returns:
            List[Dict]: List of project dictionaries ready to be created
        """
        projects = []

        try:
            for repo in repo_data:
                # Skip if repo is a fork to avoid duplicating other people's projects
                if repo.get("fork", False):
                    continue

                # Convert GitHub's datetime string to date object
                updated_at = (
                    datetime.strptime(repo.get("last_updated", "").split("T")[0], "%Y-%m-%d").date()
                    if repo.get("last_updated")
                    else None
                )

                # Extract technologies from repo
                technologies = []
                if repo.get("language"):
                    technologies.append(repo["language"])
                if repo.get("dependencies"):
                    # Add main dependencies
                    if repo["dependencies"].get("requirements"):
                        technologies.extend(
                            [dep.split("==")[0] for dep in repo["dependencies"]["requirements"]]
                        )
                    if repo["dependencies"].get("setup_py"):
                        technologies.extend(
                            [dep.split("==")[0] for dep in repo["dependencies"]["setup_py"]]
                        )

                # Remove duplicates and join with commas
                technologies = ", ".join(sorted(set(filter(None, technologies))))

                project_data = {
                    "profile": user_profile,
                    "title": repo.get("name", ""),
                    "description": repo.get("description", "")
                    or f"A {repo.get('language', 'software')} project.",
                    "technologies": technologies,
                    "github_url": f"https://github.com/{self.github_username}/{repo.get('name')}",
                    "live_url": "",  # GitHub API doesn't provide homepage URL in our current data
                    "start_date": (
                        datetime.strptime(
                            repo.get("commit_history", {}).get("first_commit", "").split("T")[0],
                            "%Y-%m-%d",
                        ).date()
                        if repo.get("commit_history", {}).get("first_commit")
                        else updated_at
                    ),
                    "end_date": None,  # Since it's a GitHub repo, we'll consider it ongoing
                    "current": True,  # Mark as current since it's from GitHub
                    # Use stars as a proxy for order (more stars = higher priority)
                    "order": repo.get("stars", 0),
                }

                projects.append(project_data)

            # Sort projects by order (stars) descending
            projects.sort(key=lambda x: x["order"], reverse=True)

            return projects

        except Exception as e:
            logger.error(f"Error transforming repos to projects: {str(e)}")
            return []


class ResumeImporter:
    """Class for handling resume uploads and parsing."""

    EXCLUSION_PROPS_PROF: List[str] = [
        "id",
        "user",
        "created_at",
        "updated_at",
        "last_github_refresh",
        "github_data",
        "parsed_resume_data",
        "resume",
    ]
    EXCLUSION_PROPS: List[str] = [
        "id",
        "user",
        "created_at",
        "updated_at",
        "profile",
        "order",
        "credential_id",
    ]

    def __init__(self, uploaded_resume_file: UploadedFile) -> None:
        self.google_client = GoogleClient(model=settings.PRO_GOOGLE_MODEL)

        self._temp_file_path: Optional[str] = None  # Store path of the temp file

        if not isinstance(uploaded_resume_file, UploadedFile):
            raise TypeError("ResumeImporter expects an Django UploadedFile object.")

        original_suffix = Path(uploaded_resume_file.name).suffix
        # Create a temporary file. It's opened in 'w+b' mode.
        # delete=False means we are responsible for deleting it.
        temp_f = tempfile.NamedTemporaryFile(delete=False, suffix=original_suffix)
        try:
            for chunk in uploaded_resume_file.chunks():
                temp_f.write(chunk)
            temp_f.flush()  # Ensure all data is written to disk
            self._temp_file_path = temp_f.name  # Get the path (string)
        except Exception as e:
            # Clean up if init fails mid-way
            if Path(temp_f.name).exists():  # Path(temp_f.name) is correct here
                try:
                    os.remove(temp_f.name)
                except OSError:  # pragma: no cover
                    pass  # Ignore if removal fails for some reason
            raise Exception(f"Failed to process uploaded resume file: {e}")
        finally:
            if not temp_f.closed:  # Ensure it's closed
                temp_f.close()

        # Now validate the path of the temp file.
        # self._temp_file_path is a string path.
        self.validated_resume_path: Path = self._validate_resume_path(self._temp_file_path)

    def _cleanup_temp_file(self):
        if self._temp_file_path:
            try:
                temp_path = Path(self._temp_file_path)
                if temp_path.exists():
                    os.remove(temp_path)
                    logger.debug(f"Temporary resume file {self._temp_file_path} removed.")
            except Exception as e:  # pragma: no cover
                logger.error(f"Error cleaning up temporary resume file {self._temp_file_path}: {e}")
            self._temp_file_path = None

    def _validate_resume_path(self, file_path_str: str) -> Path:
        """Validate the resume file."""

        # file_path_str is expected to be a string path.
        file_path = Path(file_path_str)  # Converts the string path to a Path object.

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.suffix.lower() not in [".pdf", ".doc", ".docx"]:
            raise ValueError("Unsupported file format. Please upload PDF or Word document.")

        if not file_path.is_file():
            raise IsADirectoryError(f"The path {file_path} is a directory, not a file.")

        if not file_path.is_absolute():
            file_path = file_path.resolve() or file_path.absolute()

        return file_path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup_temp_file()

    def parse_with_llm(self, resume_file) -> Dict:
        """Parse resume text using ChatGPT to extract structured information."""
        try:

            # Pass exclude_fields to get_schema to remove 'id' and 'user'
            user_profile_schema_properties = json.dumps(
                UserProfile.get_schema(exclude_fields=self.EXCLUSION_PROPS_PROF)["properties"],
                indent=2,
            )
            work_experience_schema_properties = json.dumps(
                WorkExperience.get_schema(exclude_fields=self.EXCLUSION_PROPS)["properties"],
                indent=2,
            )
            education_schema_properties = json.dumps(
                Education.get_schema(exclude_fields=self.EXCLUSION_PROPS)["properties"],
                indent=2,
            )
            project_schema_properties = json.dumps(
                Project.get_schema(exclude_fields=self.EXCLUSION_PROPS)["properties"],
                indent=2,
            )
            certification_schema_properties = json.dumps(
                Certification.get_schema(exclude_fields=self.EXCLUSION_PROPS)["properties"],
                indent=2,
            )
            skill_schema_properties = json.dumps(
                Skill.get_schema(exclude_fields=self.EXCLUSION_PROPS)["properties"],
                indent=2,
            )
            publication_schema_properties = json.dumps(
                Publication.get_schema(exclude_fields=self.EXCLUSION_PROPS)["properties"],
                indent=2,
            )

            # First, get basic information
            all_prompt = f"""
                    You are an expert resume parsing assistant. Your task is to extract information from the provided resume text and structure it as a single, valid JSON object.
                    Adhere strictly to the specified field names and data types.

                    **Output Format:**
                    Your entire response MUST be a single JSON object. Do not include any text, explanations, or markdown before or after the JSON.

                    **JSON Structure and Field Definitions:**

                    1.  `"basic_info"`: (Object) Contains general information about the candidate.
                        *   Properties for this object:
                            {user_profile_schema_properties}

                    2.  `"work_experiences"`: (List of Objects) Each object in the list represents a distinct work experience entry.
                        *   Properties for each work experience object:
                            {work_experience_schema_properties}
                        *   Example of the list structure: `[ {{ "company": "Example Corp", "position": "Developer", ... }}, {{ ... }} ]`

                    3.  `"education"`: (List of Objects) Each object in the list represents an education entry.
                        *   Properties for each education object:
                            {education_schema_properties}
                        *   Example of the list structure: `[ {{ "institution": "University of Example", "degree": "B.S.", ... }}, {{ ... }} ]`

                    4.  `"projects"`: (List of Objects) Each object in the list represents a project.
                        *   Properties for each project object:
                            {project_schema_properties}
                        *   Example of the list structure: `[ {{ "title": "Project X", "description": "...", ... }}, {{ ... }} ]`

                    5.  `"certifications"`: (List of Objects) Each object in the list represents a certification.
                        *   Properties for each certification object:
                            {certification_schema_properties}
                        *   Example of the list structure: `[ {{ "name": "Certified Example Professional", "issuer": "...", ... }}, {{ ... }} ]`

                    6.  `"skills"`: (List of Objects) Each object in the list represents a skill.
                        *   Properties for each skill object:
                            {skill_schema_properties}
                        *   Example of the list structure: `[ {{ "name": "Python", "category": "Programming Language", ... }}, {{ ... }} ]`

                    7.  `"publications"`: (List of Objects) Each object in the list represents a publication.
                        *   Properties for each publication object:
                            {publication_schema_properties}
                        *   Example of the list structure: `[ {{ "title": "Research Paper on Example", "authors": "...", ... }}, {{ ... }} ]`

                    **Data Handling Guidelines:**
                    *   If information for a specific field is not found in the resume, use `null` for object or string fields. For fields expecting a list, use an empty list `[]`.
                    *   For date fields (e.g., `start_date`, `end_date`, `publication_date`):
                        *   If the full date is available, format it as "YYYY-MM-DD".
                        *   If only year and month are available, use "YYYY-MM".
                        *   If only year is available, use "YYYY".
                        *   If a date is ongoing (e.g., "Present" for an end date), represent the `end_date` as `null`. If the schema includes a "current" boolean field (like in WorkExperience or Education), ensure it is set to `true`.
                    *   Ensure all string values are properly escaped within the JSON.

                    The resume text will be provided next. Begin your JSON output immediately.
                    """

            response = self.google_client.generate_text(
                prompt=[resume_file, all_prompt], temperature=0.1
            )
            try:
                if "```json" in response:
                    response = response.replace("```json", "").replace("```", "")
                response: dict = json.loads(response)
            except Exception as e:
                logger.error(f"Error parsing response: {str(e)}")

            return response

        except Exception as e:
            raise Exception(f"Error parsing resume with ChatGPT: {str(e)}")

    def parse_resume(self) -> Dict:
        """Parse the resume and return structured data."""
        try:
            # self.validated_resume_path should be a Path object from _validate_resume_path
            if (
                not hasattr(self, "validated_resume_path")
                or not self.validated_resume_path.exists()
            ):
                # .exists() is called on self.validated_resume_path (a Path object)
                raise FileNotFoundError("Validated resume file path does not exist or was not set.")

            google_uploaded_file: File = self.google_client.upload_file(self.validated_resume_path)

            # Parse the text using ChatGPT
            parsed_data = self.parse_with_llm(google_uploaded_file)

            return parsed_data

        except Exception as e:
            raise Exception(f"Error parsing resume: {str(e)}")


class LinkedInImporter:
    """Class for handling LinkedIn profile imports."""

    def __init__(self, linkedin_url: str):
        self.linkedin_url: str = self._normalize_linkedin_url(linkedin_url)
        self.client = GoogleClient()  # Assuming this exists in your codebase
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _normalize_linkedin_url(self, url: str) -> str:
        """Normalize LinkedIn URL to ensure it's properly formatted."""
        if not url:
            raise ValueError("LinkedIn URL cannot be empty")

        # Remove whitespace
        url = url.strip()

        # Add https:// if no protocol specified
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # Ensure it's a LinkedIn URL
        parsed = urlparse(url)
        if "linkedin.com" not in parsed.netloc.lower():
            raise ValueError("URL must be a LinkedIn profile URL")

        # Convert to standard format
        if "/in/" not in url:
            raise ValueError("URL must be a LinkedIn profile URL (should contain '/in/')")

        # Remove query parameters and fragments for cleaner URLs
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        # Ensure URL ends properly (remove trailing slash if not needed)
        if clean_url.endswith("/") and clean_url.count("/") > 4:
            clean_url = clean_url.rstrip("/")

        return clean_url

    def _validate_response(self, response: requests.Response) -> bool:
        """Validate the response from LinkedIn."""
        if response.status_code == 999:
            raise Exception(
                "LinkedIn blocked the request (Error 999). Consider using LinkedIn API instead."
            )

        if response.status_code == 404:
            raise Exception("LinkedIn profile not found. Please check the URL.")

        if response.status_code != 200:
            raise Exception(f"Failed to fetch LinkedIn profile: HTTP {response.status_code}")

        # Check if we got a CAPTCHA or login page
        if "challenge" in response.url.lower() or "login" in response.url.lower():
            raise Exception(
                "LinkedIn requires authentication or CAPTCHA. Consider using LinkedIn API."
            )

        return True

    def scrape_profile(self) -> Dict:
        """
        Scrape LinkedIn profile data.

        WARNING: This method violates LinkedIn's Terms of Service.
        Consider using LinkedIn's official API instead.
        """
        try:
            # Add random delay to avoid rate limiting
            delay = random.uniform(3, 8)
            time.sleep(delay)

            logger.info(f"Attempting to scrape LinkedIn profile: {self.linkedin_url}")
            # TODO it needs LinkedIn API to scrape user's profile
            response: requests.Response = requests.get(self.linkedin_url, timeout=30)
            self._validate_response(response)

            soup = BeautifulSoup(response.text, "html.parser")

            # Check if we actually got profile content
            if not soup.find("h1") and not soup.find("title"):
                raise Exception("Unable to parse LinkedIn profile content")

            # Extract profile data
            profile_data = {
                "url": self.linkedin_url,
                "name": self._extract_name(soup),
                "headline": self._extract_headline(soup),
                "location": self._extract_location(soup),
                "about": self._extract_about(soup),
                "experience": self._extract_experience(soup),
                "education": self._extract_education(soup),
                "skills": self._extract_skills(soup),
                "certifications": self._extract_certifications(soup),
                "publications": self._extract_publications(soup),
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            # Log what was successfully extracted
            extracted_fields = [k for k, v in profile_data.items() if v]
            logger.info(f"Successfully extracted fields: {extracted_fields}")

            return profile_data

        except Exception as e:
            logger.error(f"Error scraping LinkedIn profile {self.linkedin_url}: {str(e)}")
            raise Exception(f"Error scraping LinkedIn profile: {str(e)}")

    def _extract_name(self, soup) -> str:
        """Extract name from LinkedIn profile."""
        try:
            # Try multiple selectors for name
            selectors = [
                "h1.text-heading-xlarge",
                "h1[data-test-id='profile-name']",
                "h1.break-words",
                ".pv-text-details__left-panel h1",
                "h1",
            ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element and element.text.strip():
                    return element.text.strip()
            return ""
        except Exception as e:
            logger.debug(f"Error extracting name: {e}")
            return ""

    def _extract_headline(self, soup) -> str:
        """Extract headline from LinkedIn profile."""
        try:
            selectors = [
                ".text-body-medium.break-words",
                ".pv-text-details__left-panel .text-body-medium",
                "[data-test-id='profile-headline']",
                ".pv-top-card--list-bullet .pv-entity__summary-info h2",
            ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element and element.text.strip():
                    return element.text.strip()
            return ""
        except Exception as e:
            logger.debug(f"Error extracting headline: {e}")
            return ""

    def _extract_location(self, soup) -> str:
        """Extract location from LinkedIn profile."""
        try:
            selectors = [
                ".text-body-small.inline.t-black--light.break-words",
                ".pv-text-details__left-panel .text-body-small",
                "[data-test-id='profile-location']",
            ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element and element.text.strip():
                    return element.text.strip()
            return ""
        except Exception as e:
            logger.debug(f"Error extracting location: {e}")
            return ""

    def _extract_about(self, soup) -> str:
        """Extract about section from LinkedIn profile."""
        try:
            selectors = [
                "#about + * .pv-shared-text-with-see-more",
                ".pv-about-section .pv-about__summary-text",
                "[data-test-id='about-section'] .text-body-medium",
            ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element and element.text.strip():
                    return element.text.strip()
            return ""
        except Exception as e:
            logger.debug(f"Error extracting about: {e}")
            return ""

    def _extract_experience(self, soup) -> List[Dict]:
        """Extract work experience from LinkedIn profile."""
        experiences = []
        try:
            # Try multiple selectors for experience section
            experience_sections = soup.select(
                "#experience + *, .pv-profile-section.experience-section"
            )

            for section in experience_sections:
                exp_items = section.select(".pv-entity__summary-info, .experience-item")

                for exp in exp_items:
                    experience = {
                        "title": self._safe_extract_text(exp, "h3, .pv-entity__summary-info h3"),
                        "company": self._safe_extract_text(
                            exp, ".pv-entity__secondary-title, .company-name"
                        ),
                        "date_range": self._safe_extract_text(
                            exp, ".pv-entity__date-range, .date-range"
                        ),
                        "description": self._safe_extract_text(
                            exp, ".pv-entity__description, .description"
                        ),
                        "location": self._safe_extract_text(exp, ".pv-entity__location, .location"),
                    }

                    if experience["title"] or experience["company"]:
                        experiences.append(experience)

        except Exception as e:
            logger.debug(f"Error extracting experience: {e}")

        return experiences

    def _extract_education(self, soup) -> List[Dict]:
        """Extract education from LinkedIn profile."""
        education = []
        try:
            education_sections = soup.select(
                "#education + *, .pv-profile-section.education-section"
            )

            for section in education_sections:
                edu_items = section.select(".pv-entity__summary-info, .education-item")

                for edu in edu_items:
                    education_item = {
                        "institution": self._safe_extract_text(edu, "h3, .pv-entity__school-name"),
                        "degree": self._safe_extract_text(edu, ".pv-entity__degree-name, .degree"),
                        "field": self._safe_extract_text(edu, ".pv-entity__fos, .field-of-study"),
                        "date_range": self._safe_extract_text(
                            edu, ".pv-entity__dates, .date-range"
                        ),
                        "description": self._safe_extract_text(
                            edu, ".pv-entity__description, .description"
                        ),
                    }

                    if education_item["institution"]:
                        education.append(education_item)

        except Exception as e:
            logger.debug(f"Error extracting education: {e}")

        return education

    def _extract_skills(self, soup) -> List[str]:
        """Extract skills from LinkedIn profile."""
        skills = []
        try:
            skill_sections = soup.select(
                "#skills + *, .pv-profile-section.pv-skill-categories-section"
            )

            for section in skill_sections:
                skill_elements = section.select(".pv-skill-category-entity__name, .skill-name")
                for skill in skill_elements:
                    skill_text = skill.text.strip()
                    if skill_text and skill_text not in skills:
                        skills.append(skill_text)

        except Exception as e:
            logger.debug(f"Error extracting skills: {e}")

        return skills

    def _extract_certifications(self, soup) -> List[Dict]:
        """Extract certifications from LinkedIn profile."""
        certifications = []
        try:
            cert_sections = soup.select(
                "#certifications + *, .pv-profile-section.certifications-section"
            )

            for section in cert_sections:
                cert_items = section.select(".pv-entity__summary-info, .certification-item")

                for cert in cert_items:
                    certification = {
                        "name": self._safe_extract_text(cert, "h3, .pv-entity__summary-title"),
                        "issuer": self._safe_extract_text(
                            cert, ".pv-entity__secondary-title, .issuer"
                        ),
                        "date": self._safe_extract_text(cert, ".pv-entity__date-range, .date"),
                        "credential_id": self._safe_extract_text(
                            cert, ".pv-entity__credential-id, .credential-id"
                        ),
                    }

                    if certification["name"]:
                        certifications.append(certification)

        except Exception as e:
            logger.debug(f"Error extracting certifications: {e}")

        return certifications

    def _extract_publications(self, soup) -> List[Dict]:
        """Extract publications from LinkedIn profile."""
        publications = []
        try:
            pub_sections = soup.select(
                "#publications + *, .pv-profile-section.publications-section"
            )

            for section in pub_sections:
                pub_items = section.select(".pv-entity__summary-info, .publication-item")

                for pub in pub_items:
                    publication = {
                        "title": self._safe_extract_text(pub, "h3, .pv-entity__summary-title"),
                        "publisher": self._safe_extract_text(
                            pub, ".pv-entity__secondary-title, .publisher"
                        ),
                        "date": self._safe_extract_text(pub, ".pv-entity__date-range, .date"),
                        "description": self._safe_extract_text(
                            pub, ".pv-entity__description, .description"
                        ),
                    }

                    if publication["title"]:
                        publications.append(publication)

        except Exception as e:
            logger.debug(f"Error extracting publications: {e}")

        return publications

    def _safe_extract_text(self, parent_element, selector: str) -> str:
        """Safely extract text from an element using CSS selector."""
        try:
            element = parent_element.select_one(selector)
            return element.text.strip() if element else ""
        except:
            return ""

    def parse_linkedin_data(self) -> Optional[Dict]:
        """
        Parse LinkedIn profile data.

        Returns:
            dict: Processed LinkedIn data with success flag, or None if failed
        """
        try:
            logger.info(f"Starting LinkedIn data parsing for: {self.linkedin_url}")
            data = self.scrape_profile()

            result = {
                "raw_data": data,
                "success": True,
                "profile_url": self.linkedin_url,
                "extraction_summary": {
                    "has_name": bool(data.get("name")),
                    "has_headline": bool(data.get("headline")),
                    "has_about": bool(data.get("about")),
                    "experience_count": len(data.get("experience", [])),
                    "education_count": len(data.get("education", [])),
                    "skills_count": len(data.get("skills", [])),
                    "certifications_count": len(data.get("certifications", [])),
                },
            }

            logger.info(f"Successfully parsed LinkedIn data: {result['extraction_summary']}")
            return result

        except Exception as e:
            logger.error(f"Error parsing LinkedIn data for {self.linkedin_url}: {str(e)}")
            return {
                "raw_data": {},
                "success": False,
                "error": str(e),
                "profile_url": self.linkedin_url,
            }

    @classmethod
    def is_valid_linkedin_url(cls, url: str) -> bool:
        """Check if a URL is a valid LinkedIn profile URL."""
        try:
            normalized = cls._normalize_linkedin_url(None, url)
            return True
        except ValueError:
            return False

    def __str__(self) -> str:
        return f"LinkedInImporter(url='{self.linkedin_url}')"

    def __repr__(self) -> str:
        return self.__str__()
