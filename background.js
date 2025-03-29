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
    chrome.storage.local.get(['enabled', 'apiEndpoint'], function(result) {
      sendResponse(result);
    });
    return true; // Required for async response
  }
}); 