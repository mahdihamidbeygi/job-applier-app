import { LinkedInProfile } from './linkedinParserLangChain';

/**
 * Validate LinkedIn URL
 * @param url The LinkedIn URL
 * @returns The validated LinkedIn URL or null if not valid
 */
export function validateLinkedInUrl(url) {
  if (!url) return null;
  
  try {
    const parsedUrl = new URL(url);
    if (!parsedUrl.hostname.includes('linkedin.com')) {
      return null;
    }
    
    // Return the full URL
    return url;
  } catch (error) {
    console.error('Error validating LinkedIn URL:', error);
    return null;
  }
}

/**
 * Fetch LinkedIn profile data using the Proxycurl API
 * @param linkedInUrl The LinkedIn profile URL
 * @returns Structured LinkedIn profile data
 */
export async function fetchLinkedInDataWithProxycurl(linkedInUrl) {
  if (!linkedInUrl) {
    return null;
  }
  
  try {
    // Check if API key is available
    const apiKey = process.env.PROXYCURL_API_KEY;
    if (!apiKey) {
      console.warn('PROXYCURL_API_KEY is not set. Generating mock LinkedIn profile data.');
      return null; // Return null to try other methods instead of mock data
    }
    
    console.log(`Fetching LinkedIn profile data for URL: ${linkedInUrl}`);
    
    // Make a request to the Proxycurl API
    const apiUrl = new URL('https://nubela.co/proxycurl/api/v2/linkedin');
    apiUrl.searchParams.append('url', linkedInUrl);
    
    const response = await fetch(apiUrl.toString(), {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      console.error(`Error fetching LinkedIn profile data with Proxycurl: ${response.status} ${response.statusText}`);
      
      // Check if it's a rate limit or authorization issue
      if (response.status === 403) {
        console.log('Proxycurl API key may be invalid or expired. Will try alternative methods.');
      } else if (response.status === 429) {
        console.log('Proxycurl API rate limit exceeded. Will try alternative methods.');
      }
      
      // Return null to try other methods
      return null;
    }
    
    const data = await response.json();
    
    // Transform the Proxycurl response to our LinkedInProfile format
    return {
      firstName: data.first_name || '',
      lastName: data.last_name || '',
      headline: data.headline || '',
      summary: data.summary || '',
      industryName: data.industry || '',
      locationName: data.location_name || '',
      positions: (data.experiences || []).map(exp => ({
        title: exp.title || '',
        company: exp.company || '',
        location: exp.location || '',
        startDate: exp.starts_at ? new Date(exp.starts_at.year, exp.starts_at.month - 1) : new Date(),
        endDate: exp.ends_at ? new Date(exp.ends_at.year, exp.ends_at.month - 1) : null,
        description: exp.description || '',
        skills: []
      })),
      educations: (data.education || []).map(edu => ({
        school: edu.school || '',
        degree: edu.degree || '',
        field: edu.field_of_study || '',
        startDate: edu.starts_at ? new Date(edu.starts_at.year, edu.starts_at.month - 1) : new Date(),
        endDate: edu.ends_at ? new Date(edu.ends_at.year, edu.ends_at.month - 1) : null,
        gpa: null
      })),
      skills: (data.skills || []).map(skill => skill.name),
      certifications: (data.certifications || []).map(cert => ({
        name: cert.name || '',
        issuer: cert.authority || '',
        date: cert.starts_at ? new Date(cert.starts_at.year, cert.starts_at.month - 1) : null,
        url: ''
      }))
    };
  } catch (error) {
    console.error('Error fetching LinkedIn profile data with Proxycurl:', error);
    return null;
  }
}

/**
 * Fetch LinkedIn profile HTML directly
 * This is a fallback method when API methods fail
 * @param linkedInUrl The LinkedIn profile URL
 * @returns The HTML content of the LinkedIn profile page
 */
export async function fetchLinkedInProfileHTML(linkedInUrl) {
  if (!linkedInUrl) {
    return null;
  }
  
  try {
    console.log(`Would fetch LinkedIn profile HTML from: ${linkedInUrl}`);
    
    // Note: Direct scraping of LinkedIn is against their terms of service
    // This is just a placeholder for a proper implementation that would use
    // a headless browser or a service that respects LinkedIn's terms
    
    // For now, we'll return null to indicate this method isn't implemented
    // In a production environment, you would implement this with proper authentication
    // and respect for LinkedIn's robots.txt and terms of service
    return null;
    
    // Example implementation (commented out):
    /*
    const response = await fetch(linkedInUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch LinkedIn profile HTML: ${response.statusText}`);
    }
    
    return await response.text();
    */
  } catch (error) {
    console.error('Error fetching LinkedIn profile HTML:', error);
    return null;
  }
}

/**
 * Generate mock LinkedIn profile data based on the URL
 * @param linkedInUrl The LinkedIn profile URL
 * @returns Mock LinkedIn profile data
 */
export function generateMockLinkedInData(linkedInUrl) {
  // Extract something from the URL to seed different mock profiles
  let seed = 'default';
  try {
    const parsedUrl = new URL(linkedInUrl);
    const pathParts = parsedUrl.pathname.split('/').filter(Boolean);
    if (pathParts.length > 0) {
      // Handle /in/username format
      if (pathParts[0] === 'in' && pathParts.length > 1) {
        seed = pathParts[1];
      } else {
        seed = pathParts[0];
      }
    }
  } catch (error) {
    console.error('Error parsing LinkedIn URL for mock data:', error);
  }
  
  const firstLetter = seed.charAt(0).toLowerCase();
  
  // Generate different mock data based on the first letter of the username
  if (firstLetter >= 'a' && firstLetter <= 'm') {
    // Tech profile
    return {
      firstName: "Alex",
      lastName: "Tech",
      headline: "Senior Software Engineer",
      summary: "Experienced software engineer with a passion for building scalable applications and solving complex problems.",
      industryName: "Computer Software",
      locationName: "San Francisco Bay Area",
      positions: [
        {
          title: "Senior Software Engineer",
          companyName: "Tech Innovations Inc.",
          location: "San Francisco, CA",
          startDate: { year: 2020, month: 1 },
          description: "Developed and maintained scalable web applications using React, Node.js, and AWS. Led a team of 5 engineers."
        },
        {
          title: "Software Engineer",
          companyName: "Startup Solutions",
          location: "San Francisco, CA",
          startDate: { year: 2018, month: 3 },
          endDate: { year: 2019, month: 12 },
          description: "Built RESTful APIs and implemented frontend features using React and TypeScript."
        }
      ],
      educations: [
        {
          schoolName: "University of California, Berkeley",
          degreeName: "Bachelor of Science",
          fieldOfStudy: "Computer Science",
          startDate: { year: 2014, month: 9 },
          endDate: { year: 2018, month: 5 },
          activities: "Computer Science Club, Hackathons"
        }
      ],
      skills: ["JavaScript", "React", "Node.js", "TypeScript", "GraphQL", "AWS", "Docker", "Kubernetes"],
      certifications: [
        {
          name: "AWS Certified Solutions Architect",
          authority: "Amazon Web Services",
          licenseNumber: "AWS-SA-12345",
          startDate: { year: 2021, month: 6 }
        },
        {
          name: "Professional Scrum Master I",
          authority: "Scrum.org",
          licenseNumber: "PSM-I-12345",
          startDate: { year: 2020, month: 3 }
        }
      ]
    };
  } else {
    // Non-tech profile
    return {
      firstName: "Sam",
      lastName: "Business",
      headline: "Business Development Manager",
      summary: "Experienced business development professional with a track record of driving growth and building strong client relationships.",
      industryName: "Business Development",
      locationName: "New York City",
      positions: [
        {
          title: "Business Development Manager",
          companyName: "Global Solutions Corp",
          location: "New York, NY",
          startDate: { year: 2019, month: 4 },
          description: "Led business development initiatives and managed key client relationships. Increased revenue by 40% in two years."
        },
        {
          title: "Sales Representative",
          companyName: "Enterprise Sales Inc",
          location: "New York, NY",
          startDate: { year: 2017, month: 6 },
          endDate: { year: 2019, month: 3 },
          description: "Developed and maintained client relationships, consistently exceeding sales targets."
        }
      ],
      educations: [
        {
          schoolName: "New York University",
          degreeName: "Bachelor of Business Administration",
          fieldOfStudy: "Business Management",
          startDate: { year: 2013, month: 9 },
          endDate: { year: 2017, month: 5 },
          activities: "Business Club, Debate Team"
        }
      ],
      skills: ["Business Development", "Sales", "Client Relations", "Strategic Planning", "Market Analysis", "Team Leadership"],
      certifications: [
        {
          name: "Certified Business Development Professional",
          authority: "Business Development Institute",
          licenseNumber: "CBDP-12345",
          startDate: { year: 2020, month: 8 }
        }
      ]
    };
  }
} 