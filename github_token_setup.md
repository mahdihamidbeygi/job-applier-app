# Setting Up GitHub API Token

To fix the "rate limit exceeded" error when importing GitHub profiles, you need to set up a GitHub Personal Access Token and add it to your environment variables.

## Step 1: Create a GitHub Personal Access Token

1. Log in to your GitHub account
2. Click on your profile picture in the top-right corner and select **Settings**
3. In the left sidebar, click on **Developer settings**
4. Click on **Personal access tokens** → **Tokens (classic)**
5. Click **Generate new token** → **Generate new token (classic)**
6. Give your token a descriptive name, e.g., "Job Applier App"
7. For the scope, you only need **read-only** access to public information. Select:
   - `public_repo` 
   - `read:user`
8. Click **Generate token**
9. **Important**: Copy the token immediately! GitHub will only show it once.

## Step 2: Add the Token to Your Environment

### Option 1: Add to .env file
1. Open your project's `.env` file (or create one in the project root if it doesn't exist)
2. Add the following line:
   ```
   GITHUB_TOKEN=your_token_here
   ```
3. Replace `your_token_here` with the token you copied from GitHub
4. Save the file

### Option 2: Set as environment variable
**Windows PowerShell:**
```
$env:GITHUB_TOKEN="your_token_here"
```

**macOS or Linux:**
```
export GITHUB_TOKEN=your_token_here
```

## Step 3: Restart Your Application

After setting the token, restart your Django application for the changes to take effect.

## Verification

After restarting, try importing a GitHub profile again. You should no longer see the "rate limit exceeded" error. The GitHub API allows authenticated requests up to 5,000 requests per hour instead of just 60 for unauthenticated requests.

## Security Notes

- Never commit your GitHub token to version control
- Keep your token secure as it can grant access to your GitHub account
- Consider using a token with minimal permissions (as described above)
- Revoke the token from GitHub if you suspect it has been compromised 