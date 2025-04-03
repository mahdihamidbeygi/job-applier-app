document.addEventListener('DOMContentLoaded', function() {
    // Load saved settings
    chrome.storage.local.get([
        'apiEndpoint',
        'authToken',
        'refreshToken',
        'autoDetect',
        'autoFill',
        'username',
        'password'
    ], function(result) {
        console.log("Loading saved settings:", result);
        document.getElementById('api-endpoint').value = result.apiEndpoint || 'http://localhost:8000/api';
        document.getElementById('auth-token').value = result.authToken || '';
        document.getElementById('username').value = result.username || '';
        document.getElementById('password').value = result.password || '';
        document.getElementById('auto-detect').checked = result.autoDetect || false;
        document.getElementById('auto-fill').checked = result.autoFill || false;
    });

    // Save settings
    document.getElementById('save-settings').addEventListener('click', function() {
        const settings = {
            apiEndpoint: document.getElementById('api-endpoint').value,
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
            autoDetect: document.getElementById('auto-detect').checked,
            autoFill: document.getElementById('auto-fill').checked
        };

        console.log("Saving settings:", settings);
        chrome.storage.local.set(settings, function() {
            console.log("Settings saved successfully");
            const status = document.getElementById('status');
            status.textContent = 'Settings saved successfully!';
            status.className = 'status success';
            
            // Clear success message after 3 seconds
            setTimeout(() => {
                status.textContent = '';
                status.className = 'status';
            }, 3000);
        });
    });

    // Get token button
    document.getElementById('get-token').addEventListener('click', async function() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const apiEndpoint = document.getElementById('api-endpoint').value;
        const status = document.getElementById('status');

        if (!username || !password) {
            status.textContent = 'Please enter both username and password';
            status.className = 'status error';
            return;
        }

        try {
            await window.getNewToken(username, password, apiEndpoint);
            status.textContent = 'Token obtained and saved successfully!';
            status.className = 'status success';
        } catch (error) {
            console.error("Error getting token:", error);
            status.textContent = `Error: ${error.message}`;
            status.className = 'status error';
        }
    });

    // Validate API endpoint
    document.getElementById('api-endpoint').addEventListener('change', function() {
        const endpoint = this.value;
        if (!endpoint.startsWith('http://') && !endpoint.startsWith('https://')) {
            this.value = 'http://' + endpoint;
        }
    });
});

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

// Export functions for use in other files
window.getNewToken = getNewToken;
window.refreshToken = refreshToken; 