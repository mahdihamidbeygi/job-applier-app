# Testing the Job Application Assistant Extension

This guide will help you test the browser extension thoroughly.

## Prerequisites

1. Make sure your Django backend is running:
```bash
python manage.py runserver
```

2. Load the extension in Chrome:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" in the top right
   - Click "Load unpacked" and select the extension directory

## Testing Steps

### 1. Manual Testing

1. Open the test page:
   - Navigate to `http://localhost:8000/extension/tests/test.html`
   - This page contains a sample job application form

2. Test the extension UI:
   - Click the extension icon in your Chrome toolbar
   - Verify that the popup opens correctly
   - Check if the "Detect Application Form" button is enabled
   - Click "Detect Application Form" and verify the status message
   - Verify that the "Fill Form" button becomes enabled after detection
   - Click "Fill Form" and verify the form is filled correctly

3. Test form field filling:
   - Check if all required fields are filled
   - Verify that the filled content is relevant to the job description
   - Test different field types (text, email, tel, textarea)
   - Verify that the form validation works

### 2. Automated Testing

1. Open Chrome DevTools:
   - Right-click on the test page and select "Inspect"
   - Go to the "Console" tab

2. Run the automated tests:
   - The tests will run automatically when the page loads
   - Check the console output for test results
   - Each test will show a ✓ for pass or ✗ for fail

### 3. Testing Different Scenarios

1. Test with different job descriptions:
   - Modify the job description in `test.html`
   - Verify that the form filling adapts to the new requirements

2. Test with different form layouts:
   - Add new fields to the form
   - Test with different field types
   - Verify that the extension handles the changes correctly

3. Test error handling:
   - Disconnect from the internet to test offline behavior
   - Test with invalid form fields
   - Verify error messages are displayed correctly

### 4. Security Testing

1. Test authentication:
   - Verify that the extension requires user authentication
   - Test with invalid credentials
   - Check if sensitive data is handled securely

2. Test data handling:
   - Verify that no sensitive data is stored in the extension
   - Check that API requests are secure
   - Verify that form data is processed securely

## Common Issues and Solutions

1. Form not detected:
   - Check if the page contains the required keywords
   - Verify that the form has the correct HTML structure
   - Check the console for any error messages

2. Form filling fails:
   - Verify the backend API is running
   - Check the network tab in DevTools for API requests
   - Verify that the user is authenticated

3. Extension not responding:
   - Try reloading the extension
   - Check the background script console
   - Verify that all required permissions are set

## Reporting Issues

When reporting issues, include:
1. Steps to reproduce the problem
2. Expected behavior
3. Actual behavior
4. Console logs and error messages
5. Screenshots if applicable

## Continuous Testing

For continuous testing:
1. Set up automated tests in your CI/CD pipeline
2. Test the extension on different Chrome versions
3. Test with different job application forms
4. Monitor error logs and user feedback 