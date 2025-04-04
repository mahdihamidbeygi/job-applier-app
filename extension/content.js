// Guard against multiple injections
if (window.jobAssistantInitialized) {
  console.log('Content script already initialized');
} else {
  window.jobAssistantInitialized = true;

  // Form detection and analysis
  window.jobAssistant = {
    formData: null,
    formCache: new Map() // Cache for analyzed forms
  };

  // Listen for messages from the popup
  chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    switch (request.action) {
      case "ping":
        sendResponse({status: "ok"});
        break;
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

  async function ensureValidToken() {
    const settings = await new Promise(resolve => {
      chrome.storage.local.get(['apiEndpoint', 'authToken', 'refreshToken', 'username', 'password'], resolve);
    });

    if (!settings.apiEndpoint) {
      throw new Error('API endpoint not configured');
    }

    // If we have a refresh token, try to refresh first
    if (settings.refreshToken) {
      try {
        return await window.refreshToken(settings.refreshToken, settings.apiEndpoint);
      } catch (error) {
        console.log("Token refresh failed, will try to get new token:", error);
      }
    }

    // If refresh failed or no refresh token, get new token with credentials
    if (!settings.username || !settings.password) {
      throw new Error('Please configure your credentials in the extension settings');
    }

    const tokenData = await window.getNewToken(settings.username, settings.password, settings.apiEndpoint);
    return tokenData.access;
  }

  async function makeAuthenticatedRequest(url, options) {
    try {
      // Ensure we have a valid token
      const token = await ensureValidToken();

      // Make the request with the token
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token.trim()}`
        }
      });

      if (response.status === 401) {
        // If still unauthorized after token refresh, throw error
        throw new Error('Authentication failed');
      }

      return response;
    } catch (error) {
      console.error("Error in authenticated request:", error);
      throw error;
    }
  }

  function detectJobApplicationForm() {
    // Simple form detection logic
    const forms = document.forms;
    for (let form of forms) {
      const formText = form.innerText.toLowerCase();
      const inputs = form.querySelectorAll('input, textarea');
      
      // Check if form contains job application related fields
      const jobRelatedTerms = ['job', 'career', 'application', 'resume', 'cv', 'cover letter', 'position'];
      const hasJobTerms = jobRelatedTerms.some(term => formText.includes(term));
      
      // Check for common job application input fields
      const hasCommonFields = Array.from(inputs).some(input => {
        const fieldName = (input.name || input.id || '').toLowerCase();
        return fieldName.includes('name') || 
               fieldName.includes('email') || 
               fieldName.includes('phone') || 
               fieldName.includes('experience') ||
               fieldName.includes('resume');
      });
      
      if (hasJobTerms && hasCommonFields) {
        return true;
      }
    }
    return false;
  }

  async function analyzeForm() {
    try {
      const form = document.querySelector('form');
      if (!form) {
        return {success: false, error: 'No form found'};
      }

      // Check cache first
      const formHash = await getFormHash(form);
      if (window.jobAssistant.formCache.has(formHash)) {
        console.log('Using cached form analysis');
        window.jobAssistant.formData = window.jobAssistant.formCache.get(formHash);
        return {success: true, fields: window.jobAssistant.formData.fields.length, cached: true};
      }

      // Create a map of field elements for faster lookups
      const fieldMap = new Map();
      Array.from(form.elements).forEach(element => {
        fieldMap.set(element.id || element.name, element);
      });

      // Extract form fields and job description in parallel
      const [fields, jobDescription] = await Promise.all([
        Promise.all(
          Array.from(form.elements).map(async element => {
            const label = await getFieldLabel(element);
            const fieldType = determineFieldType(element, label);
            
            return {
              id: element.id || element.name,
              type: element.type,
              label: label,
              required: element.required,
              value: element.value,
              fieldType: fieldType,
              options: element.options ? Array.from(element.options).map(opt => opt.value) : null,
              maxLength: element.maxLength,
              placeholder: element.placeholder,
              isTextArea: element.tagName.toLowerCase() === 'textarea'
            };
          })
        ),
        extractJobDescription()
      ]);

      // Store form data
      window.jobAssistant.formData = {
        fields,
        jobDescription,
        formId: form.id || 'main-form'
      };

      // Cache the results
      window.jobAssistant.formCache.set(formHash, window.jobAssistant.formData);

      return {success: true, fields: fields.length};
    } catch (error) {
      return {success: false, error: error.message};
    }
  }

  function determineFieldType(element, label) {
    const labelLower = label.toLowerCase();
    const elementType = element.type.toLowerCase();
    
    // Check for technical experience questions
    if (labelLower.includes('experience') || labelLower.includes('skill')) {
      if (labelLower.includes('test') || labelLower.includes('testing')) {
        return 'technical_testing';
      }
      if (labelLower.includes('front') || labelLower.includes('back') || labelLower.includes('end')) {
        return 'technical_stack';
      }
      if (labelLower.includes('framework') || labelLower.includes('library')) {
        return 'technical_framework';
      }
    }

    // Check for other common question types
    if (labelLower.includes('describe') || labelLower.includes('tell us about')) {
      return 'descriptive';
    }
    if (labelLower.includes('why') || labelLower.includes('motivation')) {
      return 'motivational';
    }
    if (labelLower.includes('salary') || labelLower.includes('compensation')) {
      return 'salary';
    }
    if (labelLower.includes('availability') || labelLower.includes('start date')) {
      return 'availability';
    }

    // Default types based on input type
    switch (elementType) {
      case 'radio':
        return 'single_choice';
      case 'checkbox':
        return 'multiple_choice';
      case 'select-one':
        return 'single_choice';
      case 'select-multiple':
        return 'multiple_choice';
      case 'textarea':
        return 'descriptive';
      default:
        return 'text';
    }
  }

  async function fillForm() {
    if (!window.jobAssistant.formData) {
      return {success: false, error: 'Form not analyzed'};
    }

    try {
      const settings = await new Promise(resolve => {
        chrome.storage.local.get(['apiEndpoint', 'authToken'], resolve);
      });

      if (!settings.apiEndpoint || !settings.authToken) {
        throw new Error('API endpoint or auth token not configured');
      }

      // Send form data to backend with enhanced context
      const response = await makeAuthenticatedRequest(`${settings.apiEndpoint}/fill-form/`, {
        method: 'POST',
        body: JSON.stringify({
          ...window.jobAssistant.formData,
          context: {
            isTechnicalRole: window.jobAssistant.formData.fields.some(field => 
              field.fieldType.startsWith('technical_')
            ),
            hasComplexQuestions: window.jobAssistant.formData.fields.some(field =>
              field.fieldType === 'descriptive' || field.fieldType === 'technical_testing'
            )
          }
        })
      });
      
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Failed to get AI responses');
      }

      // Batch process field updates with enhanced handling
      const fieldMap = new Map();
      
      // First pass: collect all field elements
      Object.entries(data.responses).forEach(([fieldId, value]) => {
        const element = document.getElementById(fieldId) || 
                       document.querySelector(`[name="${fieldId}"]`);
        if (element) {
          fieldMap.set(element, value);
        }
      });

      // Second pass: batch update fields with type-specific handling
      const batchSize = 10;
      const elements = Array.from(fieldMap.keys());
      
      for (let i = 0; i < elements.length; i += batchSize) {
        const batch = elements.slice(i, i + batchSize);
        
        // Update values in batch with type-specific handling
        batch.forEach(element => {
          const value = fieldMap.get(element);
          const field = window.jobAssistant.formData.fields.find(f => 
            f.id === element.id || f.id === element.name
          );

          if (field) {
            switch (field.fieldType) {
              case 'technical_testing':
              case 'technical_stack':
              case 'technical_framework':
                // For technical questions, ensure proper formatting
                element.value = formatTechnicalResponse(value);
                break;
              case 'descriptive':
                // For descriptive questions, ensure proper paragraph formatting
                element.value = formatDescriptiveResponse(value);
                break;
              case 'multiple_choice':
                // Handle multiple choice (checkboxes)
                if (Array.isArray(value)) {
                  value.forEach(option => {
                    const checkbox = document.querySelector(`input[type="checkbox"][value="${option}"]`);
                    if (checkbox) checkbox.checked = true;
                  });
                }
                break;
              default:
                element.value = value;
            }
          } else {
            element.value = value;
          }
        });

        // Trigger change events once per batch
        batch.forEach(element => {
          element.dispatchEvent(new Event('change', { bubbles: true }));
        });

        // Small delay between batches to prevent overwhelming the page
        if (i + batchSize < elements.length) {
          await new Promise(resolve => setTimeout(resolve, 20));
        }
      }

      return {success: true};
    } catch (error) {
      console.error("Error in fillForm:", error);
      return {success: false, error: error.message};
    }
  }

  function formatTechnicalResponse(value) {
    // Format technical responses with proper spacing and bullet points
    if (typeof value === 'string') {
      return value
        .split('\n')
        .map(line => line.trim())
        .filter(line => line)
        .join('\n\n');
    }
    return value;
  }

  function formatDescriptiveResponse(value) {
    // Format descriptive responses with proper paragraph structure
    if (typeof value === 'string') {
      return value
        .split('\n')
        .map(line => line.trim())
        .filter(line => line)
        .join('\n\n');
    }
    return value;
  }

  async function getFieldLabel(element) {
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

  async function extractJobDescription() {
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
        if (text.length > 100) {
          return text;
        }
      }
    }

    // Fallback to page title and meta description
    const title = document.title;
    const metaDesc = document.querySelector('meta[name="description"]')?.content;
    return `${title}\n${metaDesc || ''}`;
  }

  async function getFormHash(form) {
    // Create a simple hash of the form's structure
    const formStructure = Array.from(form.elements).map(el => ({
      id: el.id,
      name: el.name,
      type: el.type,
      required: el.required
    }));
    
    return JSON.stringify(formStructure);
  }
} 