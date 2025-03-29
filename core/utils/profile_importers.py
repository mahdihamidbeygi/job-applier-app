import os
import tempfile
import requests
import ast
from pathlib import Path
from typing import Dict, List
from django.conf import settings
import git
from bs4 import BeautifulSoup
import openai
from datetime import datetime
from .local_llms import OllamaClient

class GitHubProfileImporter:
    def __init__(self, github_username: str):
        self.github_username = github_username
        self.client = OllamaClient()
        self.temp_dir = tempfile.mkdtemp()

    def analyze_python_code(self, code: str) -> Dict:
        """Analyze Python code and extract functions, classes, and imports."""
        try:
            tree = ast.parse(code)
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]
            return {
                "functions": functions,
                "classes": classes,
                "imports": imports,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_repository_info(self) -> List[Dict]:
        """Fetch and analyze all public repositories."""
        repos_url = f"https://api.github.com/users/{self.github_username}/repos"
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        try:
            response = requests.get(repos_url, headers=headers)
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
                try:
                    git.Repo.clone_from(clone_url, repo_path)
                except Exception as e:
                    print(f"Error cloning {name}: {e}")
                    continue

                repo_summary = []
                for filepath in Path(repo_path).rglob("*.py"):
                    try:
                        with open(filepath, "r", encoding="utf-8") as file:
                            code = file.read()
                        analysis = self.analyze_python_code(code)
                        repo_summary.append((str(filepath.relative_to(repo_path)), analysis))
                    except Exception as e:
                        print(f"Error reading {filepath}: {e}")

                # Analyze repository structure
                structure = self.analyze_repository_structure(repo_path)
                
                # Analyze dependencies
                dependencies = self.analyze_dependencies(repo_path)
                
                # Analyze commit history
                commit_history = self.analyze_commit_history(repo_path)

                repo_analyses.append({
                    "name": name,
                    "description": description,
                    "language": language,
                    "stars": stars,
                    "forks": forks,
                    "last_updated": updated_at,
                    "code_analysis": repo_summary,
                    "structure": structure,
                    "dependencies": dependencies,
                    "commit_history": commit_history
                })

            return repo_analyses
        except Exception as e:
            raise Exception(f"Error fetching repository information: {str(e)}")

    def analyze_repository_structure(self, repo_path: str) -> Dict:
        """Analyze repository structure and organization."""
        try:
            structure = {
                "total_files": 0,
                "file_types": {},
                "directories": [],
                "main_files": []
            }
            
            for root, dirs, files in os.walk(repo_path):
                rel_path = os.path.relpath(root, repo_path)
                if rel_path != '.':
                    structure["directories"].append(rel_path)
                
                for file in files:
                    structure["total_files"] += 1
                    ext = os.path.splitext(file)[1]
                    structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1
                    
                    if file.lower() in ['readme.md', 'requirements.txt', 'setup.py', 'main.py']:
                        structure["main_files"].append(os.path.join(rel_path, file))
            
            return structure
        except Exception as e:
            print(f"Error analyzing repository structure: {e}")
            return {}

    def analyze_dependencies(self, repo_path: str) -> Dict:
        """Analyze project dependencies."""
        dependencies = {
            "requirements": [],
            "setup_py": [],
            "imports": set()
        }
        
        try:
            # Check requirements.txt
            req_path = os.path.join(repo_path, "requirements.txt")
            if os.path.exists(req_path):
                with open(req_path, "r") as f:
                    dependencies["requirements"] = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            
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
                        dependencies["setup_py"] = [dep.strip().strip("'\"") for dep in deps if dep.strip()]
            
            # Collect all imports from Python files
            for filepath in Path(repo_path).rglob("*.py"):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.Import, ast.ImportFrom)):
                                if isinstance(node, ast.Import):
                                    for name in node.names:
                                        dependencies["imports"].add(name.name.split('.')[0])
                                else:
                                    dependencies["imports"].add(node.module.split('.')[0])
                except Exception as e:
                    print(f"Error analyzing imports in {filepath}: {e}")
            
            dependencies["imports"] = list(dependencies["imports"])
            return dependencies
        except Exception as e:
            print(f"Error analyzing dependencies: {e}")
            return {}

    def analyze_commit_history(self, repo_path: str) -> Dict:
        """Analyze repository commit history."""
        try:
            repo = git.Repo(repo_path)
            commits = list(repo.iter_commits())
            
            history = {
                "total_commits": len(commits),
                "first_commit": commits[-1].committed_datetime if commits else None,
                "last_commit": commits[0].committed_datetime if commits else None,
                "commit_frequency": {},
                "contributors": set()
            }
            
            # Analyze commit frequency by month
            for commit in commits:
                date = commit.committed_datetime
                month_key = f"{date.year}-{date.month:02d}"
                history["commit_frequency"][month_key] = history["commit_frequency"].get(month_key, 0) + 1
                history["contributors"].add(commit.author.name)
            
            history["contributors"] = list(history["contributors"])
            return history
        except Exception as e:
            print(f"Error analyzing commit history: {e}")
            return {}

    def extract_work_experience(self, repo_analyses: List[Dict]) -> List[Dict]:
        """Use Ollama to extract work experience from repository analyses."""
        prompt = f"""Based on the following GitHub repository analyses, identify potential work experiences and skills:

Repository Analyses:
{repo_analyses}

Please extract:
1. Work experiences (company names, roles, technologies used)
2. Skills (programming languages, frameworks, tools)
3. Project descriptions and achievements
4. Technical expertise and specialization areas
5. Development practices and methodologies

Format the response as a JSON object with the following structure:
{{
    "work_experiences": [
        {{
            "company": "string",
            "position": "string",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM",
            "description": "string",
            "technologies": ["string"],
            "achievements": ["string"]
        }}
    ],
    "skills": [
        {{
            "name": "string",
            "category": "string",
            "proficiency": "string",
            "years_of_experience": "string"
        }}
    ],
    "projects": [
        {{
            "title": "string",
            "description": "string",
            "technologies": ["string"],
            "achievements": ["string"],
            "github_url": "string"
        }}
    ],
    "technical_expertise": [
        {{
            "area": "string",
            "description": "string",
            "technologies": ["string"]
        }}
    ],
    "development_practices": [
        {{
            "practice": "string",
            "description": "string",
            "tools": ["string"]
        }}
    ]
}}
"""

        try:
            response = self.client.generate(prompt)
            return response
        except Exception as e:
            raise Exception(f"Failed to extract work experience: {str(e)}")

    def cleanup(self):
        """Clean up temporary files."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")

    def import_profile(self) -> Dict:
        """Main method to import profile from GitHub."""
        try:
            repo_analyses = self.get_repository_info()
            profile_data = self.extract_work_experience(repo_analyses)
            return profile_data
        finally:
            self.cleanup()

class ResumeImporter:
    """Class for handling resume uploads and parsing."""
    def __init__(self, resume_file):
        self.resume_file = resume_file
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def parse_date(self, date_str):
        """Parse date string into a datetime.date object."""
        if not date_str:
            return None
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%B %Y', '%b %Y', '%m/%Y', '%m/%d/%Y', '%Y']:
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def extract_text(self) -> str:
        """Extract text from the resume file."""
        try:
            if self.resume_file.name.endswith('.pdf'):
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(self.resume_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
            elif self.resume_file.name.endswith(('.doc', '.docx')):
                import docx
                doc = docx.Document(self.resume_file)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            else:
                raise ValueError("Unsupported file format. Please upload PDF or Word document.")
        except Exception as e:
            raise Exception(f"Error extracting text from resume: {str(e)}")

    def parse_with_chatgpt(self, text: str) -> Dict:
        """Parse resume text using ChatGPT to extract structured information."""
        try:
            # First, get basic information
            basic_prompt = f"""Please help me fill out these fields from the resume. Only provide the answers in exactly this format:

