import { Octokit } from '@octokit/rest';

// Types for GitHub data
interface GitHubUser {
  login: string;
  name: string;
  bio: string;
  company: string;
  blog: string;
  location: string;
  email: string;
  hireable: boolean;
  public_repos: number;
  avatar_url: string;
  html_url: string;
}

interface GitHubRepo {
  name: string;
  description: string;
  html_url: string;
  stargazers_count: number;
  language: string;
  topics: string[];
  created_at: string;
  updated_at: string;
  forks_count: number;
}

// Types for enriched profile data
interface EnrichedProfile {
  github?: {
    bio: string;
    skills: string[];
    projects: Array<{
      id: string;
      title: string;
      url: string;
      date: Date;
      description: string;
      isEditing: boolean;
      isDirty: boolean;
    }>;
    certifications: Array<{
      id: string;
      title: string;
      issuer: string;
      date: Date;
      url: string;
      isEditing: boolean;
      isDirty: boolean;
    }>;
  };
}

/**
 * Validates GitHub URL
 */
function validateGitHubUrl(url: string): string | null {
  if (!url) return null;
  
  // If it's just a username, convert it to a URL
  if (!url.includes('://')) {
    return `https://github.com/${url}`;
  }
  
  try {
    const parsedUrl = new URL(url);
    if (parsedUrl.hostname !== 'github.com') {
      return null;
    }
    
    // Return the full URL
    return url;
  } catch (error) {
    console.error('Error validating GitHub URL:', error);
    return null;
  }
}

/**
 * Generate mock GitHub data for testing or when API fails
 */
function generateMockGitHubData(username: string): {
  user: GitHubUser;
  repos: GitHubRepo[];
} {
  return {
    user: {
      login: username,
      name: username.charAt(0).toUpperCase() + username.slice(1),
      bio: "Software developer with expertise in web technologies",
      location: "San Francisco, CA",
      email: `${username}@example.com`,
      blog: `https://${username}.dev`,
      company: "Tech Company Inc.",
      avatar_url: `https://avatars.githubusercontent.com/${username}`,
      html_url: `https://github.com/${username}`,
      hireable: true,
      public_repos: 3
    },
    repos: [
      {
        name: "personal-website",
        description: "My personal website built with Next.js and Tailwind CSS",
        html_url: `https://github.com/${username}/personal-website`,
        language: "TypeScript",
        topics: ["nextjs", "tailwindcss", "react", "portfolio"],
        stargazers_count: 12,
        forks_count: 3,
        updated_at: new Date().toISOString(),
        created_at: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(), // 90 days ago
      },
      {
        name: "task-manager-app",
        description: "A full-stack task management application with authentication",
        html_url: `https://github.com/${username}/task-manager-app`,
        language: "JavaScript",
        topics: ["react", "nodejs", "express", "mongodb"],
        stargazers_count: 8,
        forks_count: 2,
        updated_at: new Date().toISOString(),
        created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(), // 60 days ago
      },
      {
        name: "data-visualization-dashboard",
        description: "Interactive dashboard for visualizing complex datasets",
        html_url: `https://github.com/${username}/data-visualization-dashboard`,
        language: "JavaScript",
        topics: ["d3js", "react", "data-visualization", "dashboard"],
        stargazers_count: 15,
        forks_count: 4,
        updated_at: new Date().toISOString(),
        created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days ago
      }
    ]
  };
}

/**
 * Fetch GitHub user data
 */
async function fetchGitHubData(githubUrl: string): Promise<{
  user: GitHubUser | null;
  repos: GitHubRepo[];
}> {
  if (!githubUrl) {
    return { user: null, repos: [] };
  }
  
  try {
    // Extract username from URL for API calls
    const parsedUrl = new URL(githubUrl);
    const pathParts = parsedUrl.pathname.split('/').filter(Boolean);
    const username = pathParts.length > 0 ? pathParts[0] : null;
    
    if (!username) {
      console.error('Could not extract username from GitHub URL:', githubUrl);
      return { user: null, repos: [] };
    }
    
    // Check if GitHub token is available
    const githubToken = process.env.GITHUB_TOKEN;
    if (!githubToken) {
      console.warn('GITHUB_TOKEN is not set. Generating mock GitHub data.');
      return generateMockGitHubData(username);
    }
    
    const octokit = new Octokit({
      auth: githubToken,
      request: {
        timeout: 10000 // 10 second timeout
      }
    });
    
    // Fetch user data
    const userResponse = await octokit.users.getByUsername({
      username,
    });
    
    // Fetch repositories
    const reposResponse = await octokit.repos.listForUser({
      username,
      sort: 'updated',
      per_page: 10,
    });
    
    return {
      user: userResponse.data as GitHubUser,
      repos: reposResponse.data as GitHubRepo[],
    };
  } catch (error) {
    console.error('Error fetching GitHub data:', error);
    
    // Try to extract username for mock data
    try {
      const parsedUrl = new URL(githubUrl);
      const pathParts = parsedUrl.pathname.split('/').filter(Boolean);
      const username = pathParts.length > 0 ? pathParts[0] : 'default';
      console.log('Falling back to mock GitHub data for:', username);
      return generateMockGitHubData(username);
    } catch (parseError) {
      console.error('Error parsing GitHub URL for mock data:', parseError);
      return generateMockGitHubData('default');
    }
  }
}

/**
 * Convert GitHub data to profile format
 */
function convertGitHubDataToProfile(data: {
  user: GitHubUser | null;
  repos: GitHubRepo[];
}): EnrichedProfile['github'] | undefined {
  if (!data.user) {
    return undefined;
  }
  
  // Extract skills from repository languages and topics
  const skills = new Set<string>();
  data.repos.forEach(repo => {
    if (repo.language) {
      skills.add(repo.language);
    }
    if (repo.topics) {
      repo.topics.forEach(topic => skills.add(topic));
    }
  });
  
  // Convert repositories to projects
  const projects = data.repos.map(repo => ({
    id: `github-${repo.name}`,
    title: repo.name,
    url: repo.html_url,
    date: new Date(repo.created_at),
    description: repo.description || '',
    isEditing: false,
    isDirty: false,
  }));
  
  return {
    bio: data.user.bio || '',
    skills: Array.from(skills),
    projects,
    certifications: [], // GitHub doesn't provide certification information
  };
}

/**
 * Enrich profile from GitHub
 */
export async function enrichProfileFromSocialMedia(
  githubUrl?: string
): Promise<EnrichedProfile> {
  const result: EnrichedProfile = {};
  
  // Process GitHub data
  if (githubUrl) {
    const validatedGithubUrl = validateGitHubUrl(githubUrl);
    if (validatedGithubUrl) {
      const githubData = await fetchGitHubData(validatedGithubUrl);
      result.github = convertGitHubDataToProfile(githubData);
    }
  }
  
  return result;
} 