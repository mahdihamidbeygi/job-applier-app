document.addEventListener('DOMContentLoaded', function() {
    // Load saved settings
    chrome.storage.local.get([
        'apiEndpoint',
        'authToken',
        'refreshToken',
        'autoDetect',
        'autoFill'
    ], function(result) {
        console.log("Loading saved settings:", result);
        document.getElementById('api-endpoint').value = result.apiEndpoint || 'http://localhost:8000/api';
        document.getElementById('auth-token').value = result.authToken || '';
        document.getElementById('auto-detect').checked = result.autoDetect || false;
        document.getElementById('auto-fill').checked = result.autoFill || false;
    });

    // Save settings
    document.getElementById('save-settings').addEventListener('click', function() {
        const settings = {
            apiEndpoint: document.getElementById('api-endpoint').value,
            authToken: document.getElementById('auth-token').value,
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

            // Save both tokens
            document.getElementById('auth-token').value = data.access.trim();
            
            // Save to chrome storage
            const settings = {
                apiEndpoint: apiEndpoint.trim(),
                authToken: data.access.trim(),
                refreshToken: data.refresh.trim()
            };
            console.log("Saving token settings:", settings);
            
            chrome.storage.local.set(settings, function() {
                console.log("Token settings saved");
                status.textContent = 'Token obtained and saved successfully!';
                status.className = 'status success';
            });
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