Name: [full name]
Email: [email address]
Phone: [phone number]
Location: [city, state/country]
LinkedIn URL: [full LinkedIn URL]
GitHub URL: [full GitHub URL]
Professional Summary: [brief summary]

Resume text:
{text}"""

            basic_response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts information from resumes. Only provide the requested information in the exact format specified."},
                    {"role": "user", "content": basic_prompt}
                ],
                temperature=0.1
            )

            # Get work experience
            work_prompt = f"""List all work experiences from this resume. For each position, provide in this exact format:

Company: [company name]
Position: [position title]
Start Date: [date in YYYY-MM-DD format]
End Date: [date in YYYY-MM-DD format or 'Present' if current]
Description: [key responsibilities]
Technologies: [comma-separated list of technologies used]

Resume text:
{text}"""

            work_response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts work experience from resumes. List each position separately and use the exact format specified."},
                    {"role": "user", "content": work_prompt}
                ],
                temperature=0.1
            )

            # Get education
            education_prompt = f"""List all education entries from this resume. For each entry, provide in this exact format:

Institution: [school name]
Degree: [degree name]
Field of Study: [field name]
Start Date: [date in YYYY-MM-DD format]
End Date: [date in YYYY-MM-DD format or 'Present' if current]
GPA: [numeric value between 0-4.0, or leave empty if not mentioned]
Achievements: [comma-separated list of achievements]

