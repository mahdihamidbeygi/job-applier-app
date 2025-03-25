import puppeteer from 'puppeteer';
import { load } from 'cheerio';

export class IndeedService {
  constructor() {
    this.baseUrl = 'https://www.indeed.com';
    this.maxRetries = 3;
    this.retryDelay = 2000;
    this.pageTimeout = 60000; // 60 seconds
  }

  /**
   * Search for jobs using Indeed web scraping
   */
  async searchJobs(params) {
    let retryCount = 0;
    let browser;

    while (retryCount < this.maxRetries) {
      try {
        browser = await puppeteer.launch({
          headless: true,
          args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu',
            '--window-size=1920x1080'
          ]
        });

        const page = await browser.newPage();
        
        // Set a realistic viewport
        await page.setViewport({ width: 1920, height: 1080 });
        
        // Set a realistic user agent
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

        // Add request interception to block unnecessary resources
        await page.setRequestInterception(true);
        page.on('request', (request) => {
          const resourceType = request.resourceType();
          if (resourceType === 'image' || resourceType === 'stylesheet' || resourceType === 'font') {
            request.abort();
          } else {
            request.continue();
          }
        });

        // Construct the search URL
        const searchUrl = this.buildSearchUrl(params);
        await page.goto(searchUrl, { 
          waitUntil: 'networkidle0',
          timeout: this.pageTimeout 
        });

        // Wait for job cards with increased timeout and multiple selectors
        try {
          await Promise.race([
            page.waitForSelector('.job_seen_beacon', { timeout: this.pageTimeout }),
            page.waitForSelector('.jobsearch-ResultsList', { timeout: this.pageTimeout }),
            page.waitForSelector('.jobCard', { timeout: this.pageTimeout })
          ]);
        } catch (selectorError) {
          const errorMessage = selectorError instanceof Error ? selectorError.message : 'Unknown error';
          console.log('Initial selectors not found, checking for alternative layouts:', errorMessage);
          // Check for alternative layouts or error messages
          const content = await page.content();
          if (content.includes('No jobs found')) {
            console.log('No jobs found message detected');
            return [];
          }
        }

        // Get the page content
        const content = await page.content();
        const $ = load(content);

        const jobs = [];

        // Try multiple selectors for job cards
        const jobCards = $('.job_seen_beacon, .jobsearch-ResultsList > div, .jobCard');

        jobCards.each((_, element) => {
          const card = $(element);
          
          // Try multiple selectors for each field
          const title = card.find('.jobTitle, .title, h2').first().text().trim();
          const company = card.find('.companyName, .company, .employer').first().text().trim();
          const location = card.find('.companyLocation, .location').first().text().trim();
          const salary = card.find('.salary-snippet, .salaryText').first().text().trim();
          const jobType = card.find('.attribute_snippet, .jobType').first().text().trim();
          const jobId = card.attr('data-jk') || `indeed-${Date.now()}-${_}`;
          const jobUrl = `${this.baseUrl}/viewjob?jk=${jobId}`;

          if (title && company) {
            jobs.push({
              id: `temp-${jobId}`,
              platform: 'indeed',
              externalId: jobId,
              title,
              company,
              location,
              description: '', // Will be filled when viewing job details
              salary: salary || null,
              jobType: jobType || null,
              url: jobUrl,
              postedAt: new Date(),
              isExternal: true,
              status: 'NEW',
              notes: null,
              resumeUrl: null,
              coverLetterUrl: null,
              userId: null,
            });
          }
        });

        await browser.close();
        return jobs;
      } catch (error) {
        console.error(`Error during Indeed job search (attempt ${retryCount + 1}/${this.maxRetries}):`, error);
        
        if (browser) {
          try {
            await browser.close();
          } catch (closeError) {
            console.error('Error closing browser:', closeError);
          }
        }

        retryCount++;
        if (retryCount < this.maxRetries) {
          const delay = this.retryDelay * Math.pow(2, retryCount);
          console.log(`Waiting ${delay}ms before retry...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    console.log('All retry attempts failed, returning empty results');
    return [];
  }

  /**
   * Get detailed job information
   */
  async getJobDetails(jobId) {
    let browser;
    let retryCount = 0;

    while (retryCount < this.maxRetries) {
      try {
        browser = await puppeteer.launch({
          headless: true,
          args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--window-size=1920x1080'
          ]
        });

        const page = await browser.newPage();
        await page.setViewport({ width: 1920, height: 1080 });
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

        const jobUrl = `${this.baseUrl}/viewjob?jk=${jobId}`;
        await page.goto(jobUrl, { 
          waitUntil: 'networkidle0',
          timeout: this.pageTimeout 
        });

        // Wait for job details with multiple selectors
        await Promise.race([
          page.waitForSelector('#jobDescriptionText', { timeout: this.pageTimeout }),
          page.waitForSelector('.jobsearch-JobComponent', { timeout: this.pageTimeout })
        ]);

        const content = await page.content();
        const $ = load(content);

        const description = $('#jobDescriptionText, .jobsearch-JobComponent-description').text().trim();
        const jobType = $('.jobsearch-JobMetadataHeader-item, .icl-u-textColor--secondary:contains("Job Type")').first().text().trim();
        const salary = $('.jobsearch-JobMetadataHeader-item:contains("$"), .salary-snippet').first().text().trim();

        await browser.close();

        return {
          description,
          jobType: jobType || null,
          salary: salary || null,
        };
      } catch (error) {
        console.error(`Error fetching Indeed job details (attempt ${retryCount + 1}/${this.maxRetries}):`, error);
        
        if (browser) {
          try {
            await browser.close();
          } catch (closeError) {
            console.error('Error closing browser:', closeError);
          }
        }

        retryCount++;
        if (retryCount < this.maxRetries) {
          const delay = this.retryDelay * Math.pow(2, retryCount);
          console.log(`Waiting ${delay}ms before retry...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    console.error('All retry attempts failed for job details');
    return null;
  }

  /**
   * Build the search URL with parameters
   */
  buildSearchUrl(params) {
    const queryParams = new URLSearchParams();
    queryParams.append('q', params.query);
    if (params.location) queryParams.append('l', params.location);
    if (params.start) queryParams.append('start', params.start.toString());
    if (params.fromage) queryParams.append('fromage', params.fromage.toString());
    if (params.sort) queryParams.append('sort', params.sort);
    
    // Add job type filter if specified
    if (params.jobType) {
      const jobTypeMap = {
        'FULL_TIME': 'fulltime',
        'PART_TIME': 'parttime',
        'CONTRACT': 'contract',
        'TEMPORARY': 'temporary',
        'INTERNSHIP': 'internship',
      };
      queryParams.append('jt', jobTypeMap[params.jobType] || 'fulltime');
    }

    return `${this.baseUrl}/jobs?${queryParams.toString()}`;
  }

  /**
   * Parse posted date string into Date object
   */
  parsePostedDate(dateStr) {
    const now = new Date();
    const match = dateStr.match(/(\d+)\s*(day|week|month|year)s?\s*ago/i);
    
    if (!match) return now;
    
    const [, num, unit] = match;
    const value = parseInt(num);
    
    switch (unit.toLowerCase()) {
      case 'day':
        now.setDate(now.getDate() - value);
        break;
      case 'week':
        now.setDate(now.getDate() - (value * 7));
        break;
      case 'month':
        now.setMonth(now.getMonth() - value);
        break;
      case 'year':
        now.setFullYear(now.getFullYear() - value);
        break;
    }
    
    return now;
  }
} 