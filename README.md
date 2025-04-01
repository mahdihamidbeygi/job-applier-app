# Job Application Assistant Browser Extension

A Chrome extension that helps you fill out job application forms using AI-powered personal and application agents.

## Features

- Automatically detects job application forms on web pages
- Analyzes form fields and job descriptions
- Uses your personal profile and experience to generate relevant responses
- Fills out forms with AI-generated content
- Maintains consistency across applications
- Manual job application submission with tailored documents
- AI-powered cover letter and resume generation
- Application question answer generation

## Installation

1. Clone this repository
2. Open Chrome and go to `chrome://extensions/`
3. Enable "Developer mode" in the top right
4. Click "Load unpacked" and select the extension directory
5. The extension icon should appear in your Chrome toolbar

## Usage

### Browser Extension
1. Navigate to a job application page
2. Click the extension icon in your Chrome toolbar
3. Click "Detect Application Form" to analyze the form
4. Review the detected fields
5. Click "Fill Form" to automatically fill out the form with AI-generated responses

### Manual Submission
1. Go to the Manual Submission page
2. Paste the job description
3. Choose to generate:
   - Tailored Resume
   - Cover Letter
   - Application Question Answers
4. Download the generated documents

### Generated Documents
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

### Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Run the Django development server:
```bash
python manage.py runserver
```

4. Load the extension in Chrome:
- Go to `chrome://extensions/`
- Enable "Developer mode"
- Click "Load unpacked"
- Select the extension directory

### Extension Structure

- `manifest.json`: Extension configuration
- `popup.html`: Extension popup interface
- `popup.js`: Popup logic
- `content.js`: Page interaction logic
- `background.js`: Background tasks
- `icons/`: Extension icons

### Backend Integration

The extension communicates with your Django backend through the following endpoints:

- `POST /api/fill-form/`: Handles form filling requests
  - Request body: `{ fields: [...], jobDescription: string }`
  - Response: `{ success: boolean, responses: {...} }`

- `POST /process-application/`: Handles manual document generation
  - Request body: `{ job_description: string, document_type: string, additional_services: {...} }`
  - Response: `{ documents: {...}, answers: [...] }`

## Security

- The extension only runs on job application pages
- All API requests require authentication
- Form data is processed securely on the backend
- No sensitive data is stored in the extension
- Generated documents are named with user identification for security

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details 