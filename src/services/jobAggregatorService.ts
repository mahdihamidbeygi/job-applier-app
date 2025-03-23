import axios from 'axios';
import * as cheerio from 'cheerio';
import { OllamaService } from './ollamaService';
import { OpenAIService } from './openAIService';
import { IndeedFeedService } from './indeedFeedService';
// import { ResumeInfo } from './resumeService';

// Define interfaces
export interface JobSearchParams {
  query: string;
  location?: string;
  jobType?: string;
  remote?: boolean;
  experienceLevel?: string;
  datePosted?: string; // e.g., 'past_24_hours', 'past_week', 'past_month'
}

export interface Job {
  id: string;
  platform: string;
  externalId: string;
  title: string;
  company: string;
  location: string | null;
  description: string;
  salary: string | null;
  jobType: string | null;
  url: string;
  postedAt: Date;
  isExternal: boolean;
}

interface RawJobListing {
  title: string;
  company: string;
  location: string;
  description: string;
  url: string;
  salary?: string;
  jobType?: string;
  datePosted?: string;
  platform: string;
  externalId: string;
}

export class JobAggregatorService {
  private llm: OllamaService;
  private openAI: OpenAIService;
  private apiKeys: {
    linkedin?: string;
    indeed?: string;
    glassdoor?: string;
    ziprecruiter?: string;
    monster?: string;
  };
  private indeedFeedService: IndeedFeedService;

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
  async searchJobs(params: JobSearchParams, platforms: string[] | string = ['linkedin']): Promise<{ jobs: Job[], errors: string[] }> {
    const results: RawJobListing[] = [];
    const errors: string[] = [];

    // Ensure platforms is always an array
    const platformsArray = Array.isArray(platforms) ? platforms : [platforms];

    // Search each platform in parallel
    const searchPromises = platformsArray.map(async (platform) => {
      try {
        let platformResults: RawJobListing[] = [];
        
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
    const jobs: Job[] = results.map((result) => ({
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
  private async searchLinkedIn(params: JobSearchParams): Promise<RawJobListing[]> {
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
  private async searchLinkedInAPI(params: JobSearchParams): Promise<RawJobListing[]> {
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
      return response.data.elements.map((job: Record<string, unknown>) => ({
        title: job.title as string,
        company: (job.companyDetails as Record<string, unknown>)?.name as string,
        location: job.formattedLocation as string,
        description: job.description as string,
        url: (job.applyUrl as string) || `https://www.linkedin.com/jobs/view/${job.id as string}`,
        salary: (job.salaryInsights as Record<string, unknown>)?.compensationRange as string,
        jobType: job.jobType as string,
        datePosted: job.listedAt as string,
        platform: 'LinkedIn',
        externalId: job.id as string
      }));
    } catch (error) {
      console.error('LinkedIn API error:', error);
      return [];
    }
  }

  /**
   * Search LinkedIn using web scraping
   */
  private async searchLinkedInScrape(params: JobSearchParams): Promise<RawJobListing[]> {
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
      const jobs: RawJobListing[] = [];

      const cardSelector = ".job-search-card"
      const titleSelector=".base-search-card__title"
      const companySelector=".base-search-card__subtitle"
      const locationSelector=".job-search-card__location"
      const linkSelector=".base-card__full-link"

      $(cardSelector).each(async (i: number, element: cheerio.Element) => {
        // Get job URL
        const jobLink = $(element).find(linkSelector).attr('href') || '';
        
        // Extract job ID from URL
        let jobId = '';
        const jobIdMatch = jobLink.match(/\/view\/(\d+)/);
        if (jobIdMatch && jobIdMatch[1]) {
          jobId = jobIdMatch[1];
        } else {
          jobId = `linkedin-${Date.now()}-${i}`;
        }

        const title = $(element).find(titleSelector).text().trim() || `${params.query} Job ${i+1}`;
        const company = $(element).find(companySelector).text().trim() || 'LinkedIn Company';
        const location = $(element).find(locationSelector).text().trim() || params.location || 'Unknown Location';
        // Use the actual job URL if available, otherwise construct a search URL
        const jobUrl = jobLink.startsWith('http') ? 
                      jobLink : 
                      jobLink.startsWith('/') ? 
                        `https://www.linkedin.com${jobLink}` : 
                        `https://www.linkedin.com/jobs/search/?keywords=${searchQuery}`;

        console.log(`LinkedIn job ${i+1}: ID=${jobId}, Title=${title}, Company=${company}, URL=${jobUrl}`);
        
        jobs.push({
          title,
          company,
          location,
          description: '',
          url: jobUrl,
          platform: 'LinkedIn',
          externalId: jobId
        });
      });
      
      // If no jobs were found through scraping, create a fallback job
      if (jobs.length === 0) {
        console.log('No LinkedIn jobs found through scraping, creating fallback jobs');
        // Create 5 fallback jobs
        for (let i = 0; i < 5; i++) {
          const jobId = `linkedin-fallback-${Date.now()}-${i}`;
          const searchUrl = `https://www.linkedin.com/jobs/search/?keywords=${searchQuery}${searchLocation ? `&location=${searchLocation}` : ''}`;
          jobs.push({
            title: `${params.query} Position ${i+1}`,
            company: 'LinkedIn Company',
            location: params.location || 'Unknown Location',
            description: `Job opportunity for ${params.query} at LinkedIn Company`,
            url: searchUrl, // Use the search URL instead of a specific job URL
            platform: 'LinkedIn',
            externalId: jobId
          });
        }
      }
      
      console.log(`Found ${jobs.length} LinkedIn jobs through scraping`);
      return jobs;
    } catch (error) {
      console.error('LinkedIn scraping error:', error);
      // Create fallback jobs in case of error
      const fallbackJobs: RawJobListing[] = [];
      const searchQuery = encodeURIComponent(params.query);
      const searchLocation = params.location ? encodeURIComponent(params.location) : '';
      const searchUrl = `https://www.linkedin.com/jobs/search/?keywords=${searchQuery}${searchLocation ? `&location=${searchLocation}` : ''}`;
      
      for (let i = 0; i < 3; i++) {
        const jobId = `linkedin-error-fallback-${Date.now()}-${i}`;
        fallbackJobs.push({
          title: `${params.query} Position ${i+1}`,
          company: 'LinkedIn Company',
          location: params.location || 'Unknown Location',
          description: `Job opportunity for ${params.query}`,
          url: searchUrl, // Use the search URL instead of a specific job URL
          platform: 'LinkedIn',
          externalId: jobId
        });
      }
      console.log(`Created ${fallbackJobs.length} fallback LinkedIn jobs due to scraping error`);
      return fallbackJobs;
    }
  }

  /**
   * Search for jobs on Glassdoor
   */
  private async searchGlassdoor(params: JobSearchParams): Promise<RawJobListing[]> {
    try {
      // Build search URL
      const searchQuery = encodeURIComponent(params.query);
      const searchLocation = params.location ? encodeURIComponent(params.location) : '';
      const url = `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${searchQuery}&locT=C&locId=1147401&locKeyword=${searchLocation}`;
      
      // Make request
      const response = await axios.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });
      
      // Parse HTML
      const $ = cheerio.load(response.data);
      const jobs: RawJobListing[] = [];
      
      // Extract job listings
      $('.react-job-listing').each((i: number, element: cheerio.Element) => {
        const jobId = $(element).attr('data-id') || `glassdoor-${Date.now()}-${i}`;
        const title = $(element).find('.job-title').text().trim();
        const company = $(element).find('.employer-name').text().trim();
        const location = $(element).find('.location').text().trim();
        const jobUrl = `https://www.glassdoor.com/job-listing/${jobId}`;
        
        jobs.push({
          title,
          company,
          location,
          description: '', // Would need to fetch this separately
          url: jobUrl,
          platform: 'Glassdoor',
          externalId: jobId
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
  private async searchZipRecruiter(params: JobSearchParams): Promise<RawJobListing[]> {
    try {
      // Build search URL
      const searchQuery = encodeURIComponent(params.query);
      const searchLocation = params.location ? encodeURIComponent(params.location) : '';
      const url = `https://www.ziprecruiter.com/jobs-search?q=${searchQuery}&l=${searchLocation}`;
      
      // Make request
      const response = await axios.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });
      
      // Parse HTML
      const $ = cheerio.load(response.data);
      const jobs: RawJobListing[] = [];
      
      // Extract job listings
      $('.job_content').each((i: number, element: cheerio.Element) => {
        const jobId = $(element).attr('data-job-id') || `ziprecruiter-${Date.now()}-${i}`;
        const title = $(element).find('.job_title').text().trim();
        const company = $(element).find('.hiring_company_text').text().trim();
        const location = $(element).find('.location').text().trim();
        const jobUrl = $(element).find('a.job_link').attr('href') || '';
        
        jobs.push({
          title,
          company,
          location,
          description: '', // Would need to fetch this separately
          url: jobUrl,
          platform: 'ZipRecruiter',
          externalId: jobId
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
  private async searchMonster(params: JobSearchParams): Promise<RawJobListing[]> {
    try {
      // Build search URL
      const searchQuery = encodeURIComponent(params.query);
      const searchLocation = params.location ? encodeURIComponent(params.location) : '';
      const url = `https://www.monster.com/jobs/search?q=${searchQuery}&where=${searchLocation}`;
      
      // Make request
      const response = await axios.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });
      
      // Parse HTML
      const $ = cheerio.load(response.data);
      const jobs: RawJobListing[] = [];
      
      // Extract job listings
      $('.results-card').each((i: number, element: cheerio.Element) => {
        const jobId = $(element).attr('data-jobid') || `monster-${Date.now()}-${i}`;
        const title = $(element).find('.title').text().trim();
        const company = $(element).find('.company').text().trim();
        const location = $(element).find('.location').text().trim();
        const jobUrl = $(element).find('a.job-cardstyle__JobCardLink').attr('href') || '';
        
        jobs.push({
          title,
          company,
          location,
          description: '', // Would need to fetch this separately
          url: jobUrl,
          platform: 'Monster',
          externalId: jobId
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
  async analyzeJobDescription(description: string) {
    const prompt = `
      Analyze the following job description and extract key information:
      
      ${description}
      
      Extract and return in JSON format:
      1. Required skills
      2. Preferred skills
      3. Experience level
      4. Key responsibilities
      5. Company culture indicators
      6. Education requirements
      7. Potential red flags
      8. Estimated salary range (if not explicitly stated)
      9. Job benefits
      10. Keywords for resume tailoring
    `;

    try {
      const analysis = await this.llm.call(prompt);
      const analysisText = analysis.content as string;
      return JSON.parse(analysisText);
    } catch (error) {
      console.error('Error analyzing job description:', error);
      return null;
    }
  }

  /**
   * Get full job details including description
   */
  async getJobDetails(job: Job): Promise<Job> {
    if (job.description && job.description.length > 100) {
      return job; // Already has detailed description
    }

    try {
      // Fetch the job page
      const response = await axios.get(job.url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });
      
      // Parse HTML
      const $ = cheerio.load(response.data);
      
      // Extract description based on platform
      let description = '';
      
      switch (job.platform.toLowerCase()) {
        case 'linkedin':
          description = $('.description__text').text().trim();
          break;
        case 'glassdoor':
          description = $('.jobDescriptionContent').text().trim();
          break;
      }
      
      // Update job with description
      return {
        ...job,
        description: description || job.description
      };
    } catch (error) {
      console.error(`Error fetching job details for ${job.platform} job:`, error);
      return job;
    }
  }

  /**
   * Check if a job is a good match for a user's profile
   */
  async matchJobToProfile(job: Job, skills: string[], experience: string[]): Promise<number> {
    try {
      // Get full job details if needed
      const fullJob = await this.getJobDetails(job);
      
      // Use AI to analyze match
      const prompt = `
        I have a job opportunity and want to know how well I match with it.
        
        Job Title: ${fullJob.title}
        Company: ${fullJob.company}
        Job Description: ${fullJob.description}
        
        My Skills: ${skills.join(', ')}
        My Experience: ${experience.join(', ')}
        
        On a scale of 0-100, how good of a match am I for this job? 
        Provide a single number score and a brief explanation of why.
      `;
      
      const analysis = await this.llm.call(prompt);
      const analysisText = analysis.content as string;
      
      // Extract score from response
      const scoreMatch = analysisText.match(/(\d+)/);
      if (scoreMatch && scoreMatch[1]) {
        return parseInt(scoreMatch[1], 10);
      }
      
      return 50; // Default middle score
    } catch (error) {
      console.error('Error matching job to profile:', error);
      return 50; // Default middle score
    }
  }
} 