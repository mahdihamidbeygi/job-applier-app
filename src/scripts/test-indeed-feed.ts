/**
 * Test script for the Indeed RSS feed integration
 * 
 * Run with: npx ts-node src/scripts/test-indeed-feed.ts
 */

import { IndeedFeedService } from '../services/indeedFeedService';

async function testIndeedFeed() {
  console.log('Testing Indeed RSS feed integration...');
  
  const indeedFeedService = new IndeedFeedService();
  
  // Test with a simple query
  const params = {
    query: 'software developer',
    location: 'remote',
    sort: 'date' as const,
    fromage: 7, // Last 7 days
  };
  
  console.log(`Searching for "${params.query}" in "${params.location || 'anywhere'}"...`);
  
  try {
    // Test single page search
    console.log('\nTesting single page search:');
    const singlePageJobs = await indeedFeedService.searchJobs(params);
    console.log(`Found ${singlePageJobs.length} jobs in single page search`);
    
    if (singlePageJobs.length > 0) {
      console.log('\nSample job from single page search:');
      console.log(JSON.stringify(singlePageJobs[0], null, 2));
    }
    
    // Test pagination
    console.log('\nTesting pagination with getAllJobs:');
    const allJobs = await indeedFeedService.getAllJobs(params);
    console.log(`Found ${allJobs.length} jobs in total with pagination`);
    
    if (allJobs.length > 25) {
      console.log(`\nPagination successful! Retrieved more than 25 jobs (${allJobs.length})`);
    } else {
      console.log('\nPagination may not have worked as expected, or there are fewer than 25 results available.');
    }
    
    console.log('\nTest completed successfully!');
  } catch (error) {
    console.error('Error testing Indeed RSS feed:', error);
  }
}

// Run the test
testIndeedFeed().catch(console.error); 