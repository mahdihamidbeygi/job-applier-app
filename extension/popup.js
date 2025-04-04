document.addEventListener('DOMContentLoaded', async function() {
  const detectButton = document.getElementById('detectForm');
  const fillButton = document.getElementById('fillForm');
  const statusDiv = document.getElementById('status');
  const detectLoading = document.getElementById('detectLoading');
  const fillLoading = document.getElementById('fillLoading');
  const settingsLink = document.getElementById('openSettings');

  // Disable buttons initially
  detectButton.disabled = true;
  fillButton.disabled = true;

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

  // Initialize the extension
  await initializeExtension();

  // Add event listeners
  detectButton.addEventListener('click', detectForm);
  fillButton.addEventListener('click', fillForm);

  async function initializeExtension() {
    try {
      // Get current tab
      const tabs = await chrome.tabs.query({active: true, currentWindow: true});
      const currentTab = tabs[0];
      
      if (!currentTab) {
        throw new Error('No active tab found');
      }

      // Check if we can inject scripts
      if (!currentTab.url.startsWith('http')) {
        throw new Error('Extension can only work on web pages');
      }

      // Try to inject content scripts
      try {
        await injectContentScripts(currentTab.id);
      } catch (error) {
        console.error('Failed to inject content scripts:', error);
        throw new Error('Failed to initialize extension');
      }

      // Check for form
      const response = await chrome.tabs.sendMessage(currentTab.id, {action: "checkForm"});
      if (response && response.hasForm) {
        detectButton.disabled = false;
        updateStatus('Form detected! Click "Detect Application Form" to analyze.', 'success');
      } else {
        updateStatus('No job application form detected on this page.', 'error');
      }
    } catch (error) {
      console.error('Initialization error:', error);
      updateStatus(error.message, 'error');
    }
  }

  async function injectContentScripts(tabId) {
    // Check if content scripts are already loaded
    try {
      await chrome.tabs.sendMessage(tabId, {action: "ping"});
      console.log('Content scripts already loaded');
      return;
    } catch (error) {
      console.log('Content scripts not loaded, injecting...');
    }

    // Inject utils.js first
    await chrome.scripting.executeScript({
      target: { tabId: tabId },
      files: ['utils.js']
    });

    // Then inject content.js
    await chrome.scripting.executeScript({
      target: { tabId: tabId },
      files: ['content.js']
    });

    // Verify injection
    try {
      await chrome.tabs.sendMessage(tabId, {action: "ping"});
      console.log('Content scripts successfully injected');
    } catch (error) {
      throw new Error('Failed to verify content script injection');
    }
  }

  async function detectForm() {
    setLoading(detectButton, detectLoading, true);
    updateStatus('Analyzing form...', 'success');

    try {
      const tabs = await chrome.tabs.query({active: true, currentWindow: true});
      if (!tabs[0]) {
        throw new Error('No active tab found');
      }

      // Ensure content scripts are loaded
      await injectContentScripts(tabs[0].id);

      const analysis = await chrome.tabs.sendMessage(tabs[0].id, {action: "analyzeForm"});
      
      if (analysis && analysis.success) {
        fillButton.disabled = false;
        updateStatus('Form analyzed successfully! Click "Fill Form" to proceed.', 'success');
      } else {
        throw new Error(analysis?.error || 'Form analysis failed');
      }
    } catch (error) {
      console.error('Error:', error);
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
      if (!tabs[0]) {
        throw new Error('No active tab found');
      }

      // Ensure content scripts are loaded
      await injectContentScripts(tabs[0].id);

      const fillResult = await chrome.tabs.sendMessage(tabs[0].id, {action: "fillForm"});
      
      if (fillResult && fillResult.success) {
        updateStatus('Form filled successfully!', 'success');
      } else {
        throw new Error(fillResult?.error || 'Form filling failed');
      }
    } catch (error) {
      console.error('Error:', error);
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