Resume text:
{text}"""

            education_response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts education information from resumes. List each education entry separately and use the exact format specified."},
                    {"role": "user", "content": education_prompt}
                ],
                temperature=0.1
            )

            # Get projects
            projects_prompt = f"""List all projects from this resume. For each project, provide in this exact format:

Title: [project name]
Description: [brief description]
Start Date: [date in YYYY-MM-DD format]
End Date: [date in YYYY-MM-DD format or 'Present' if current]
Technologies: [comma-separated list of technologies]
GitHub URL: [GitHub URL if available]
Live URL: [Live URL if available]

Resume text:
{text}"""

            projects_response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts project information from resumes. List each project separately and use the exact format specified."},
                    {"role": "user", "content": projects_prompt}
                ],
                temperature=0.1
            )

            # Get certifications
            certifications_prompt = f"""List all certifications from this resume. For each certification, provide in this exact format:

Name: [certification name]
Issuer: [issuing organization]
Issue Date: [date in YYYY-MM-DD format]
Expiry Date: [date in YYYY-MM-DD format or leave empty if no expiry]
Credential ID: [credential ID if available]
URL: [verification URL if available]

Resume text:
{text}"""

            certifications_response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts certification information from resumes. List each certification separately and use the exact format specified."},
                    {"role": "user", "content": certifications_prompt}
                ],
                temperature=0.1
            )

            # Get publications
            publications_prompt = f"""List all publications from this resume. For each publication, provide in this exact format:

Title: [publication title]
Authors: [comma-separated list of authors]
Publication Date: [date in YYYY-MM-DD format]
Publisher: [publisher name]
Journal: [journal name if applicable]
DOI: [DOI if available]
URL: [URL if available]
Abstract: [brief abstract if available]

Resume text:
{text}"""

            publications_response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts publication information from resumes. List each publication separately and use the exact format specified."},
                    {"role": "user", "content": publications_prompt}
                ],
                temperature=0.1
            )

            # Get skills with categories
            skills_prompt = f"""List all skills from this resume, categorized by type. Use this exact format for each skill:

Name: [skill name]
Category: [one of: programming, frameworks, databases, tools, soft_skills, languages, other]
Proficiency: [number between 1-5]

