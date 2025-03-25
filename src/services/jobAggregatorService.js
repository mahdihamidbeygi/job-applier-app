import axios from 'axios';
import * as cheerio from 'cheerio';
import { OllamaService } from './ollamaService';
import { OpenAIService } from './openAIService';
import { IndeedFeedService } from './indeedFeedService';

export class JobAggregatorService {
  constructor() {
    // Initialize Ollama for general analysis
    this.llm = new OllamaService();
    
    // Initialize OpenAI for specific tasks like selectors
    this.openAI = new OpenAIService();

    // Initialize API keys
    this.apiKeys = {
      linkedin: process.env.LINKEDIN_API_KEY,
      indeed: process.env.INDEED_API_KEY,
      glassdoor: process.env.GLASSDOOR_API_KEY,
      ziprecruiter: process.env.ZIPRECRUITER_API_KEY,
      monster: process.env.MONSTER_API_KEY,
    };
    
    this.indeedFeedService = new IndeedFeedService();
  }

  /**
   * Search for jobs across multiple platforms
   */
  async searchJobs(params, platforms = ['linkedin']) {
    const results = [];
    const errors = [];

    // Ensure platforms is always an array
    const platformsArray = Array.isArray(platforms) ? platforms : [platforms];

    // Search each platform in parallel
    const searchPromises = platformsArray.map(async (platform) => {
      try {
        let platformResults = [];
        
        switch (platform.toLowerCase()) {
          case 'linkedin':
            platformResults = await this.searchLinkedIn(params);
            break;
          case 'glassdoor':
            platformResults = await this.searchGlassdoor(params);
            break;
          case 'ziprecruiter':
            platformResults = await this.searchZipRecruiter(params);
            break;
          case 'monster':
            platformResults = await this.searchMonster(params);
            break;
        }
        
        console.log(`Found ${platformResults.length} results from ${platform}`);
        return platformResults;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        errors.push(`Error searching ${platform}: ${errorMessage}`);
        console.error(`Error searching ${platform}:`, error);
        return [];
      }
    });

    // Wait for all searches to complete
    const searchResults = await Promise.all(searchPromises);
    
    // Flatten results
    searchResults.forEach(platformResults => {
      results.push(...platformResults);
    });

    // Log any errors that occurred
    if (errors.length > 0) {
      console.error(`Encountered ${errors.length} errors during job search:`, errors);
    }

    // Process results
    const jobs = results.map((result) => ({
      id: `${result.platform.toLowerCase()}-${result.externalId}`,
      platform: result.platform,
      externalId: result.externalId,
      title: result.title,
      company: result.company,
      location: result.location,
      description: result.description,
      salary: result.salary || null,
      jobType: result.jobType || null,
      url: result.url,
      postedAt: result.datePosted ? new Date(result.datePosted) : new Date(),
      isExternal: true,
    }));

    return { jobs, errors };
  }

  /**
   * Search for jobs on LinkedIn
   */
  async searchLinkedIn(params) {
    try {
      if (this.apiKeys.linkedin) {
        // Use LinkedIn API if key is available
        return await this.searchLinkedInAPI(params);
      } else {
        // Fall back to web scraping
        return await this.searchLinkedInScrape(params);
      }
    } catch (error) {
      console.error('LinkedIn search error:', error);
      return [];
    }
  }

  /**
   * Search LinkedIn using their API
   */
  async searchLinkedInAPI(params) {
    try {
      // LinkedIn API endpoint
      const url = 'https://api.linkedin.com/v2/jobSearch';
      
      // Build query parameters
      const queryParams = {
        keywords: params.query,
        location: params.location,
        jobType: params.jobType,
        remote: params.remote,
        start: 0,
        count: 25
      };
      
      // Make API request
      const response = await axios.get(url, {
        params: queryParams,
        headers: {
          'Authorization': `Bearer ${this.apiKeys.linkedin}`,
          'Content-Type': 'application/json'
        }
      });
      // Process and return results
      return response.data.elements.map((job) => ({
        title: job.title,
        company: job.companyDetails?.name,
        location: job.formattedLocation,
        description: job.description,
        url: job.applyUrl || `https://www.linkedin.com/jobs/view/${job.id}`,
        salary: job.salaryInsights?.compensationRange,
        jobType: job.jobType,
        datePosted: job.listedAt,
        platform: 'LinkedIn',
        externalId: job.id
      }));
    } catch (error) {
      console.error('LinkedIn API error:', error);
      return [];
    }
  }

