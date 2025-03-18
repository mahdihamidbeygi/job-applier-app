import { Job } from '@prisma/client';
import axios from 'axios';
import { load } from 'cheerio';
import axiosRetry from 'axios-retry';
import { IndeedService } from './indeedService';

interface IndeedFeedParams {
  query: string;
  location?: string;
  jobType?: string;
  fromage?: number;
  start?: number;
  limit?: number;
  sort?: 'date' | 'relevance';
}

export class IndeedFeedService {
  private readonly baseUrl = 'https://www.indeed.com';
  private readonly indeedScraper: IndeedService;
  private readonly maxRetries = 4;
  private readonly retryDelay = 2000; // Increased to 2 seconds
  private readonly maxTimeout = 60000; // 60 seconds

  constructor() {
    this.indeedScraper = new IndeedService();
    
    // Configure axios retry behavior with exponential backoff
    axiosRetry(axios, {
      retries: this.maxRetries,
      retryDelay: (retryCount) => {
        const delay = this.retryDelay * Math.pow(2, retryCount - 1);
        return Math.min(delay, 10000); // Cap at 10 seconds
      },
      retryCondition: (error) => {
        return axiosRetry.isNetworkOrIdempotentRequestError(error) || 
               error.response?.status === 429 ||
               error.code === 'ECONNABORTED';
      },
      timeout: this.maxTimeout,
      timeoutErrorMessage: 'Request timed out after 60 seconds'
    });
  }

  /**
   * Search for jobs using Indeed RSS feed with web scraping fallback
   */
  async searchJobs(params: IndeedFeedParams): Promise<Job[]> {
    let retryCount = 0;
    const maxRetries = 3;

    while (retryCount < maxRetries) {
      try {
        // First attempt: RSS feed
        const jobs = await this.searchRssFeed(params);
        if (jobs.length > 0) {
          return jobs;
        }

        console.log('RSS feed returned no results, falling back to web scraping...');
        
        // Add delay before web scraping
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Fallback: Web scraping with increased timeout
        return await this.indeedScraper.searchJobs({
          ...params,
          timeout: this.maxTimeout
        });
      } catch (error) {
        retryCount++;
        const isLastAttempt = retryCount === maxRetries;
        
        if (error.response?.status === 429) {
          console.log(`Rate limited (attempt ${retryCount}/${maxRetries}), waiting before retry...`);
          await new Promise(resolve => setTimeout(resolve, this.retryDelay * Math.pow(2, retryCount)));
        } else if (!isLastAttempt) {
          console.log(`Error fetching jobs (attempt ${retryCount}/${maxRetries}):`, error.message);
          await new Promise(resolve => setTimeout(resolve, this.retryDelay));
        } else {
          console.error('All attempts failed, returning empty results:', error);
          return [];
        }
      }
    }

    return [];
  }

  /**
   * Search for jobs using Indeed RSS feed
   */
  private async searchRssFeed(params: IndeedFeedParams): Promise<Job[]> {
    const url = this.buildRssUrl(params);
    console.log(`Fetching Indeed RSS feed: ${url}`);

    try {
      const response = await axios.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
          'Accept': 'application/rss+xml, application/xml, text/xml, */*',
          'Accept-Language': 'en-US,en;q=0.9',
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache',
          'Referer': 'https://www.indeed.com/',
        },
        timeout: 10000, // 10 second timeout
      });

      const $ = load(response.data, { xmlMode: true });
      const items = $('item');
      const jobs: Job[] = [];

      items.each((_, item) => {
        const $item = $(item);
        const title = $item.find('title').text().trim();
        const company = $item.find('source').text().trim();
        const location = $item.find('location').text().trim();
        const description = $item.find('description').text().trim();
        const link = $item.find('link').text().trim();
        const guid = $item.find('guid').text().trim();
        const pubDate = $item.find('pubDate').text().trim();

        if (title && company) {
          jobs.push({
            id: `temp-${guid}`,
            platform: 'indeed',
            externalId: guid,
            title,
            company,
            location,
            description,
            salary: null, // RSS feed doesn't include salary
            jobType: null, // RSS feed doesn't include job type
            url: link,
            postedAt: new Date(pubDate),
            isExternal: true,
            status: 'NEW',
            notes: null,
            resumeUrl: null,
            coverLetterUrl: null,
            userId: null,
          } as Job);
        }
      });

      return jobs;
    } catch (error) {
      console.error(`Error fetching Indeed RSS feed:`, error);
      throw error;
    }
  }

  /**
   * Build the RSS feed URL with parameters
   */
  private buildRssUrl(params: IndeedFeedParams): string {
    const queryParams = new URLSearchParams();
    queryParams.append('q', params.query);
    if (params.location) queryParams.append('l', params.location);
    if (params.fromage) queryParams.append('fromage', params.fromage.toString());
    
    // Add job type filter if specified
    if (params.jobType) {
      const jobTypeMap: Record<string, string> = {
        'FULL_TIME': 'fulltime',
        'PART_TIME': 'parttime',
        'CONTRACT': 'contract',
        'TEMPORARY': 'temporary',
        'INTERNSHIP': 'internship',
      };
      queryParams.append('jt', jobTypeMap[params.jobType] || 'fulltime');
    }

    // Add sort parameter
    if (params.sort) {
      queryParams.append('sort', params.sort);
    }

    // Add limit parameter
    if (params.limit) {
      queryParams.append('limit', params.limit.toString());
    }

    // Add start parameter
    if (params.start) {
      queryParams.append('start', params.start.toString());
    }

    return `${this.baseUrl}/rss?${queryParams.toString()}`;
  }

  /**
   * Get detailed job information
   */
  async getJobDetails(jobId: string): Promise<Partial<Job> | null> {
    try {
      return await this.indeedScraper.getJobDetails(jobId);
    } catch (error) {
      console.error('Error fetching Indeed job details:', error);
      return null;
    }
  }

  /**
   * Paginate through all results from the Indeed RSS feed
   * This handles the 25 results per page limitation
   */
  async getAllJobs(params: IndeedFeedParams): Promise<Job[]> {
    try {
      const allJobs: Job[] = [];
      let start = 0;
      const limit = 25; // Indeed limits to 25 results per request
      let hasMoreJobs = true;
      let consecutiveEmptyResults = 0;
      const maxConsecutiveEmptyResults = 2;

      while (hasMoreJobs) {
        const pageParams = { ...params, start, limit };
        const jobs = await this.searchJobs(pageParams);

        if (jobs.length === 0) {
          consecutiveEmptyResults++;
          if (consecutiveEmptyResults >= maxConsecutiveEmptyResults) {
            console.log(`Received ${consecutiveEmptyResults} consecutive empty results, stopping pagination`);
            hasMoreJobs = false;
          }
        } else {
          consecutiveEmptyResults = 0;
          allJobs.push(...jobs);
          start += limit;

          // Add a delay to avoid rate limiting
          await new Promise(resolve => setTimeout(resolve, 1000));
        }

        // Safety check to prevent infinite loops
        if (start > 100) {
          console.log('Reached maximum pagination limit (100 results), stopping');
          hasMoreJobs = false;
        }
      }

      console.log(`Retrieved a total of ${allJobs.length} jobs from Indeed`);
      return allJobs;
    } catch (error) {
      console.error('Error retrieving all jobs from Indeed:', error);
      
      // If getAllJobs fails completely, try a single search with fallback
      return this.indeedScraper.searchJobs(params);
    }
  }
} 