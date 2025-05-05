# Job Application Assistant

A comprehensive job application assistant that helps you manage and streamline your job search process. The platform consists of a web application and browser extension that work together to help you fill out job applications, generate tailored documents, and track your applications.

## Features

### Web Application
- User profile management
- Application tracking and management
- AI-powered document generation
  - Tailored resumes
  - Custom cover letters
  - Application question answers
- Application status tracking
- Document library management

### Browser Extension
- Automatically detects job application forms on web pages
- Analyzes form fields and job descriptions
- Uses your personal profile and experience to generate relevant responses
- Fills out forms with AI-generated content
- Maintains consistency across applications
- Seamless integration with the web application

## Installation

### Web Application
1. Clone this repository
2. Install Python dependencies:
```bash
pip install -r requirements.txt
```
3. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```
4. Run the Django development server:
```bash
python manage.py runserver
```

### Browser Extension
1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" in the top right
3. Click "Load unpacked" and select the extension directory
4. The extension icon should appear in your Chrome toolbar

## Usage

### Web Application
1. Create an account and set up your profile
2. Access your dashboard to:
   - Track applications
   - Generate documents
   - Manage your profile
   - View application history

### Browser Extension
1. Navigate to a job application page
2. Click the extension icon in your Chrome toolbar
3. Click "Detect Application Form" to analyze the form
4. Review the detected fields
5. Click "Fill Form" to automatically fill out the form with AI-generated responses

### Document Generation
The system generates the following documents with personalized naming:
- Resume: `resume_[username]_[date]_[time].pdf`
- Cover Letter: `cover_letter_[username]_[date]_[time].pdf`
- Application Answers: Displayed directly on the page

## Development

### Prerequisites
- Python 3.8+
- Django
- Chrome browser
- Node.js (for building the extension)

### Project Structure
- `backend/`: Django web application
- `extension/`: Chrome extension
- `frontend/`: Web application frontend
- `docs/`: Documentation

### Backend Integration

The system uses the following main endpoints:

- `POST /api/fill-form/`: Handles form filling requests
  - Request body: `{ fields: [...], jobDescription: string }`
  - Response: `{ success: boolean, responses: {...} }`

- `POST /process-application/`: Handles manual document generation
  - Request body: `{ job_description: string, document_type: string, additional_services: {...} }`
  - Response: `{ documents: {...}, answers: [...] }`

## Security

- All API requests require authentication
- Form data is processed securely on the backend
- No sensitive data is stored in the extension
- Generated documents are named with user identification for security
- Secure user authentication and authorization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details

## JSON Schema Generation

This project includes tools for generating JSON schemas from Django models.

### Using Schema Generation API Endpoints

The following API endpoints are available for schema generation:

- `GET /api/schema/models/<model_name>/` - Get JSON schema for a specific model
- `GET /api/schema/app/<app_name>/` - Get JSON schemas for all models in an app
- `GET /api/schema/models/` - Get JSON schemas for all models in all apps

These endpoints require authentication.

### Using Schema Generation in Code

You can use the schema generation tools in your code by using the methods available on any model that inherits from `TimestampMixin`.

```python
from core.models import UserProfile, WorkExperience

# Get schema for a model
schema = UserProfile.get_schema()
schema_json = UserProfile.get_schema_as_json()

# Get schemas for all models in the core app
from core.models.base import TimestampMixin
all_schemas = TimestampMixin.get_app_schemas('core')
all_schemas_json = TimestampMixin.get_app_schemas_as_json('core')
```

### Exporting Schemas to Files

You can export schemas to files using the `export_schema` management command:

```bash
# Export schema for a specific model
python manage.py export_schema --model UserProfile --output userprofile_schema.json

# Export schemas for all models in an app
python manage.py export_schema --app core --output core_schemas.json

# Export schemas for all apps and models
python manage.py export_schema --all --output all_schemas.json

# Include abstract models
python manage.py export_schema --include-abstract --output schemas_with_abstract.json
```

### Schema Format

The generated schemas follow the JSON Schema standard. Here's an example schema for a simple model:

```json
{
  "type": "object",
  "title": "UserProfile",
  "properties": {
    "id": {
      "type": "integer"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    },
    "phone": {
      "type": "string"
    },
    "address": {
      "type": "string"
    }
  },
  "required": ["id", "created_at", "updated_at"]
}
``` 