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