  /**
   * Search LinkedIn using web scraping
   */
  async searchLinkedInScrape(params) {
    try {
      // Build search URL
      const searchQuery = encodeURIComponent(params.query);
      const searchLocation = params.location ? encodeURIComponent(params.location) : '';
      const url = `https://www.linkedin.com/jobs/search/?keywords=${searchQuery}&location=${searchLocation}`;
      
      console.log(`Searching LinkedIn jobs with URL: ${url}`);
      
      // Make request
      const response = await axios.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });
      
      // Parse HTML
      const $ = cheerio.load(response.data);
      const jobs = [];

      const cardSelector = ".job-search-card"
      const titleSelector=".base-search-card__title"
      const companySelector=".base-search-card__subtitle"
      const locationSelector=".job-search-card__location"
      const linkSelector=".base-card__full-link"

      $(cardSelector).each(async (i, element) => {
        // Get job URL
        const jobLink = $(element).find(linkSelector).attr('href') || '';
        
        // Extract job ID from URL
        let jobId = '';
        const jobIdMatch = jobLink.match(/\/view\/(\d+)/);
        if (jobIdMatch && jobIdMatch[1]) {
          jobId = jobIdMatch[1];
        } else {
          // If no ID found, generate a unique one
          jobId = `linkedin-${Date.now()}-${i}`;
        }

        // Get job details
        const title = $(element).find(titleSelector).text().trim();
        const company = $(element).find(companySelector).text().trim();
        const location = $(element).find(locationSelector).text().trim();

        // Add job to results
        jobs.push({
          title,
          company,
          location,
          description: '', // Will be filled in when fetching job details
          url: jobLink,
          platform: 'LinkedIn',
          externalId: jobId,
          datePosted: new Date().toISOString()
        });
      });

