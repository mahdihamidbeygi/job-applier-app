import { Job } from '@prisma/client';
import puppeteer from 'puppeteer';
import { load } from 'cheerio';

interface LinkedInJobSearchParams {
  query: string;
  location?: string;
  jobType?: string;
  start?: number;
  count?: number;
}

export class LinkedInService {
  private readonly baseUrl = 'https://www.linkedin.com/jobs/search';

  /**
   * Search for jobs using LinkedIn web scraping
   */
  async searchJobs(params: LinkedInJobSearchParams): Promise<Job[]> {
    try {
      console.log('Searching LinkedIn jobs with params:', params);

      const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
      });

      const page = await browser.newPage();
      
      // Set a realistic user agent
      await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

      // Construct the search URL
      const searchUrl = this.buildSearchUrl(params);
      await page.goto(searchUrl, { waitUntil: 'networkidle0' });

      // Wait for job cards to load
      await page.waitForSelector('.job-search-card');

      // Get the page content
      const content = await page.content();
      const $ = load(content);

      const jobs: Job[] = [];

      // Extract job information
      $('.job-search-card').each((_, element) => {
        const jobCard = $(element);
        const jobId = jobCard.attr('data-id') || '';
        const title = jobCard.find('.job-search-card__title').text().trim();
        const company = jobCard.find('.job-search-card__company-name').text().trim();
        const location = jobCard.find('.job-search-card__location').text().trim();
        const postedDate = jobCard.find('time').attr('datetime') || new Date().toISOString();
        const jobUrl = jobCard.find('.job-search-card__link').attr('href') || '';

        if (title && company) {
          jobs.push({
            id: `temp-${jobId}`,
            platform: 'linkedin',
            externalId: jobId,
            title,
            company,
            location,
            description: '', // Will be filled when viewing job details
            salary: null,
            jobType: null,
            url: this.normalizeJobUrl(jobUrl),
            postedAt: new Date(postedDate),
            isExternal: true,
            status: 'NEW',
            notes: null,
            resumeUrl: null,
            coverLetterUrl: null,
            userId: null,
          } as Job);
        }
      });

      await browser.close();
      return jobs;
    } catch (error) {
      console.error('Error searching LinkedIn jobs:', error);
      return [];
    }
  }

  /**
   * Get detailed job information
   */
  async getJobDetails(jobId: string): Promise<Partial<Job> | null> {
    try {
      const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
      });

      const page = await browser.newPage();
      await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

      const jobUrl = `https://www.linkedin.com/jobs/view/${jobId}`;
      await page.goto(jobUrl, { waitUntil: 'networkidle0' });

      // Wait for job details to load
      await page.waitForSelector('.job-details');

      const content = await page.content();
      const $ = load(content);

      const description = $('.job-details').text().trim();
      const jobType = $('.job-criteria-text:contains("Employment type")').next().text().trim();
      const salary = $('.compensation-text').text().trim();

      await browser.close();

      return {
        description,
        jobType: jobType || null,
        salary: salary || null,
      };
    } catch (error) {
      console.error('Error fetching LinkedIn job details:', error);
      return null;
    }
  }

  /**
   * Build the search URL with parameters
   */
  private buildSearchUrl(params: LinkedInJobSearchParams): string {
    const queryParams = new URLSearchParams();
    queryParams.append('keywords', params.query);
    if (params.location) queryParams.append('location', params.location);
    if (params.start) queryParams.append('start', params.start.toString());
    
    // Add job type filter if specified
    if (params.jobType) {
      const jobTypeMap: Record<string, string> = {
        'FULL_TIME': 'F',
        'PART_TIME': 'P',
        'CONTRACT': 'C',
        'TEMPORARY': 'T',
        'INTERNSHIP': 'I',
      };
      queryParams.append('f_JT', jobTypeMap[params.jobType] || 'F');
    }

    return `${this.baseUrl}?${queryParams.toString()}`;
  }

  /**
   * Normalize LinkedIn job URL
   */
  private normalizeJobUrl(url: string): string {
    if (!url) return '';
    if (url.startsWith('http')) return url;
    return `https://www.linkedin.com${url}`;
  }
} 