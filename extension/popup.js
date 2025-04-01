document.addEventListener('DOMContentLoaded', function() {
  const detectButton = document.getElementById('detectForm');
  const fillButton = document.getElementById('fillForm');
  const statusDiv = document.getElementById('status');
  const detectLoading = document.getElementById('detectLoading');
  const fillLoading = document.getElementById('fillLoading');
  const settingsLink = document.getElementById('openSettings');

  // Load settings
  chrome.storage.local.get(['autoDetect', 'autoFill'], function(result) {
    if (result.autoDetect) {
      detectForm();
    }
  });

  // Open settings page
  settingsLink.addEventListener('click', function(e) {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });

  // Check if we're on a job application page
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    chrome.tabs.sendMessage(tabs[0].id, {action: "checkForm"}, function(response) {
      if (response && response.hasForm) {
        detectButton.disabled = false;
        updateStatus('Form detected! Click "Detect Application Form" to analyze.', 'success');
      } else {
        updateStatus('No job application form detected on this page.', 'error');
      }
    });
  });

  detectButton.addEventListener('click', detectForm);
  fillButton.addEventListener('click', fillForm);

  async function detectForm() {
    setLoading(detectButton, detectLoading, true);
    updateStatus('Analyzing form...', 'success');

    try {
      const tabs = await chrome.tabs.query({active: true, currentWindow: true});
      const analysis = await chrome.tabs.sendMessage(tabs[0].id, {action: "analyzeForm"});
      
      if (analysis && analysis.success) {
        fillButton.disabled = false;
        updateStatus('Form analyzed successfully! Click "Fill Form" to proceed.', 'success');
      } else {
        throw new Error(analysis?.error || 'Form analysis failed');
      }
    } catch (error) {
      updateStatus('Failed to analyze form: ' + error.message, 'error');
    } finally {
      setLoading(detectButton, detectLoading, false);
    }
  }

  async function fillForm() {
    setLoading(fillButton, fillLoading, true);
    updateStatus('Filling form...', 'success');

    try {
      const tabs = await chrome.tabs.query({active: true, currentWindow: true});
      const fillResult = await chrome.tabs.sendMessage(tabs[0].id, {action: "fillForm"});
      
      if (fillResult && fillResult.success) {
        updateStatus('Form filled successfully!', 'success');
      } else {
        throw new Error(fillResult?.error || 'Form filling failed');
      }
    } catch (error) {
      updateStatus('Failed to fill form: ' + error.message, 'error');
    } finally {
      setLoading(fillButton, fillLoading, false);
    }
  }

  function updateStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = 'status ' + type;
  }

  function setLoading(button, spinner, isLoading) {
    button.disabled = isLoading;
    spinner.style.display = isLoading ? 'block' : 'none';
  }
}); 