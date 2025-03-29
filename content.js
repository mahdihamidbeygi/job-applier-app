// Form detection and analysis
let formData = null;

// Listen for messages from the popup
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  switch (request.action) {
    case "checkForm":
      sendResponse({hasForm: detectJobApplicationForm()});
      break;
    case "analyzeForm":
      analyzeForm().then(response => sendResponse(response));
      return true; // Required for async response
    case "fillForm":
      fillForm().then(response => sendResponse(response));
      return true; // Required for async response
  }
});

function detectJobApplicationForm() {
  // Look for common job application form indicators
  const indicators = [
    'job application',
    'apply now',
    'submit application',
    'careers',
    'work with us',
    'join our team'
  ];
  
  const pageText = document.body.innerText.toLowerCase();
  const hasIndicators = indicators.some(indicator => pageText.includes(indicator));
  
  // Check for form elements
  const forms = document.getElementsByTagName('form');
  const hasForm = forms.length > 0;
  
  return hasIndicators && hasForm;
}

async function analyzeForm() {
  try {
    const form = document.querySelector('form');
    if (!form) {
      return {success: false, error: 'No form found'};
    }

    // Extract form fields
    const fields = Array.from(form.elements).map(element => ({
      id: element.id || element.name,
      type: element.type,
      label: getFieldLabel(element),
      required: element.required,
      value: element.value
    }));

    // Extract job description
    const jobDescription = extractJobDescription();

    // Store form data for later use
    formData = {
      fields,
      jobDescription,
      formId: form.id || 'main-form'
    };

    return {success: true, fields: fields.length};
  } catch (error) {
    return {success: false, error: error.message};
  }
}

async function fillForm() {
  if (!formData) {
    return {success: false, error: 'Form not analyzed'};
  }

  try {
    // Send form data to backend
    const response = await fetch('http://localhost:8000/api/fill-form/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(formData)
    });

    if (!response.ok) {
      throw new Error('Failed to get AI responses');
    }

    const data = await response.json();
    
    // Fill form fields with AI responses
    Object.entries(data.responses).forEach(([fieldId, value]) => {
      const element = document.getElementById(fieldId) || 
                     document.querySelector(`[name="${fieldId}"]`);
      if (element) {
        element.value = value;
        // Trigger change event to ensure form validation works
        element.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });

    return {success: true};
  } catch (error) {
    return {success: false, error: error.message};
  }
}

function getFieldLabel(element) {
  // Try to find label by id
  const labelById = document.querySelector(`label[for="${element.id}"]`);
  if (labelById) return labelById.textContent.trim();

  // Try to find parent label
  const parentLabel = element.closest('label');
  if (parentLabel) return parentLabel.textContent.trim();

  // Try to find nearby text
  const nearbyText = element.previousElementSibling?.textContent.trim() ||
                    element.nextElementSibling?.textContent.trim();
  if (nearbyText) return nearbyText;

  // Fallback to placeholder or name
  return element.placeholder || element.name || element.id || 'Unknown Field';
}

function extractJobDescription() {
  // Look for job description in common locations
  const selectors = [
    '#job-description',
    '.job-description',
    '[data-testid="job-description"]',
    '#description',
    '.description',
    'article',
    'main'
  ];

  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      const text = element.innerText.trim();
      if (text.length > 100) { // Ensure we have meaningful content
        return text;
      }
    }
  }

  // Fallback to page title and meta description
  const title = document.title;
  const metaDesc = document.querySelector('meta[name="description"]')?.content;
  return `${title}\n${metaDesc || ''}`;
} 