import puppeteer from 'puppeteer';
import { OllamaService } from './ollamaService';
import { JobAggregatorService } from './jobAggregatorService';

export class JobService {
  constructor() {
    this.llm = new OllamaService();
    this.jobAggregator = new JobAggregatorService();
  }

  /**
   * Search for jobs across multiple platforms
   * @param query Search query
   * @param location Optional location filter
   * @param jobType Optional job type filter
   * @param platforms Platforms to search (defaults to LinkedIn and Indeed)
   * @returns Jobs and any errors encountered
   */
  async searchJobs(query, location, jobType, platforms = ['linkedin']) {
    try {
      console.log(`Searching for jobs with query: "${query}", location: "${location || 'any'}", jobType: "${jobType || 'any'}", platforms:`, platforms);
      
      // Call the job aggregator service
      const result = await this.jobAggregator.searchJobs(
        {
          query,
          location,
          jobType,
          remote: false, // Default to false, can be made configurable
        },
        platforms
      );
      
      // Validate and fix job URLs if needed
      const validatedJobs = result.jobs.map(job => {
        // Log job details for debugging
        console.log(`Processing job: platform=${job.platform}, id=${job.id || job.externalId}, title=${job.title ? job.title.substring(0, 20) + '...' : 'missing'}, company=${job.company || 'missing'}`);
        
        // Ensure job has title and company for LinkedIn jobs
        if (job.platform.toLowerCase() === 'linkedin') {
          if (!job.title) {
            job.title = `LinkedIn Job ${job.externalId}`;
            console.log(`Added default title for LinkedIn job ${job.id || job.externalId}`);
          }
          if (!job.company) {
            job.company = 'LinkedIn Company';
            console.log(`Added default company for LinkedIn job ${job.id || job.externalId}`);
          }
        }
        
        // Ensure job URL is valid
        if (!job.url || !job.url.startsWith('http')) {
          console.log(`Job ${job.id || job.externalId} has invalid URL: "${job.url}". Attempting to fix.`);
          
          // Try to construct a URL based on the platform
          switch (job.platform.toLowerCase()) {
            case 'linkedin':
              // For LinkedIn, if we have a valid externalId that looks like a number, use the view URL
              if (job.externalId && /^\d+$/.test(job.externalId)) {
                job.url = `https://www.linkedin.com/jobs/view/${job.externalId}`;
                console.log(`Constructed LinkedIn job URL with ID: ${job.externalId}`);
              } else {
                // Otherwise, use a search URL
                const searchQuery = encodeURIComponent(job.title.split(' ').slice(0, 3).join(' '));
                job.url = `https://www.linkedin.com/jobs/search/?keywords=${searchQuery}`;
                console.log(`Using LinkedIn search URL for job: ${job.title}`);
              }
              break;
            case 'indeed':
              job.url = `https://www.indeed.com/viewjob?jk=${job.externalId}`;
              break;
            case 'glassdoor':
              job.url = `https://www.glassdoor.com/job-listing/${job.externalId}`;
              break;
            default:
              console.log(`Cannot construct URL for job ${job.id || job.externalId} from platform ${job.platform}`);
              break;
          }
          
          console.log(`Updated URL for job ${job.id || job.externalId}: ${job.url}`);
        }
        
        // Verify the URL is properly formatted
        if (job.url && !job.url.startsWith('http')) {
          job.url = `https://${job.url.replace(/^\/\//, '')}`;
          console.log(`Fixed URL format for job ${job.id || job.externalId}: ${job.url}`);
        }
        
        // Ensure job has a description
        if (!job.description || job.description.trim() === '') {
          job.description = `${job.title} at ${job.company}${job.location ? ` in ${job.location}` : ''}`;
        }
        
        return job;
      });
      
      // Log the number of jobs found
      console.log(`Found ${validatedJobs.length} jobs across ${Array.isArray(platforms) ? platforms.join(', ') : platforms}`);
      
      // Return the validated jobs
      return {
        jobs: validatedJobs,
        errors: result.errors
      };
    } catch (error) {
      console.error('Error searching for jobs:', error);
      return {
        jobs: [],
        errors: [error instanceof Error ? error.message : String(error)]
      };
    }
  }

  /**
   * Get detailed information for a specific job
   * @param jobId Job ID
   * @returns Detailed job information
   */
  async getJobDetails(jobId) {
    try {
      // This would typically fetch from the database or call an API
      console.log(`Getting details for job ID: ${jobId}`);
      // For now, we'll just return null
      return null;
    } catch (error) {
      console.error(`Error getting job details for ID ${jobId}:`, error);
      return null;
    }
  }

  async analyzeJobDescription(description) {
    return this.jobAggregator.analyzeJobDescription(description);
  }

  async applyToJob(job, resumePath, coverLetter) {
    if (!job.isExternal) {
      return this.applyEasyApply(job, resumePath, coverLetter);
    } else {
      return this.applyExternal(job, resumePath, coverLetter);
    }
  }

  async applyEasyApply(job, resumePath, coverLetter) {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    try {
      await page.goto(job.url);
      
      // Upload resume
      const resumeInput = await page.$('input[type="file"]');
      if (resumeInput) {
        await resumeInput.uploadFile(resumePath);
      }

      // Fill cover letter if provided
      if (coverLetter) {
        const coverLetterInput = await page.$('textarea[name="coverLetter"]');
        if (coverLetterInput) {
          await coverLetterInput.type(coverLetter);
        }
      }

      // Submit application
      const submitButton = await page.$('button[type="submit"]');
      if (submitButton) {
        await submitButton.click();
        await page.waitForNavigation();
      }

      return {
        success: true,
        message: 'Application submitted successfully',
        applicationId: `${job.platform}-${Date.now()}`,
      };
    } catch (error) {
      return {
        success: false,
        message: 'Failed to submit application',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    } finally {
      await browser.close();
    }
  }

  async applyExternal(job, resumePath, coverLetter) {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    try {
      await page.goto(job.url);
      
      // Upload resume
      const resumeInput = await page.$('input[type="file"]');
      if (resumeInput) {
        await resumeInput.uploadFile(resumePath);
      }

      // Fill cover letter if provided
      if (coverLetter) {
        const coverLetterInput = await page.$('textarea[name="coverLetter"]');
        if (coverLetterInput) {
          await coverLetterInput.type(coverLetter);
        }
      }

      // Submit application
      const submitButton = await page.$('button[type="submit"]');
      if (submitButton) {
        await submitButton.click();
        await page.waitForNavigation();
      }

      return {
        success: true,
        message: 'External application submitted successfully',
        applicationId: `${job.platform}-external-${Date.now()}`,
      };
    } catch (error) {
      return {
        success: false,
        message: 'Failed to submit external application',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    } finally {
      await browser.close();
    }
  }
} 