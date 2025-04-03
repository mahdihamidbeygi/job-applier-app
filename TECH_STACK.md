# Job Application Assistant - Technical Stack Documentation

## Overview
This document outlines the complete technical stack used in the Job Application Assistant, which consists of a Chrome browser extension and a Django backend application.

## Backend Stack

### Core Framework
- **Django 5.1.7+**: Main web framework
- **Django REST Framework**: For building RESTful APIs
- **Django REST Framework SimpleJWT**: For JWT-based authentication

### Database
- **PostgreSQL**: Primary database
- **psycopg2-binary**: PostgreSQL adapter

### Task Queue & Caching
- **Celery**: For asynchronous task processing
- **Redis**: Message broker and caching layer

### AI & Machine Learning
- **OpenAI API**: For AI-powered content generation
- **scikit-learn**: For machine learning tasks and vector operations

### Document Processing
- **python-docx**: For Microsoft Word document processing
- **pdfminer.six**: For PDF document parsing
- **Pillow**: For image processing
- **reportlab**: For PDF generation

### Web Scraping
- **Selenium**: For web automation and scraping
- **undetected-chromedriver**: For automated browser control
- **beautifulsoup4**: For HTML parsing
- **requests**: For HTTP requests

### Storage & Cloud
- **django-storages**: For handling file storage
- **boto3**: AWS SDK for cloud storage integration
- **cryptography**: For secure data handling

### Development Tools
- **pytest**: For testing
- **pylint**: For code linting
- **python-dotenv**: For environment variable management

## Frontend Stack (Browser Extension)

### Core Technologies
- **HTML5**: For extension structure
- **CSS3**: For styling
- **JavaScript**: For extension functionality
- **Chrome Extension APIs**: For browser integration

### Extension Components
- **manifest.json**: Extension configuration
- **popup.html/js**: Extension popup interface
- **content.js**: Page interaction logic
- **background.js**: Background tasks

## Development Environment

### Version Control
- **Git**: For source control
- **GitHub**: For repository hosting

### Development Tools
- **VS Code**: IDE with Python and JavaScript support
- **Chrome DevTools**: For extension debugging

### Environment Management
- **.env**: For environment variables
- **requirements.txt**: For Python dependencies
- **pyproject.toml**: For project configuration

## Security Features
- JWT-based authentication
- Secure document handling
- Environment variable protection
- Secure API endpoints
- Data encryption

## Deployment Requirements
- Python 3.8+
- Node.js (for extension development)
- Chrome browser
- PostgreSQL database
- Redis server
- AWS S3 (for document storage)

## Testing & Quality Assurance
- pytest for backend testing
- Chrome extension testing tools
- pylint for code quality
- Automated testing workflows

## Monitoring & Logging
- Django logging system
- Celery task monitoring
- Chrome extension console logging

This technical stack is designed to provide a robust, scalable, and secure solution for automated job application assistance, combining modern web technologies with AI capabilities. 