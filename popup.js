document.addEventListener('DOMContentLoaded', function() {
  const detectButton = document.getElementById('detectForm');
  const fillButton = document.getElementById('fillForm');
  const statusDiv = document.getElementById('status');

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

  detectButton.addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      updateStatus('Analyzing form...', 'success');
      chrome.tabs.sendMessage(tabs[0].id, {action: "analyzeForm"}, function(response) {
        if (response && response.success) {
          fillButton.disabled = false;
          updateStatus('Form analyzed successfully! Click "Fill Form" to proceed.', 'success');
        } else {
          updateStatus('Failed to analyze form. Please try again.', 'error');
        }
      });
    });
  });

  fillButton.addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      updateStatus('Filling form...', 'success');
      chrome.tabs.sendMessage(tabs[0].id, {action: "fillForm"}, function(response) {
        if (response && response.success) {
          updateStatus('Form filled successfully!', 'success');
        } else {
          updateStatus('Failed to fill form. Please try again.', 'error');
        }
      });
    });
  });

  function updateStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = 'status ' + type;
  }
}); 