      return jobs;
    } catch (error) {
      console.error('LinkedIn scraping error:', error);
      return [];
    }
  }

  /**
   * Search for jobs on Glassdoor
   */
  async searchGlassdoor(params) {
    try {
      if (this.apiKeys.glassdoor) {
        // Use Glassdoor API if key is available
        return await this.searchGlassdoorAPI(params);
      } else {
        // Fall back to web scraping
        return await this.searchGlassdoorScrape(params);
      }
    } catch (error) {
      console.error('Glassdoor search error:', error);
      return [];
    }
  }

  /**
   * Search Glassdoor using their API
   */
  async searchGlassdoorAPI(params) {
    try {
      // Glassdoor API endpoint
      const url = 'https://api.glassdoor.com/api/api.htm';
      
      // Build query parameters
      const queryParams = {
        'v': '1',
        'format': 'json',
        't.p': this.apiKeys.glassdoor,
        't.k': process.env.GLASSDOOR_PARTNER_ID,
        'action': 'jobs-prog',
        'q': params.query,
        'l': params.location,
        'userip': '0.0.0.0',
        'useragent': 'Mozilla/5.0'
      };
      
      // Make API request
      const response = await axios.get(url, { params: queryParams });
      
      // Process and return results
      return response.data.response.jobs.map((job) => ({
        title: job.jobTitle,
        company: job.employerName,
        location: job.location,
        description: job.jobDescription,
        url: job.jobViewUrl,
        salary: job.salary,
        jobType: job.jobType,
        datePosted: job.datePosted,
        platform: 'Glassdoor',
        externalId: job.jobId
      }));
    } catch (error) {
      console.error('Glassdoor API error:', error);
      return [];
    }
  }

  /**
   * Search Glassdoor using web scraping
   */
  async searchGlassdoorScrape(params) {
    try {
      // Build search URL
      const searchQuery = encodeURIComponent(params.query);
      const searchLocation = params.location ? encodeURIComponent(params.location) : '';
      const url = `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${searchQuery}&locT=C&locId=${searchLocation}`;
      
      // Make request
      const response = await axios.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });
      
      // Parse HTML
      const $ = cheerio.load(response.data);
      const jobs = [];

      // Extract job listings
      $('.jobListing').each((i, element) => {
        const title = $(element).find('.jobTitle').text().trim();
        const company = $(element).find('.employerName').text().trim();
        const location = $(element).find('.location').text().trim();
        const jobLink = $(element).find('.jobLink').attr('href') || '';
        const jobId = jobLink.match(/jobListingId=(\d+)/)?.[1] || `glassdoor-${Date.now()}-${i}`;

        jobs.push({
          title,
          company,
          location,
          description: '', // Will be filled in when fetching job details
          url: jobLink.startsWith('http') ? jobLink : `https://www.glassdoor.com${jobLink}`,
          platform: 'Glassdoor',
          externalId: jobId,
          datePosted: new Date().toISOString()
        });
      });

      return jobs;
    } catch (error) {
      console.error('Glassdoor scraping error:', error);
      return [];
    }
  }

  /**
   * Search for jobs on ZipRecruiter
   */
  async searchZipRecruiter(params) {
    try {
      if (this.apiKeys.ziprecruiter) {
        // Use ZipRecruiter API if key is available
        return await this.searchZipRecruiterAPI(params);
      } else {
        // Fall back to web scraping
        return await this.searchZipRecruiterScrape(params);
      }
    } catch (error) {
      console.error('ZipRecruiter search error:', error);
      return [];
    }
  }

  /**
   * Search ZipRecruiter using their API
   */
  async searchZipRecruiterAPI(params) {
    try {
      // ZipRecruiter API endpoint
      const url = 'https://api.ziprecruiter.com/jobs/v1';
      
      // Build query parameters
      const queryParams = {
        search: params.query,
        location: params.location,
        job_type: params.jobType,
        api_key: this.apiKeys.ziprecruiter,
        page: 1,
        jobs_per_page: 25
      };
      
      // Make API request
      const response = await axios.get(url, { params: queryParams });
      
      // Process and return results
      return response.data.jobs.map((job) => ({
        title: job.name,
        company: job.hiring_company.name,
        location: job.location,
        description: job.snippet,
        url: job.url,
        salary: job.salary_min ? `${job.salary_min} - ${job.salary_max}` : null,
        jobType: job.job_type,
        datePosted: job.date_posted,
        platform: 'ZipRecruiter',
        externalId: job.id
      }));
    } catch (error) {
      console.error('ZipRecruiter API error:', error);
      return [];
    }
  }

  /**
   * Search ZipRecruiter using web scraping
   */
  async searchZipRecruiterScrape(params) {
    try {
      // Build search URL
      const searchQuery = encodeURIComponent(params.query);
      const searchLocation = params.location ? encodeURIComponent(params.location) : '';
      const url = `https://www.ziprecruiter.com/candidate/search?search=${searchQuery}&location=${searchLocation}`;
      
      // Make request
      const response = await axios.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });
      
      // Parse HTML
      const $ = cheerio.load(response.data);
      const jobs = [];

      // Extract job listings
      $('.job_content').each((i, element) => {
        const title = $(element).find('.job_title').text().trim();
        const company = $(element).find('.hiring_company').text().trim();
        const location = $(element).find('.location').text().trim();
        const jobLink = $(element).find('.job_link').attr('href') || '';
        const jobId = jobLink.match(/job-(\d+)/)?.[1] || `ziprecruiter-${Date.now()}-${i}`;

        jobs.push({
          title,
          company,
          location,
          description: '', // Will be filled in when fetching job details
          url: jobLink.startsWith('http') ? jobLink : `https://www.ziprecruiter.com${jobLink}`,
          platform: 'ZipRecruiter',
          externalId: jobId,
          datePosted: new Date().toISOString()
        });
      });

      return jobs;
    } catch (error) {
      console.error('ZipRecruiter scraping error:', error);
      return [];
    }
  }

  /**
   * Search for jobs on Monster
   */
  async searchMonster(params) {
    try {
      if (this.apiKeys.monster) {
        // Use Monster API if key is available
        return await this.searchMonsterAPI(params);
      } else {
        // Fall back to web scraping
        return await this.searchMonsterScrape(params);
      }
    } catch (error) {
      console.error('Monster search error:', error);
      return [];
    }
  }

  /**
   * Search Monster using their API
   */
  async searchMonsterAPI(params) {
    try {
      // Monster API endpoint
      const url = 'https://api.monster.com/v2/jobs/search';
      
      // Build query parameters
      const queryParams = {
        q: params.query,
        where: params.location,
        job_type: params.jobType,
        api_key: this.apiKeys.monster,
        page: 1,
        per_page: 25
      };
      
      // Make API request
      const response = await axios.get(url, { params: queryParams });
      
      // Process and return results
      return response.data.jobs.map((job) => ({
        title: job.title,
        company: job.company.name,
        location: job.location,
        description: job.description,
        url: job.url,
        salary: job.salary,
        jobType: job.job_type,
        datePosted: job.date_posted,
        platform: 'Monster',
        externalId: job.id
      }));
    } catch (error) {
      console.error('Monster API error:', error);
      return [];
    }
  }

  /**
   * Search Monster using web scraping
   */
  async searchMonsterScrape(params) {
    try {
      // Build search URL
      const searchQuery = encodeURIComponent(params.query);
      const searchLocation = params.location ? encodeURIComponent(params.location) : '';
      const url = `https://www.monster.com/jobs/search/?q=${searchQuery}&where=${searchLocation}`;
      
      // Make request
      const response = await axios.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });
      
      // Parse HTML
      const $ = cheerio.load(response.data);
      const jobs = [];

      // Extract job listings
      $('.job-search-card').each((i, element) => {
        const title = $(element).find('.title').text().trim();
        const company = $(element).find('.company').text().trim();
        const location = $(element).find('.location').text().trim();
        const jobLink = $(element).find('.job-card-link').attr('href') || '';
        const jobId = jobLink.match(/job-(\d+)/)?.[1] || `monster-${Date.now()}-${i}`;

        jobs.push({
          title,
          company,
          location,
          description: '', // Will be filled in when fetching job details
          url: jobLink.startsWith('http') ? jobLink : `https://www.monster.com${jobLink}`,
          platform: 'Monster',
          externalId: jobId,
          datePosted: new Date().toISOString()
        });
      });

      return jobs;
    } catch (error) {
      console.error('Monster scraping error:', error);
      return [];
    }
  }

  /**
   * Analyze a job description using AI
   */
  async analyzeJobDescription(description) {
    const messages = [
      new SystemMessage(
        "You are a job description analyzer. Extract key information and requirements from job descriptions. You must ALWAYS respond with valid JSON."
      ),
      new HumanMessage(
        `Analyze the following job description and extract key information. You MUST respond with a valid JSON object only, no other text.

        Job Description: ${description}
        
        The JSON object must have these exact fields:
        {
          "title": string, // The job title
          "company": string, // The company name
          "location": string, // The job location
          "requirements": string[], // Array of required skills and qualifications
          "responsibilities": string[], // Array of job responsibilities
          "benefits": string[], // Array of job benefits
          "experienceLevel": string, // Required experience level
          "education": string, // Required education level
          "salary": string, // Salary information if available
          "jobType": string, // Type of job (full-time, part-time, etc.)
          "remote": boolean, // Whether the job is remote
          "keywords": string[] // Array of relevant keywords
        }
        
        Remember: Respond with ONLY the JSON object, no other text or explanation.`
      )
    ];

    try {
      const response = await this.llm.invoke(messages);
      const content = response.content.toString().trim();
      
      // Try to find JSON in the response if it's wrapped in other text
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      const jsonStr = jsonMatch ? jsonMatch[0] : content;
      
      const parsed = JSON.parse(jsonStr);
      
      // Validate the structure
      if (!parsed.title || !parsed.company || !parsed.location || 
          !parsed.requirements || !parsed.responsibilities || !parsed.benefits ||
          !parsed.experienceLevel || !parsed.education || !parsed.jobType ||
          typeof parsed.remote !== 'boolean' || !parsed.keywords) {
        throw new Error('Invalid response structure');
      }
      
      return parsed;
    } catch (error) {
      console.error('Error analyzing job description:', error);
      throw new Error('Failed to analyze job description');
    }
  }

  /**
   * Get detailed information for a specific job
   */
  async getJobDetails(job) {
    try {
      // Make request to job URL
      const response = await axios.get(job.url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });
      
      // Parse HTML
      const $ = cheerio.load(response.data);
      
      // Extract job details based on platform
      switch (job.platform.toLowerCase()) {
        case 'linkedin':
          return this.extractLinkedInJobDetails($, job);
        case 'glassdoor':
          return this.extractGlassdoorJobDetails($, job);
        case 'ziprecruiter':
          return this.extractZipRecruiterJobDetails($, job);
        case 'monster':
          return this.extractMonsterJobDetails($, job);
        default:
          return job;
      }
    } catch (error) {
      console.error(`Error getting job details for ${job.platform} job ${job.id}:`, error);
      return job;
    }
  }

  /**
   * Extract job details from LinkedIn job page
   */
  extractLinkedInJobDetails($, job) {
    const description = $('.job-description').text().trim();
    const salary = $('.salary-insights').text().trim() || null;
    const jobType = $('.job-type').text().trim() || null;
    
    return {
      ...job,
      description,
      salary,
      jobType
    };
  }

  /**
   * Extract job details from Glassdoor job page
   */
  extractGlassdoorJobDetails($, job) {
    const description = $('.jobDescriptionContent').text().trim();
    const salary = $('.salary').text().trim() || null;
    const jobType = $('.jobType').text().trim() || null;
    
    return {
      ...job,
      description,
      salary,
      jobType
    };
  }

  /**
   * Extract job details from ZipRecruiter job page
   */
  extractZipRecruiterJobDetails($, job) {
    const description = $('.job_description').text().trim();
    const salary = $('.salary').text().trim() || null;
    const jobType = $('.job_type').text().trim() || null;
    
    return {
      ...job,
      description,
      salary,
      jobType
    };
  }

  /**
   * Extract job details from Monster job page
   */
  extractMonsterJobDetails($, job) {
    const description = $('.job-description').text().trim();
    const salary = $('.salary').text().trim() || null;
    const jobType = $('.job-type').text().trim() || null;
    
    return {
      ...job,
      description,
      salary,
      jobType
    };
  }

  /**
   * Match a job to a candidate's profile
   */
  async matchJobToProfile(job, skills, experience) {
    const messages = [
      new SystemMessage(
        "You are a job matching expert. Analyze how well a job matches a candidate's profile. You must ALWAYS respond with valid JSON."
      ),
      new HumanMessage(
        `Analyze how well the following job matches the candidate's profile. You MUST respond with a valid JSON object only, no other text.

        Job:
        Title: ${job.title}
        Company: ${job.company}
        Description: ${job.description}
        Requirements: ${job.requirements?.join(', ') || ''}

        Candidate Profile:
        Skills: ${skills.join(', ')}
        Experience: ${experience.join(', ')}

        The JSON object must have these exact fields:
        {
          "matchScore": number, // Number between 0-100 indicating overall match
          "matchingSkills": string[], // Array of skills that match
          "missingSkills": string[], // Array of required skills that candidate lacks
          "recommendations": string[], // Array of suggestions to improve match
          "explanation": string // Brief explanation of the match score
        }
        
        Remember: Respond with ONLY the JSON object, no other text or explanation.`
      )
    ];

    try {
      const response = await this.llm.invoke(messages);
      const content = response.content.toString().trim();
      
      // Try to find JSON in the response if it's wrapped in other text
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      const jsonStr = jsonMatch ? jsonMatch[0] : content;
      
      const parsed = JSON.parse(jsonStr);
      
      // Validate the structure
      if (typeof parsed.matchScore !== 'number' || !parsed.matchingSkills || 
          !parsed.missingSkills || !parsed.recommendations || !parsed.explanation) {
        throw new Error('Invalid response structure');
      }
      
      return parsed;
    } catch (error) {
      console.error('Error matching job to profile:', error);
      throw new Error('Failed to match job to profile');
    }
  }
} 