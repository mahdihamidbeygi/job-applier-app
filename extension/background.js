// Import shared functions
importScripts('utils.js');

// Listen for installation
chrome.runtime.onInstalled.addListener(function() {
  // Initialize extension settings
  chrome.storage.local.set({
    enabled: true,
    apiEndpoint: 'http://localhost:8000/api'
  });
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === "getSettings") {
    chrome.storage.local.get(['enabled', 'apiEndpoint', 'authToken', 'refreshToken', 'username', 'password'], function(result) {
      sendResponse(result);
    });
    return true; // Required for async response
  }
});

// Listen for storage changes
chrome.storage.onChanged.addListener(function(changes, namespace) {
  if (namespace === 'local') {
    // If credentials are saved and no token exists, try to get a token
    if (changes.username || changes.password) {
      chrome.storage.local.get(['username', 'password', 'apiEndpoint', 'authToken'], function(result) {
        if (result.username && result.password && result.apiEndpoint && !result.authToken) {
          window.getNewToken(result.username, result.password, result.apiEndpoint)
            .then(() => console.log('Initial token created successfully'))
            .catch(error => console.error('Failed to create initial token:', error));
        }
      });
    }
  }
}); 