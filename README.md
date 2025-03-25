# AI-Powered Job Application System

An intelligent job application automation system that helps users find and apply for jobs using AI.

## Features

- Profile analysis from LinkedIn and GitHub
- Automated job search across multiple platforms
- AI-powered resume and cover letter generation
- Automated job application submission
- Job matching and recommendation system
- Pydantic-powered data validation and AI integration

## Technology Stack

- Django 5.0+
- PostgreSQL
- Redis
- Celery
- OpenAI GPT-4
- Playwright
- BeautifulSoup4
- Pydantic & Pydantic AI

## Prerequisites

- Python 3.9+
- pip (Python package manager)
- PostgreSQL
- Redis
- OpenAI API key

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/job-applier.git
cd job-applier
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Unix or MacOS:
source venv/bin/activate
```

3. Install dependencies:
```bash
# Install main dependencies
pip install -e .

# Install development dependencies (optional)
pip install -e ".[dev]"
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up the database:
```bash
python manage.py migrate
```

6. Install Playwright browsers:
```bash
playwright install
```

7. Run the development server:
```bash
python manage.py runserver
```

8. Start Celery worker:
```bash
celery -A config worker -l info
```

9. Start Celery beat for scheduled tasks:
```bash
celery -A config beat -l info
```

## Project Structure

```
job_applier/
├── apps/
│   ├── users/          # User management
│   ├── profiles/       # Profile management
│   ├── jobs/          # Job search and management
│   └── applications/  # Application handling
├── services/
│   ├── ai/           # AI services
│   ├── scraping/     # Web scraping
│   └── automation/   # Form automation
├── config/           # Project configuration
└── tests/           # Test files
```

## Development

1. Run tests:
```bash
pytest
```

2. Format code:
```bash
black .
isort .
```

3. Type checking:
```bash
mypy .
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is designed to assist with job applications but should be used responsibly and in accordance with each job platform's terms of service. Always review applications before submission and ensure compliance with platform policies.
