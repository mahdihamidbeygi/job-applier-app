import base64
import io
import json
import logging
import mimetypes
import os
import random
import re
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import git
import httpx
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import models as django_models
from google.genai.types import File

from core.models.profile import (
    Certification,
    Education,
    Project,
    Publication,
    Skill,
    UserProfile,
    WorkExperience,
)
from core.utils.llm_clients import GoogleClient

# For parsing pyproject.toml
try:
    import tomllib  # Python 3.11+
except ImportError:
    import toml as tomllib  # Fallback for older Python versions (requires `pip install toml`)

# Configure logging
logger = logging.getLogger(__name__)


class CodeFileFilter:
    def __init__(self):
        # Existing extension exclusions
        self.EXCLUSION_EXTS = list(
            set(
                {
                    # MEDIA FILES
                    # Images
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".gif",
                    ".bmp",
                    ".tiff",
                    ".tif",
                    ".svg",
                    ".webp",
                    ".ico",
                    ".psd",
                    ".ai",
                    ".eps",
                    ".raw",
                    ".cr2",
                    ".nef",
                    ".orf",
                    ".sr2",
                    ".dng",
                    ".heic",
                    ".heif",
                    ".avif",
                    ".jxl",
                    # Audio
                    ".mp3",
                    ".wav",
                    ".flac",
                    ".aac",
                    ".ogg",
                    ".wma",
                    ".m4a",
                    ".opus",
                    ".ape",
                    ".ac3",
                    ".dts",
                    ".au",
                    ".aiff",
                    ".amr",
                    ".3gp",
                    ".m4p",
                    ".m4b",
                    # Video
                    ".mp4",
                    ".avi",
                    ".mkv",
                    ".mov",
                    ".wmv",
                    ".flv",
                    ".webm",
                    ".m4v",
                    ".3gp",
                    ".ogv",
                    ".asf",
                    ".rm",
                    ".rmvb",
                    ".vob",
                    ".ts",
                    ".mts",
                    ".m2ts",
                    ".divx",
                    ".xvid",
                    ".f4v",
                    ".mpg",
                    ".mpeg",
                    ".m2v",
                    # DOCUMENT FILES
                    # Office Documents
                    ".doc",
                    ".docx",
                    ".xls",
                    ".xlsx",
                    ".ppt",
                    ".pptx",
                    ".odt",
                    ".ods",
                    ".odp",
                    ".rtf",
                    ".pages",
                    ".numbers",
                    ".key",
                    # PDF and eBooks
                    ".pdf",
                    ".epub",
                    ".mobi",
                    ".azw",
                    ".azw3",
                    ".fb2",
                    ".lit",
                    ".pdb",
                    ".djvu",
                    # Text Documents (non-code)
                    ".txt",
                    ".docm",
                    ".dotx",
                    ".dotm",
                    ".xlsm",
                    ".xltx",
                    ".xltm",
                    ".xlsb",
                    ".pptm",
                    ".potx",
                    ".potm",
                    ".ppsx",
                    ".ppsm",
                    # ARCHIVE FILES
                    ".zip",
                    ".rar",
                    ".7z",
                    ".tar",
                    ".gz",
                    ".bz2",
                    ".xz",
                    ".tar.gz",
                    ".tar.bz2",
                    ".tar.xz",
                    ".tgz",
                    ".tbz2",
                    ".txz",
                    ".cab",
                    ".arj",
                    ".lzh",
                    ".ace",
                    ".iso",
                    ".dmg",
                    ".img",
                    ".bin",
                    ".cue",
                    ".nrg",
                    ".mdf",
                    ".udf",
                    # EXECUTABLE FILES
                    ".exe",
                    ".msi",
                    ".app",
                    ".deb",
                    ".rpm",
                    ".pkg",
                    ".dmg",
                    ".run",
                    ".bin",
                    ".com",
                    ".scr",
                    ".bat",
                    ".cmd",
                    ".vbs",
                    ".ps1",
                    ".sh",
                    # SYSTEM FILES
                    ".dll",
                    ".so",
                    ".dylib",
                    ".sys",
                    ".drv",
                    ".ocx",
                    ".cpl",
                    ".scr",
                    ".tmp",
                    ".temp",
                    ".cache",
                    ".log",
                    ".bak",
                    ".old",
                    ".orig",
                    ".swp",
                    ".swo",
                    ".~",
                    # DATABASE FILES (Binary)
                    ".db",
                    ".sqlite",
                    ".sqlite3",
                    ".mdb",
                    ".accdb",
                    ".dbf",
                    ".frm",
                    ".myd",
                    ".myi",
                    ".ibd",
                    # FONT FILES
                    ".ttf",
                    ".otf",
                    ".woff",
                    ".woff2",
                    ".eot",
                    ".fon",
                    ".fnt",
                    # 3D AND CAD FILES
                    ".obj",
                    ".fbx",
                    ".dae",
                    ".3ds",
                    ".max",
                    ".blend",
                    ".c4d",
                    ".ma",
                    ".mb",
                    ".dwg",
                    ".dxf",
                    ".step",
                    ".stp",
                    ".iges",
                    ".igs",
                    ".stl",
                    ".ply",
                    ".x3d",
                    # GAME FILES
                    ".unity",
                    ".unitypackage",
                    ".pak",
                    ".vpk",
                    ".bsp",
                    ".wad",
                    ".pk3",
                    ".pk4",
                    ".sav",
                    ".dat",
                    ".gam",
                    ".rom",
                    ".iso",
                    # ENCRYPTED/PROTECTED FILES
                    ".p12",
                    ".pfx",
                    ".cer",
                    ".crt",
                    ".der",
                    ".pem",
                    ".key",
                    ".pub",
                    ".sig",
                    ".gpg",
                    ".pgp",
                    ".asc",
                    # BACKUP FILES
                    ".bak",
                    ".backup",
                    ".old",
                    ".orig",
                    ".save",
                    ".autosave",
                    ".recover",
                    ".~bak",
                    ".tmp",
                    # TEMPORARY/CACHE FILES
                    ".tmp",
                    ".temp",
                    ".cache",
                    ".log",
                    ".thumbs.db",
                    ".ds_store",
                    ".localized",
                    ".spotlight-v100",
                    ".trashes",
                    ".fseventsd",
                    ".temporaryitems",
                    ".apdisk",
                    # PROPRIETARY FORMATS
                    # Adobe
                    ".psd",
                    ".ai",
                    ".indd",
                    ".prproj",
                    ".aep",
                    ".fla",
                    ".swf",
                    # Microsoft specific
                    ".lnk",
                    ".url",
                    ".contact",
                    ".group",
                    ".library-ms",
                    ".searchconnector-ms",
                    # Apple specific
                    ".plist",
                    ".nib",
                    ".xib",
                    ".storyboard",
                    ".xcassets",
                    ".car",
                    # OBSOLETE/LEGACY FORMATS
                    ".fla",
                    ".swf",
                    ".as2",
                    ".as3",
                    ".hqx",
                    ".sit",
                    ".sitx",
                    ".sea",
                    ".cpt",
                    ".pict",
                    ".rsrc",
                    # VIRTUAL MACHINE FILES
                    ".vmdk",
                    ".vdi",
                    ".vhd",
                    ".vhdx",
                    ".ova",
                    ".ovf",
                    ".qcow2",
                    ".img",
                    # TORRENT AND P2P
                    ".torrent",
                    ".magnet",
                    ".ed2k",
                    ".metalink",
                    # EMAIL FILES
                    ".msg",
                    ".eml",
                    ".emlx",
                    ".mbox",
                    ".pst",
                    ".ost",
                    ".nsf",
                    ".dbx",
                    # CALENDAR/CONTACT FILES
                    ".ics",
                    ".ical",
                    ".vcf",
                    ".vcard",
                    ".ldif",
                    # GIS/MAPPING FILES
                    ".shp",
                    ".kml",
                    ".kmz",
                    ".gpx",
                    ".geojson",
                    ".mxd",
                    ".qgs",
                    # SCIENTIFIC DATA
                    ".mat",
                    ".hdf5",
                    ".h5",
                    ".fits",
                    ".nc",
                    ".cdf",
                    ".sav",
                    # BLOCKCHAIN/CRYPTO
                    ".wallet",
                    ".dat",
                    ".keys",
                    ".seed",
                    # PACKAGE MANAGERS (Binary packages, not source)
                    ".apk",
                    ".ipa",
                    ".deb",
                    ".rpm",
                    ".msi",
                    ".pkg",
                    ".snap",
                    ".flatpak",
                    # BROWSER FILES
                    ".crx",
                    ".xpi",
                    ".bookmark",
                    ".webloc",
                    # SUBTITLE FILES (not code)
                    ".srt",
                    ".ass",
                    ".ssa",
                    ".vtt",
                    ".sub",
                    ".idx",
                    # LICENSE/LEGAL FILES (when not code-related)
                    ".license",
                    ".copying",
                    ".authors",
                    ".contributors",
                    ".credits",
                }
            )
        )

        # Size limits
        self.MAX_INDIVIDUAL_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
        self.MIN_FILE_SIZE_BYTES = 1  # Skip empty files
        self.MAX_TOTAL_ANALYSIS_SIZE = 50 * 1024 * 1024  # 50MB total

        # Path-based exclusions
        self.EXCLUDED_DIRECTORIES = {
            # Dependencies and packages
            "node_modules",
            "vendor",
            "packages",
            "lib",
            "libs",
            "third_party",
            "external",
            "dependencies",
            "bower_components",
            # Build outputs and generated files
            "build",
            "dist",
            "out",
            "output",
            "release",
            "debug",
            "bin",
            "obj",
            "target",
            "cmake-build-debug",
            "cmake-build-release",
            # IDE and editor files
            ".vscode",
            ".idea",
            ".vs",
            ".eclipse",
            ".settings",
            ".metadata",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".tox",
            # Version control
            ".git",
            ".svn",
            ".hg",
            ".bzr",
            # Cache and temporary
            ".cache",
            ".tmp",
            "tmp",
            "temp",
            ".temp",
            "cache",
            # Documentation builds
            "_site",
            "_build",
            "site",
            "docs/_build",
            ".docusaurus",
            # Test coverage and reports
            "coverage",
            "htmlcov",
            ".nyc_output",
            ".coverage",
            # Mobile development
            "Pods",
            "DerivedData",
            ".expo",
            ".flutter-plugins",
            # Logs
            "logs",
            "log",
            ".logs",
        }

        self.EXCLUDED_FILENAMES = {
            # Lock files
            "package-lock.json",
            "yarn.lock",
            "composer.lock",
            "Pipfile.lock",
            "poetry.lock",
            "Gemfile.lock",
            "cargo.lock",
            "mix.lock",
            # Generated files
            "bundle.js",
            "bundle.min.js",
            "app.min.js",
            "vendor.js",
            "main.bundle.js",
            "polyfills.js",
            "runtime.js",
            # Database files
            "database.sqlite",
            "database.db",
            "data.db",
            "app.db",
            # IDE files
            ".DS_Store",
            "Thumbs.db",
            "desktop.ini",
            ".directory",
            # Compiled Python
            "*.pyc",
            "*.pyo",
            "*.pyd",
            # Environment files with potentially sensitive data
            ".env.local",
            ".env.production",
            ".env.staging",
        }

        # Filename pattern exclusions (regex-based, NO CONTENT READING)
        self.EXCLUDED_FILENAME_PATTERNS = [
            # Minified files (detectable by name)
            r".*\.min\.(js|css|html)$",
            r".*-min\.(js|css)$",
            r".*\.bundle\.(js|css)$",
            r".*\.chunk\.[a-f0-9]+\.(js|css)$",  # Webpack chunks
            # Temporary files
            r".*\.tmp$",
            r".*\.temp$",
            r".*\.bak$",
            r".*\.backup$",
            r".*\.old$",
            r".*\.orig$",
            r".*~$",
            r"^\#.*\#$",
            r"\..*\.sw[po]$",  # Vim swap files
            # Lock and generated patterns
            r".*-lock\..*$",
            r".*\.lockfile$",
            # Version/build artifacts
            r".*\.[a-f0-9]{8,}\.js$",  # Hash-based filenames
            r".*\.[a-f0-9]{8,}\.css$",
            r".*\.generated\..*$",
            r".*\.auto\..*$",
            # Compiled files
            r".*\.pyc$",
            r".*\.pyo$",
            r".*\.pyd$",
            r".*\.class$",
            r".*\.o$",
            r".*\.obj$",
            # Log files
            r".*\.log$",
            r".*\.log\.\d+$",
            # Test artifacts
            r".*\.test\.js\.snap$",  # Jest snapshots
            r".*__snapshots__.*$",
            # Coverage files
            r".*\.lcov$",
            r".*\.coverage$",
            # Map files
            r".*\.map$",
            r".*\.js\.map$",
            r".*\.css\.map$",
        ]

        # Content-based filters
        self.GENERATED_FILE_INDICATORS = [
            "auto-generated",
            "automatically generated",
            "do not edit",
            "generated by",
            "this file was generated",
            "// <auto-generated",
            "/* auto-generated */",
            "# Auto-generated",
            "# Generated by",
            "Code generated by",
            "WARNING: do not modify",
        ]

        self.MINIFIED_FILE_INDICATORS = [
            # Single line with high character density
            r"^.{500,}$",  # Single line over 500 chars
            # Minified JS/CSS patterns
            r"[a-zA-Z]\w*\(\w*\)\s*{[^}]+}[a-zA-Z]\w*\(\w*\)\s*{",  # Compressed functions
        ]

        # Binary file detection
        self.BINARY_EXTENSIONS = {
            ".so",
            ".dll",
            ".dylib",
            ".a",
            ".lib",
            ".exe",
            ".bin",
            ".dat",
            ".class",
            ".jar",
            ".war",
            ".ear",
            ".dex",
            ".apk",
            ".ipa",
        }

        # Suspicious size patterns (files that are likely generated)
        self.SUSPICIOUS_SIZE_RANGES: List[tuple[int, float]] = [
            # Very large single files (likely bundled/generated)
            (1024 * 1024, float("inf")),  # > 1MB single files
        ]

    def should_skip_file(self, file_path: str, file_size: int, name: str = "") -> tuple[bool, str]:
        """
        Comprehensive file filtering WITHOUT reading file content.

        Returns:
            tuple[bool, str]: (should_skip, reason)
        """
        path_obj = Path(file_path)
        ext = path_obj.suffix.lower()
        filename = path_obj.name
        filename_lower = filename.lower()

        # 1. Extension-based exclusion (your existing check)
        if ext in self.EXCLUSION_EXTS:
            return True, f"Excluded extension: {ext}"

        # 2. File size checks (your existing checks)
        if file_size > self.MAX_INDIVIDUAL_FILE_SIZE_BYTES:
            return (
                True,
                f"File too large: {file_size:,} bytes > {self.MAX_INDIVIDUAL_FILE_SIZE_BYTES:,}",
            )

        if file_size <= self.MIN_FILE_SIZE_BYTES:
            return True, "Empty or near-empty file"

        # 3. Directory-based exclusions
        path_parts = [p.lower() for p in path_obj.parts]
        for excluded_dir in self.EXCLUDED_DIRECTORIES:
            if excluded_dir in path_parts:
                return True, f"In excluded directory: {excluded_dir}"

        # 4. Exact filename exclusions
        if filename_lower in {f.lower() for f in self.EXCLUDED_FILENAMES}:
            return True, f"Excluded filename: {filename}"

        # 5. Filename pattern exclusions
        for pattern in self.EXCLUDED_FILENAME_PATTERNS:
            if re.match(pattern, filename_lower, re.IGNORECASE):
                return True, f"Matches excluded pattern: {pattern}"

        # 6. Binary file extensions
        if ext in self.BINARY_EXTENSIONS:
            return True, f"Binary file extension: {ext}"

        # 7. Hidden files (often system/config files)
        if filename.startswith(".") and ext not in {".js", ".ts", ".py", ".java", ".cpp"}:
            return True, "Hidden file (likely system/config)"

        # 8. Very long filenames (often generated)
        if len(filename) > 100:
            return True, f"Filename too long: {len(filename)} characters"

        # 9. Files with suspicious character patterns in name
        if self._has_suspicious_filename_pattern(filename):
            return True, "Suspicious filename pattern (likely generated)"

        # 10. MIME type check (no content reading, just extension-based)
        mime_type = mimetypes.guess_type(file_path)[0]
        if mime_type and not self._is_likely_text_mime_type(mime_type):
            return True, f"Non-text MIME type: {mime_type}"

        # 11. Files with numeric-heavy names (often generated)
        if self._is_numeric_heavy_filename(filename):
            return True, "Numeric-heavy filename (likely generated)"

        # 12. Test files (optional - you might want to analyze these)
        if self._is_test_file_by_path(file_path):
            return True, "Test file (excluded from main analysis)"

        # 13. Documentation in non-code format
        if self._is_non_code_documentation(filename_lower, ext):
            return True, "Non-code documentation file"

        return False, "File passed all filters"

    def _has_suspicious_filename_pattern(self, filename: str) -> bool:
        """Detect generated files by filename patterns."""
        suspicious_patterns = [
            # Hash-like patterns
            r"[a-f0-9]{32,}",  # MD5/SHA hashes
            r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",  # UUIDs
            # Build artifacts
            r"chunk\.\w+\.",
            r"vendor\.\w+\.",
            r"runtime\.\w+\.",
            # Multiple consecutive dots
            r"\.{3,}",
        ]

        return any(re.search(pattern, filename, re.IGNORECASE) for pattern in suspicious_patterns)

    def _is_numeric_heavy_filename(self, filename: str) -> bool:
        """Check if filename is heavily numeric (likely generated)."""
        name_without_ext = Path(filename).stem
        if len(name_without_ext) == 0:
            return False

        numeric_chars = sum(1 for c in name_without_ext if c.isdigit())
        return numeric_chars / len(name_without_ext) > 0.6  # >60% numeric

    def _is_test_file_by_path(self, file_path: str) -> bool:
        """Detect test files by path patterns."""
        path_lower = file_path.lower()
        filename = Path(file_path).name.lower()

        # Directory-based detection
        test_dirs = {"test", "tests", "__tests__", "spec", "specs", "testing"}
        path_parts = set(Path(file_path).parts)
        if any(test_dir in {p.lower() for p in path_parts} for test_dir in test_dirs):
            return True

        # Filename-based detection
        test_patterns = [
            r".*test.*\.(py|js|ts|java|cpp|c|cs|rb|go|rs)$",
            r".*_test\.(py|js|ts|java|cpp|c|cs|rb|go|rs)$",
            r"test_.*\.(py|js|ts|java|cpp|c|cs|rb|go|rs)$",
            r".*\.test\.(js|ts)$",
            r".*\.spec\.(js|ts|py|rb)$",
        ]

        return any(re.match(pattern, filename) for pattern in test_patterns)

    def _is_non_code_documentation(self, filename_lower: str, ext: str) -> bool:
        """Check if file is documentation that doesn't contain code."""
        # Documentation files that typically don't contain analyzable code
        doc_files = {
            "readme",
            "readme.txt",
            "readme.md",
            "readme.rst",
            "license",
            "license.txt",
            "license.md",
            "changelog",
            "changelog.md",
            "changelog.txt",
            "authors",
            "contributors",
            "credits",
            "thanks",
            "install",
            "install.txt",
            "install.md",
            "news",
            "history",
            "copying",
            "notice",
        }

        base_name = Path(filename_lower).stem
        return base_name in doc_files or filename_lower in doc_files

    def _is_likely_text_mime_type(self, mime_type: str) -> bool:
        """Check if MIME type indicates text content (no file reading)."""
        text_mime_prefixes = [
            "text/",
            "application/json",
            "application/xml",
            "application/javascript",
            "application/x-httpd-php",
            "application/x-python",
            "application/x-sh",
        ]
        return any(mime_type.startswith(prefix) for prefix in text_mime_prefixes)

    def filter_files_with_budget(self, files: List[Dict]) -> List[Dict]:
        """
        Filter files with total size budget management (no content reading).
        """
        filtered_files = []
        current_total_size = 0

        # Sort by priority (code files first, then by size)
        prioritized_files = sorted(files, key=self._get_file_priority)

        for file in prioritized_files:
            file_path = file.get("path", str(file))
            file_size = file.get("size", 0)

            should_skip, reason = self.should_skip_file(file_path, file_size)

            if should_skip:
                logger.debug(f"Skipping {file_path}: {reason}")
                continue

            if current_total_size + file_size > self.MAX_TOTAL_ANALYSIS_SIZE:
                logger.warning(
                    f"Reached size budget ({self.MAX_TOTAL_ANALYSIS_SIZE:,} bytes), "
                    f"skipping remaining files including {file_path}"
                )
                break

            filtered_files.append(file)
            current_total_size += file_size

        logger.info(
            f"Filtered {len(files)} files to {len(filtered_files)} files "
            f"({current_total_size:,} bytes total)"
        )

        return filtered_files

    def _get_file_priority(self, file: Dict) -> tuple:
        """Get priority score for file (lower = higher priority)."""
        file_path = file.get("path", str(file)).lower()
        ext = Path(file_path).suffix.lower()
        size = file.get("size", 0)

        # Priority 1: Main programming language files
        if ext in {
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
            ".c",
            ".cs",
            ".rb",
            ".go",
            ".rs",
            ".swift",
            ".kt",
        }:
            return (1, size)

        # Priority 2: Web development files
        if ext in {".html", ".css", ".scss", ".sass", ".vue", ".jsx", ".tsx", ".php"}:
            return (2, size)

        # Priority 3: Build/config files that contain logic
        if ext in {".json", ".yaml", ".yml", ".toml", ".dockerfile"} and "package" not in file_path:
            return (3, size)

        # Priority 4: Database/query files
        if ext in {".sql", ".graphql", ".gql"}:
            return (4, size)

        # Priority 5: Documentation with potential code
        if ext in {".md", ".rst"} and any(word in file_path for word in ["api", "readme", "doc"]):
            return (5, size)

        # Priority 6: Everything else
        return (6, size)