Resume text:
{text}"""

            skills_response = self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts and categorizes skills from resumes. For each skill, provide the name, category, and a proficiency level from 1-5. Use the exact format specified."},
                    {"role": "user", "content": skills_prompt}
                ],
                temperature=0.1
            )

            # Process responses into a structured format
            def parse_key_value_response(response_text):
                result = {}
                current_key = None
                for line in response_text.strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower().replace(' ', '_')
                        value = value.strip()
                        
                        # Handle dates specifically
                        if key in ['start_date', 'end_date', 'issue_date', 'expiry_date', 'publication_date']:
                            if value.lower() == 'present':
                                if key == 'end_date':
                                    result['current'] = True
                                    value = None
                            else:
                                parsed_date = self.parse_date(value)
                                if parsed_date:
                                    value = parsed_date.isoformat()
                                else:
                                    value = None
                        
                        # Handle proficiency
                        if key == 'proficiency':
                            try:
                                value = int(value)
                                if value < 1:
                                    value = 1
                                elif value > 5:
                                    value = 5
                            except (ValueError, TypeError):
                                value = 3  # Default proficiency
                        
                        result[key] = value
                return result

            # Structure all the data
            basic_info = parse_key_value_response(basic_response.choices[0].message.content)
            
            # Parse work experiences
            work_text = work_response.choices[0].message.content
            work_entries = [entry.strip() for entry in work_text.split('\n\n') if entry.strip()]
            work_experiences = [parse_key_value_response(entry) for entry in work_entries]
            
            # Parse education entries
            education_text = education_response.choices[0].message.content
            education_entries = [entry.strip() for entry in education_text.split('\n\n') if entry.strip()]
            education = [parse_key_value_response(entry) for entry in education_entries]
            
            # Parse projects
            projects_text = projects_response.choices[0].message.content
            project_entries = [entry.strip() for entry in projects_text.split('\n\n') if entry.strip()]
            projects = [parse_key_value_response(entry) for entry in project_entries]
            
            # Parse certifications
            certifications_text = certifications_response.choices[0].message.content
            certification_entries = [entry.strip() for entry in certifications_text.split('\n\n') if entry.strip()]
            certifications = [parse_key_value_response(entry) for entry in certification_entries]
            
            # Parse publications
            publications_text = publications_response.choices[0].message.content
            publication_entries = [entry.strip() for entry in publications_text.split('\n\n') if entry.strip()]
            publications = [parse_key_value_response(entry) for entry in publication_entries]
            
            # Parse skills
            skills_text = skills_response.choices[0].message.content
            skill_entries = [entry.strip() for entry in skills_text.split('\n\n') if entry.strip()]
            skills = [parse_key_value_response(entry) for entry in skill_entries]

            # Combine everything into the final structure
            parsed_data = {
                "personal_info": {
                    "name": basic_info.get('name', ''),
                    "email": basic_info.get('email', ''),
                    "phone": basic_info.get('phone', ''),
                    "location": basic_info.get('location', ''),
                    "linkedin": basic_info.get('linkedin_url', ''),
                    "github": basic_info.get('github_url', ''),
                    "professional_summary": basic_info.get('professional_summary', '')
                },
                "work_experiences": work_experiences,
                "education": education,
                "projects": projects,
                "certifications": certifications,
                "publications": publications,
                "skills": skills
            }

            return parsed_data

        except Exception as e:
            raise Exception(f"Error parsing resume with ChatGPT: {str(e)}")

    def parse_resume(self) -> Dict:
        """Parse the resume and return structured data."""
        try:
            # Extract text from the resume
            text = self.extract_text()
            
            # Parse the text using ChatGPT
            parsed_data = self.parse_with_chatgpt(text)
            
            # Add the raw text to the parsed data
            parsed_data['raw_text'] = text
            
            return parsed_data
            
        except Exception as e:
            raise Exception(f"Error parsing resume: {str(e)}")

class LinkedInImporter:
    """Class for handling LinkedIn profile imports."""
    def __init__(self, linkedin_url: str):
        self.linkedin_url = linkedin_url
        self.client = OllamaClient()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def scrape_profile(self) -> Dict:
        """Scrape LinkedIn profile data."""
        try:
            import time
            import random
            
            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(2, 5))
            
            response = requests.get(self.linkedin_url, headers=self.headers)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch LinkedIn profile: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract profile data
            profile_data = {
                'name': self._extract_name(soup),
                'headline': self._extract_headline(soup),
                'location': self._extract_location(soup),
                'about': self._extract_about(soup),
                'experience': self._extract_experience(soup),
                'education': self._extract_education(soup),
                'skills': self._extract_skills(soup),
                'certifications': self._extract_certifications(soup)
            }
            
            return profile_data
        except Exception as e:
            raise Exception(f"Error scraping LinkedIn profile: {str(e)}")

    def _extract_name(self, soup) -> str:
        """Extract name from LinkedIn profile."""
        try:
            name_element = soup.find('h1', class_='text-heading-xlarge')
            return name_element.text.strip() if name_element else ""
        except:
            return ""

    def _extract_headline(self, soup) -> str:
        """Extract headline from LinkedIn profile."""
        try:
            headline_element = soup.find('div', class_='text-body-medium')
            return headline_element.text.strip() if headline_element else ""
        except:
            return ""

    def _extract_location(self, soup) -> str:
        """Extract location from LinkedIn profile."""
        try:
            location_element = soup.find('span', class_='text-body-small')
            return location_element.text.strip() if location_element else ""
        except:
            return ""

    def _extract_about(self, soup) -> str:
        """Extract about section from LinkedIn profile."""
        try:
            about_element = soup.find('div', {'id': 'about'})
            return about_element.text.strip() if about_element else ""
        except:
            return ""

    def _extract_experience(self, soup) -> List[Dict]:
        """Extract work experience from LinkedIn profile."""
        experiences = []
        try:
            experience_section = soup.find('section', {'id': 'experience-section'})
            if experience_section:
                for exp in experience_section.find_all('li', class_='experience-item'):
                    experience = {
                        'title': exp.find('h3').text.strip() if exp.find('h3') else "",
                        'company': exp.find('p', class_='company-name').text.strip() if exp.find('p', class_='company-name') else "",
                        'date_range': exp.find('p', class_='date-range').text.strip() if exp.find('p', class_='date-range') else "",
                        'description': exp.find('p', class_='description').text.strip() if exp.find('p', class_='description') else ""
                    }
                    experiences.append(experience)
        except:
            pass
        return experiences

    def _extract_education(self, soup) -> List[Dict]:
        """Extract education from LinkedIn profile."""
        education = []
        try:
            education_section = soup.find('section', {'id': 'education-section'})
            if education_section:
                for edu in education_section.find_all('li', class_='education-item'):
                    education_item = {
                        'institution': edu.find('h3').text.strip() if edu.find('h3') else "",
                        'degree': edu.find('p', class_='degree').text.strip() if edu.find('p', class_='degree') else "",
                        'date_range': edu.find('p', class_='date-range').text.strip() if edu.find('p', class_='date-range') else "",
                        'description': edu.find('p', class_='description').text.strip() if edu.find('p', class_='description') else ""
                    }
                    education.append(education_item)
        except:
            pass
        return education

    def _extract_skills(self, soup) -> List[str]:
        """Extract skills from LinkedIn profile."""
        skills = []
        try:
            skills_section = soup.find('section', {'id': 'skills-section'})
            if skills_section:
                for skill in skills_section.find_all('span', class_='skill-name'):
                    skills.append(skill.text.strip())
        except:
            pass
        return skills

    def _extract_certifications(self, soup) -> List[Dict]:
        """Extract certifications from LinkedIn profile."""
        certifications = []
        try:
            cert_section = soup.find('section', {'id': 'certifications-section'})
            if cert_section:
                for cert in cert_section.find_all('li', class_='certification-item'):
                    certification = {
                        'name': cert.find('h3').text.strip() if cert.find('h3') else "",
                        'issuer': cert.find('p', class_='issuer').text.strip() if cert.find('p', class_='issuer') else "",
                        'date': cert.find('p', class_='date').text.strip() if cert.find('p', class_='date') else ""
                    }
                    certifications.append(certification)
        except:
            pass
        return certifications

    def parse_profile(self) -> Dict:
        """Parse LinkedIn profile data into structured format."""
        try:
            profile_data = self.scrape_profile()
            
            prompt = f"""Based on the following LinkedIn profile data, create a structured profile:

Profile Data:
{profile_data}

Please format the data as a JSON object with the following structure:
{{
    "work_experiences": [
        {{
            "company": "string",
            "position": "string",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM",
            "description": "string",
            "technologies": ["string"]
        }}
    ],
    "education": [
        {{
            "institution": "string",
            "degree": "string",
            "field_of_study": "string",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM",
            "gpa": "string",
            "achievements": ["string"]
        }}
    ],
    "skills": [
        {{
            "name": "string",
            "category": "string",
            "proficiency": "string"
        }}
    ],
    "certifications": [
        {{
            "name": "string",
            "issuer": "string",
            "issue_date": "YYYY-MM",
            "expiry_date": "YYYY-MM",
            "credential_id": "string"
        }}
    ]
}}
"""

            response = self.client.generate(prompt)
            return response
        except Exception as e:
            raise Exception(f"Error parsing LinkedIn profile: {str(e)}") 