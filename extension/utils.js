// Function to get a new token
async function getNewToken(username, password, apiEndpoint) {
    console.log("Requesting token from:", `${apiEndpoint}/token/`);
    console.log("Request body:", { username, password });
    
    const response = await fetch(`${apiEndpoint}/token/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password })
    });

    console.log("Response status:", response.status);
    console.log("Response headers:", Object.fromEntries(response.headers.entries()));
    
    const data = await response.json();
    console.log("Token response:", data);

    if (!response.ok) {
        throw new Error(data.error || data.detail || 'Failed to get token');
    }

    if (!data.access || !data.refresh) {
        throw new Error('Invalid token response format');
    }

    // Save both tokens and credentials
    const settings = {
        apiEndpoint: apiEndpoint.trim(),
        authToken: data.access.trim(),
        refreshToken: data.refresh.trim(),
        username: username,
        password: password
    };
    console.log("Saving token settings:", settings);
    
    await new Promise((resolve) => {
        chrome.storage.local.set(settings, resolve);
    });
    
    return data;
}

// Function to refresh token
async function refreshToken(refreshToken, apiEndpoint) {
    console.log("Refreshing token with:", refreshToken);
    const response = await fetch(`${apiEndpoint}/token/refresh/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh: refreshToken.trim() })
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to refresh token');
    }

    const data = await response.json();
    console.log("Token refresh response:", data);
    
    // Save new access token
    await new Promise((resolve) => {
        chrome.storage.local.set({ authToken: data.access.trim() }, resolve);
    });
    
    return data.access;
}

// Export functions based on context
if (typeof window !== 'undefined') {
    // Content script context
    window.getNewToken = getNewToken;
    window.refreshToken = refreshToken;
} else {
    // Service worker context
    self.getNewToken = getNewToken;
    self.refreshToken = refreshToken;
} 