class GitHubProfileImporter:
    """TODO this class will be refactored to an agent."""

    def __init__(self, github_username: str) -> None:
        self.github_username = github_username
        self.client = GoogleClient(model=settings.FAST_GOOGLE_MODEL)
        self.filter_obj = CodeFileFilter()
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

    def _fetch_repo_tree(self, repo_name: str, default_branch: str) -> List[Dict]:
        """Helper to fetch all file blobs from a repo's tree."""
        try:
            # First, get the SHA of the default branch's tree
            branch_url = f"https://api.github.com/repos/{self.github_username}/{repo_name}/branches/{default_branch}"
            branch_resp = requests.get(branch_url, headers=self.headers, timeout=15)
            branch_resp.raise_for_status()
            tree_sha = branch_resp.json()["commit"]["commit"]["tree"]["sha"]

            # Then, get the recursive tree
            tree_url = f"https://api.github.com/repos/{self.github_username}/{repo_name}/git/trees/{tree_sha}?recursive=1"
            tree_resp = requests.get(tree_url, headers=self.headers, timeout=30)
            tree_resp.raise_for_status()

            all_tree_items = tree_resp.json().get("tree", [])
            # Filter")
            # Filter for blobs (files) and ensure 'path' and 'size' are present
            file_items = [
                item
                for item in all_tree_items
                if item.get("type") == "blob" and "path" in item and "size" in item
            ]
            return file_items
        except requests.exceptions.RequestException as e:
            logger.error(f"API error fetching tree for {repo_name} on branch {default_branch}: {e}")
        except KeyError as e:
            logger.error(f"Unexpected API response structure for {repo_name} tree (KeyError: {e}).")
        except Exception as e:
            logger.error(f"Generic error fetching tree for {repo_name}: {e}")
        return []

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

    def analyze_coding_experience(self, uploaded_files: list[File]) -> Dict:
        """
        Comprehensive analysis of user's coding experience and abilities for job applications.
        Extracts technical skills, programming patterns, complexity indicators, and professional readiness.
        """
        try:
            prompt: str = """
            Analyze the provided code files to assess the user's experience, skills, and abilities for job application purposes.
            
            Provide a comprehensive analysis covering:
            
            1. TECHNICAL PROFICIENCY:
            - Programming languages used and proficiency level (beginner/intermediate/advanced)
            - Frameworks, libraries, and tools demonstrated
            - Database technologies and data handling approaches
            - API usage and integration patterns
            
            2. CODE QUALITY & BEST PRACTICES:
            - Code organization and structure quality
            - Use of design patterns and architectural principles
            - Error handling and edge case management
            - Code documentation and commenting practices
            - Testing approaches (unit tests, integration tests, etc.)
            
            3. PROBLEM-SOLVING & ALGORITHMS:
            - Algorithm complexity and efficiency considerations
            - Data structure usage and optimization
            - Problem decomposition and solution approach
            - Mathematical or computational thinking demonstrated
            
            4. SOFTWARE ENGINEERING PRACTICES:
            - Object-oriented programming concepts usage
            - Functional programming patterns
            - Code reusability and modularity
            - Version control practices (if evident)
            - Configuration management
            
            5. DOMAIN EXPERTISE:
            - Specific industry/domain knowledge shown
            - Business logic implementation
            - Integration with external systems
            - Data processing and analysis capabilities
            
            6. EXPERIENCE INDICATORS:
            - Project complexity level (simple scripts vs. full applications)
            - Code maturity and sophistication
            - Performance optimization techniques
            - Security considerations implemented
            
            7. COLLABORATION & PROFESSIONALISM:
            - Code readability for team environments
            - Documentation quality for knowledge sharing
            - Consistent coding style and conventions
            - Professional development practices
            
            Return detailed analysis as JSON with specific examples and recommendations for job applications.
            """

            output_schema: Dict[str, Dict[str, str]] = {
                "technical_skills": {
                    "languages": "dict with language names as keys and proficiency levels as values",
                    "frameworks_libraries": "list of frameworks/libraries with usage context",
                    "databases": "list of database technologies and usage patterns",
                    "tools_technologies": "list of development tools and platforms used",
                },
                "code_quality": {
                    "overall_rating": "string: excellent/good/fair/needs_improvement",
                    "strengths": "list of code quality strengths demonstrated",
                    "areas_for_improvement": "list of areas that could be enhanced",
                    "best_practices_used": "list of software engineering best practices observed",
                },
                "problem_solving": {
                    "algorithm_complexity": "assessment of algorithmic thinking and efficiency",
                    "data_structures": "list of data structures used appropriately",
                    "problem_approach": "description of problem-solving methodology",
                    "optimization_techniques": "list of performance optimizations demonstrated",
                },
                "experience_level": {
                    "overall_assessment": "string: junior/mid-level/senior/expert",
                    "project_complexity": "description of project sophistication level",
                    "years_equivalent": "estimated equivalent years of professional experience",
                    "readiness_indicators": "list of indicators showing job readiness",
                },
                "domain_expertise": {
                    "specialized_areas": "list of domain-specific knowledge areas",
                    "business_logic": "assessment of business problem solving capability",
                    "integration_skills": "evaluation of system integration abilities",
                    "data_handling": "assessment of data processing and analysis skills",
                },
                "professional_skills": {
                    "collaboration_readiness": "assessment of team-work code quality",
                    "documentation_quality": "evaluation of code documentation practices",
                    "maintainability": "assessment of code maintainability and scalability",
                    "testing_approach": "evaluation of testing methodology and coverage",
                },
                "job_application_summary": {
                    "key_strengths": "list of top 5 strengths to highlight in applications",
                    "suitable_roles": "list of job roles/positions this experience suits",
                    "competitive_advantages": "unique aspects that stand out to employers",
                    "development_recommendations": "areas to focus on for career growth",
                },
                "portfolio_recommendations": {
                    "highlight_projects": "specific code examples to showcase in portfolio",
                    "skill_demonstrations": "how to present technical abilities effectively",
                    "improvement_suggestions": "concrete steps to enhance job application materials",
                },
            }

            llm_input_contents: List[File | str] = [prompt] + uploaded_files

            try:
                llm_analysis = self.client.generate_structured_output(
                    prompt=llm_input_contents, output_schema=output_schema
                )

                # Ensure comprehensive analysis structure with defaults
                analysis_result = {
                    "technical_skills": llm_analysis.get(
                        "technical_skills",
                        {
                            "languages": {},
                            "frameworks_libraries": [],
                            "databases": [],
                            "tools_technologies": [],
                        },
                    ),
                    "code_quality": llm_analysis.get(
                        "code_quality",
                        {
                            "overall_rating": "needs_assessment",
                            "strengths": [],
                            "areas_for_improvement": [],
                            "best_practices_used": [],
                        },
                    ),
                    "problem_solving": llm_analysis.get(
                        "problem_solving",
                        {
                            "algorithm_complexity": "basic level demonstrated",
                            "data_structures": [],
                            "problem_approach": "standard approach",
                            "optimization_techniques": [],
                        },
                    ),
                    "experience_level": llm_analysis.get(
                        "experience_level",
                        {
                            "overall_assessment": "junior",
                            "project_complexity": "basic projects",
                            "years_equivalent": "0-1 years",
                            "readiness_indicators": [],
                        },
                    ),
                    "domain_expertise": llm_analysis.get(
                        "domain_expertise",
                        {
                            "specialized_areas": [],
                            "business_logic": "basic understanding",
                            "integration_skills": "limited experience",
                            "data_handling": "basic data processing",
                        },
                    ),
                    "professional_skills": llm_analysis.get(
                        "professional_skills",
                        {
                            "collaboration_readiness": "needs development",
                            "documentation_quality": "minimal documentation",
                            "maintainability": "basic structure",
                            "testing_approach": "limited testing",
                        },
                    ),
                    "job_application_summary": llm_analysis.get(
                        "job_application_summary",
                        {
                            "key_strengths": [],
                            "suitable_roles": ["Entry-level Developer"],
                            "competitive_advantages": [],
                            "development_recommendations": [],
                        },
                    ),
                    "portfolio_recommendations": llm_analysis.get(
                        "portfolio_recommendations",
                        {
                            "highlight_projects": [],
                            "skill_demonstrations": [],
                            "improvement_suggestions": [],
                        },
                    ),
                    "analyzed_by": "comprehensive_llm_analysis",
                    "analysis_timestamp": self._get_current_timestamp(),
                    "files_analyzed": len(uploaded_files),
                }

                return analysis_result

            except Exception as llm_error:
                logger.error(f"Comprehensive coding analysis failed: {llm_error}")
                return {
                    "error": f"Analysis failed: {str(llm_error)}",
                    "technical_skills": {
                        "languages": {},
                        "frameworks_libraries": [],
                        "databases": [],
                        "tools_technologies": [],
                    },
                    "code_quality": {
                        "overall_rating": "unable_to_assess",
                        "strengths": [],
                        "areas_for_improvement": [],
                        "best_practices_used": [],
                    },
                    "problem_solving": {
                        "algorithm_complexity": "unable_to_assess",
                        "data_structures": [],
                        "problem_approach": "unable_to_assess",
                        "optimization_techniques": [],
                    },
                    "experience_level": {
                        "overall_assessment": "unable_to_assess",
                        "project_complexity": "unable_to_assess",
                        "years_equivalent": "unknown",
                        "readiness_indicators": [],
                    },
                    "domain_expertise": {
                        "specialized_areas": [],
                        "business_logic": "unable_to_assess",
                        "integration_skills": "unable_to_assess",
                        "data_handling": "unable_to_assess",
                    },
                    "professional_skills": {
                        "collaboration_readiness": "unable_to_assess",
                        "documentation_quality": "unable_to_assess",
                        "maintainability": "unable_to_assess",
                        "testing_approach": "unable_to_assess",
                    },
                    "job_application_summary": {
                        "key_strengths": [],
                        "suitable_roles": [],
                        "competitive_advantages": [],
                        "development_recommendations": [],
                    },
                    "portfolio_recommendations": {
                        "highlight_projects": [],
                        "skill_demonstrations": [],
                        "improvement_suggestions": [],
                    },
                }

        except Exception as e:
            logger.error(f"Unexpected error in coding experience analysis: {e}")
            return {
                "error": f"Failed to analyze coding experience: {str(e)}",
                "analysis_status": "failed",
            }

    def _get_current_timestamp(self):
        """Helper method to get current timestamp for analysis tracking."""

        return datetime.now().isoformat()

    def generate_job_application_report(self, analysis_result: Dict) -> str:
        """
        Generate a formatted report suitable for job applications based on coding analysis.
        """
        if "error" in analysis_result:
            return f"Analysis Error: {analysis_result['error']}"

        report: str = f"""
                # CODING EXPERIENCE ANALYSIS REPORT

                ## Overall Assessment
                **Experience Level:** {analysis_result['experience_level']['overall_assessment'].title()}
                **Equivalent Experience:** {analysis_result['experience_level']['years_equivalent']}
                **Code Quality Rating:** {analysis_result['code_quality']['overall_rating'].title()}

                ## Key Technical Strengths
                """

        # Add key strengths
        for strength in analysis_result["job_application_summary"]["key_strengths"]:
            report += f"• {strength}\n"

        report += """
                    ## Technical Skills Profile
                    **Programming Languages:**
                    """
        for lang, level in analysis_result["technical_skills"]["languages"].items():
            report += f"• {lang}: {level}\n"

        report += """
                    **Frameworks & Libraries:**
                    """
        for framework in analysis_result["technical_skills"]["frameworks_libraries"]:
            report += f"• {framework}\n"

        report += """
                    ## Suitable Job Roles
                    """
        for role in analysis_result["job_application_summary"]["suitable_roles"]:
            report += f"• {role}\n"

        report += """
                ## Competitive Advantages
                """
        for advantage in analysis_result["job_application_summary"]["competitive_advantages"]:
            report += f"• {advantage}\n"

        report += """
                    ## Portfolio Recommendations
                    **Projects to Highlight:**
                    """
        for project in analysis_result["portfolio_recommendations"]["highlight_projects"]:
            report += f"• {project}\n"

        report += """
                ## Development Recommendations
                """
        for recommendation in analysis_result["job_application_summary"][
            "development_recommendations"
        ]:
            report += f"• {recommendation}\n"

        return report

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
                description = repo.get("description", "")
                language = repo.get("language", "")
                stars = repo.get("stargazers_count", 0)
                forks = repo.get("forks_count", 0)
                updated_at = repo.get("updated_at", "")
                default_branch = repo.get("default_branch", "main")

                repo_tree_items = self._fetch_repo_tree(name, default_branch)
                # repo_path = os.path.join(self.temp_dir, name) # Not used if fetching via API

                uploaded_files_for_analysis: list[File] = []
                processed_file_paths: List[str] = []

                for file_item in repo_tree_items:
                    file_path_in_repo = file_item["path"]
                    blob_api_url = file_item["url"]
                    file_size = file_item.get("size", 0)

                    should_skip, reason = self.filter_obj.should_skip_file(
                        file_path_in_repo, file_size, name
                    )

                    if should_skip:
                        logger.debug(f"Skipping {file_path_in_repo}: {reason}")
                        continue

                    try:
                        # Use self.headers for authenticated requests if token is present
                        blob_response = httpx.get(blob_api_url, headers=self.headers, timeout=20)
                        blob_response.raise_for_status()
                        blob_data = blob_response.json()

                        if blob_data.get("encoding") != "base64":
                            logger.warning(
                                f"File {file_path_in_repo} in {name} is not base64 encoded as expected. Encoding: {blob_data.get('encoding')}. Skipping."
                            )
                            continue

                        file_content_base64 = blob_data.get("content")
                        if not file_content_base64:
                            logger.warning(
                                f"No content found for file {file_path_in_repo} in {name}. Skipping."
                            )
                            continue

                        decoded_content_bytes = base64.b64decode(file_content_base64)
                        doc_io = io.BytesIO(decoded_content_bytes)

                        mime_type, _ = mimetypes.guess_type(file_path_in_repo)
                        if mime_type is None:
                            mime_type = "application/octet-stream"  # Default if cannot guess

                        uploaded_file_obj = self.client.client.files.upload(
                            file=doc_io,
                            config={"mime_type": mime_type},
                        )
                        uploaded_files_for_analysis.append(uploaded_file_obj)
                        processed_file_paths.append(file_path_in_repo)

                    except Exception as e:  # pylint: disable=broad-except
                        logger.error(
                            f"Error processing or uploading file {file_path_in_repo} from {name}: {e}"
                        )
                try:
                    analysis = self.analyze_coding_experience(uploaded_files_for_analysis)
                except Exception as e:  # pylint: disable=broad-except
                    logger.error(f"Error reading {name} repo: {e}")

                repo_analyses.append(
                    {
                        "name": name,
                        "description": description,
                        "language": language,
                        "stars": stars,
                        "forks": forks,
                        "last_updated": updated_at,
                        "code_analysis": analysis,
                    }
                )

            return repo_analyses
        except Exception as e:
            logger.error(f"Error fetching repository info: {e}")
            return []

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
            top_repos = simplified_repos

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

    def import_profile(self) -> dict:
        """Import profile data from GitHub"""
        try:
            # Get user profile info
            logger.debug("Fetching GitHub profile data...")
            profile_data = self.get_profile_info()
            if not profile_data:
                return json.dumps({"error": "Failed to fetch GitHub profile data"})

            # Get repository info
            logger.debug("Fetching GitHub repository data...")
            repo_data = self.get_repository_info()
            if not repo_data:
                return json.dumps({"error": "Failed to fetch repository data"})

            # Get contribution data
            logger.debug("Fetching GitHub contribution data...")
            contribution_data = self.get_contribution_data()
            if not contribution_data:
                return json.dumps({"error": "Failed to fetch contribution data"})

            # Extract skills from repositories
            logger.debug("Extracting skills from repositories...")
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

            return combined_data

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
                if repo.get("code_analysis"):
                    technologies = repo["code_analysis"]["technical_skills"]

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

    def _parse_date_flexible(
        self,
        date_str: Optional[str],
        field_name: str,
        section_name: str,
        item_identifier: Optional[str] = None,
    ) -> Optional[str]:
        """
        Parses date strings (YYYY-MM-DD, YYYY-MM, YYYY) into "YYYY-MM-DD" or None.
        Defaults to day 01 / month 01 if not specified.
        """
        if not date_str or not isinstance(date_str, str):
            return None

        original_date_str = date_str
        log_prefix = f"Validation for {section_name}"
        if item_identifier:
            log_prefix += f" (item: {item_identifier})"
        log_prefix += f", field '{field_name}':"

        try:
            # Try YYYY-MM-DD
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            try:
                # Try YYYY-MM
                dt_obj = datetime.strptime(date_str, "%Y-%m")
                parsed_date = dt_obj.strftime("%Y-%m-01")
                logger.info(
                    f"{log_prefix} Date '{original_date_str}' parsed as YYYY-MM, converted to '{parsed_date}'."
                )
                return parsed_date
            except ValueError:
                try:
                    # Try YYYY
                    dt_obj = datetime.strptime(date_str, "%Y")
                    parsed_date = dt_obj.strftime("%Y-01-01")
                    logger.info(
                        f"{log_prefix} Date '{original_date_str}' parsed as YYYY, converted to '{parsed_date}'."
                    )
                    return parsed_date
                except ValueError:
                    logger.warning(
                        f"{log_prefix} Could not parse date string '{original_date_str}'. Expected YYYY-MM-DD, YYYY-MM, or YYYY. Setting to None."
                    )
                    return None

    def _truncate_string(
        self,
        value: Optional[Any],
        max_length: int,
        field_name: str,
        section_name: str,
        item_identifier: Optional[str] = None,
    ) -> Optional[str]:
        """Truncates string if it exceeds max_length. Converts non-strings to strings if possible."""
        if value is None:
            return None

        log_prefix = f"Validation for {section_name}"
        if item_identifier:
            log_prefix += f" (item: {item_identifier})"
        log_prefix += f", field '{field_name}':"

        if not isinstance(value, str):
            original_type = type(value).__name__
            try:
                value = str(value)
                logger.warning(
                    f"{log_prefix} Expected string, got {original_type}. Converted to string: '{value[:50]}...'"
                )
            except Exception:
                logger.error(
                    f"{log_prefix} Could not convert non-string value of type {original_type} to string. Setting to empty string."
                )
                return ""

        if len(value) > max_length:
            truncated_value = value[:max_length]
            logger.warning(
                f"{log_prefix} Value '{value[:30]}...' (len: {len(value)}) exceeded max_length {max_length}. Truncated to '{truncated_value[:30]}...'."
            )
            return truncated_value
        return value

    def _validate_and_clean_parsed_data(self, parsed_data: Dict) -> Dict:
        """Validates and cleans data parsed by LLM against model schemas."""
        cleaned_data = parsed_data.copy()

        # --- Basic Info (UserProfile) ---
        basic_info = cleaned_data.get("basic_info")
        if isinstance(basic_info, dict):
            model_cls = UserProfile
            for field_name, value in basic_info.items():
                try:
                    field_obj = model_cls._meta.get_field(field_name)
                    if isinstance(field_obj, django_models.CharField) and not isinstance(
                        field_obj, django_models.TextField
                    ):
                        basic_info[field_name] = self._truncate_string(
                            value, field_obj.max_length, field_name, "basic_info"
                        )

                    # Check for null values in required fields
                    if not field_obj.null and (value is None or value == ""):
                        logger.warning(
                            f"Field '{field_name}' in 'basic_info' is required but null/empty. Setting to 'Not extracted'."
                        )
                        basic_info[field_name] = "Not extracted"

                except django_models.fields.FieldDoesNotExist:
                    logger.debug(
                        f"Field '{field_name}' in 'basic_info' from LLM not found in UserProfile model. Retaining."
                    )
                except AttributeError:  # e.g. field_obj.max_length might not exist
                    pass
        elif basic_info is not None:
            logger.warning(
                f"'basic_info' from LLM is not a dictionary: {type(basic_info)}. Defaulting to empty dict."
            )
            cleaned_data["basic_info"] = {}

        # --- Helper function for list items ---
        def validate_list_items(
            data_list: Optional[List[Dict]],
            section_name: str,
            model_cls,
            date_fields: List[str],
            bool_fields: List[str],
            float_fields: List[str] = [],
            int_fields: List[str] = [],
        ):
            if not isinstance(data_list, list):
                if (
                    data_list is not None
                ):  # If None, it's fine, will be defaulted by get_schema later if needed
                    logger.warning(
                        f"'{section_name}' from LLM is not a list: {type(data_list)}. Setting to empty list."
                    )
                return []

            validated_list = []
            for i, item in enumerate(data_list):
                if not isinstance(item, dict):
                    logger.warning(
                        f"Item {i} in '{section_name}' is not a dictionary: {type(item)}. Skipping."
                    )
                    continue

                cleaned_item = item.copy()
                item_identifier = cleaned_item.get(
                    "title", cleaned_item.get("name", cleaned_item.get("company", f"item {i}"))
                )

                for field_name, value in cleaned_item.items():
                    try:
                        field_obj = model_cls._meta.get_field(field_name)

                        # Handle string fields
                        if isinstance(field_obj, django_models.CharField) and not isinstance(
                            field_obj, django_models.TextField
                        ):
                            cleaned_item[field_name] = self._truncate_string(
                                value,
                                field_obj.max_length,
                                field_name,
                                section_name,
                                item_identifier,
                            )
                        # Handle date fields
                        elif field_name in date_fields and isinstance(
                            field_obj, django_models.DateField
                        ):
                            cleaned_item[field_name] = self._parse_date_flexible(
                                value, field_name, section_name, item_identifier
                            )
                        # Handle boolean fields
                        elif field_name in bool_fields and isinstance(
                            field_obj, django_models.BooleanField
                        ):
                            if not isinstance(value, bool) and value is not None:
                                logger.debug(
                                    f"Validation for {section_name} (item: {item_identifier}), field '{field_name}': Expected boolean, got {type(value)} ('{value}'). Converting."
                                )
                                cleaned_item[field_name] = str(value).lower() in [
                                    "true",
                                    "1",
                                    "yes",
                                    "present",
                                ]
                        # Handle float fields
                        elif field_name in float_fields and isinstance(
                            field_obj, django_models.FloatField
                        ):
                            if value is not None:
                                try:
                                    cleaned_item[field_name] = float(value)
                                except (ValueError, TypeError):
                                    logger.warning(
                                        f"Validation for {section_name} (item: {item_identifier}), field '{field_name}': Could not convert '{value}' to float. Setting to None."
                                    )
                                    cleaned_item[field_name] = None
                        # Handle integer fields
                        elif field_name in int_fields and isinstance(
                            field_obj, django_models.IntegerField
                        ):
                            if value is not None:
                                try:
                                    cleaned_item[field_name] = int(value)
                                except (ValueError, TypeError):
                                    logger.warning(
                                        f"Validation for {section_name} (item: {item_identifier}), field '{field_name}': Could not convert '{value}' to int. Setting to None."
                                    )
                                    cleaned_item[field_name] = None

                        # Check for null values in required fields (after all type conversions)
                        if not field_obj.null and (
                            cleaned_item.get(field_name) is None
                            or cleaned_item.get(field_name) == ""
                        ):
                            # Use appropriate default based on field type
                            if isinstance(
                                field_obj, (django_models.CharField, django_models.TextField)
                            ):
                                default_value = "Not extracted"
                            elif isinstance(field_obj, django_models.BooleanField):
                                default_value = False
                            elif isinstance(field_obj, django_models.IntegerField):
                                default_value = 0
                            elif isinstance(field_obj, django_models.FloatField):
                                default_value = 0.0
                            elif isinstance(field_obj, django_models.DateField):
                                # Skip date fields - they should remain None if not parsed
                                continue
                            else:
                                default_value = "Not extracted"

                            logger.warning(
                                f"Validation for {section_name} (item: {item_identifier}), field '{field_name}': Required field is null/empty. Setting to '{default_value}'."
                            )
                            cleaned_item[field_name] = default_value

                    except django_models.fields.FieldDoesNotExist:
                        logger.debug(
                            f"Field '{field_name}' in '{section_name}' (item: {item_identifier}) from LLM not found in {model_cls.__name__} model. Retaining."
                        )
                    except AttributeError:  # e.g. field_obj.max_length might not exist
                        pass

                # Check for missing required fields that weren't in the parsed data
                for field in model_cls._meta.get_fields():
                    if (
                        not field.null
                        and hasattr(field, "name")
                        and field.name not in cleaned_item
                        and not field.primary_key  # Skip primary key fields
                        and not getattr(field, "auto_now", False)  # Skip auto fields
                        and not getattr(field, "auto_now_add", False)
                    ):

                        # Use appropriate default based on field type
                        if isinstance(field, (django_models.CharField, django_models.TextField)):
                            default_value = "Not extracted"
                        elif isinstance(field, django_models.BooleanField):
                            default_value = False
                        elif isinstance(field, django_models.IntegerField):
                            default_value = 0
                        elif isinstance(field, django_models.FloatField):
                            default_value = 0.0
                        elif isinstance(field, django_models.DateField):
                            # Skip date fields - they should remain None if not parsed
                            continue
                        else:
                            # Unknown fields it's better to skip them
                            continue

                        logger.warning(
                            f"Validation for {section_name} (item: {item_identifier}): Missing required field '{field.name}'. Setting to '{default_value}'."
                        )
                        cleaned_item[field.name] = default_value

                validated_list.append(cleaned_item)
            return validated_list

        # --- Validate sections ---
        sections_config = {
            "work_experiences": (WorkExperience, ["start_date", "end_date"], [], [], []),
            "education": (Education, ["start_date", "end_date"], [], ["gpa"], []),
            "projects": (Project, ["start_date", "end_date"], [], [], []),
            "certifications": (Certification, ["issue_date", "expiration_date"], [], [], []),
            "skills": (Skill, [], [], [], ["proficiency"]),
            "publications": (Publication, ["publication_date"], [], [], []),
        }

        for section_key, (
            model_cls,
            date_fields,
            bool_fields,
            float_fields,
            int_fields,
        ) in sections_config.items():
            cleaned_data[section_key] = validate_list_items(
                cleaned_data.get(section_key),
                section_key,
                model_cls,
                date_fields,
                bool_fields,
                float_fields,
                int_fields,
            )

        return cleaned_data

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
                        *   If a date is ongoing (e.g., "Present" for an end date), represent the `end_date` as `null`.
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
            raw_parsed_data = self.parse_with_llm(google_uploaded_file)

            # Validate and clean the parsed data
            if isinstance(raw_parsed_data, dict) and not raw_parsed_data.get("error"):
                logger.debug("LLM parsing successful, proceeding to validation and cleaning.")
                validated_data = self._validate_and_clean_parsed_data(raw_parsed_data)
                return validated_data
            else:
                # If parsing failed, or returned an error structure, or not a dict, return as is or a generic error
                logger.warning(
                    f"LLM parsing did not return a clean dictionary for validation. Raw data: {str(raw_parsed_data)[:500]}"
                )
                return (
                    raw_parsed_data
                    if isinstance(raw_parsed_data, dict)
                    else {"error": "LLM parsing failed to return a valid data structure."}
                )

        except Exception as e:
            logger.error(f"Error parsing resume: {str(e)}")
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
