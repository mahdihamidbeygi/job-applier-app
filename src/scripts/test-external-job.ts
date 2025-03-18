/**
 * This script tests the external job creation and application process.
 * 
 * To run this script:
 * 1. Make sure you have a user in the database
 * 2. Run: npx ts-node -r tsconfig-paths/register src/scripts/test-external-job.ts
 */

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  try {
    // 1. Create a test user if needed
    const testUser = await prisma.user.findFirst();
    
    if (!testUser) {
      console.error('No users found in the database. Please create a user first.');
      return;
    }
    
    console.log(`Using test user: ${testUser.id}`);

    // 2. Create an external job
    const externalJob = await prisma.job.create({
      data: {
        platform: 'TestPlatform',
        externalId: `test-${Date.now()}`,
        title: 'Test External Job',
        company: 'Test Company',
        location: 'Remote',
        description: 'This is a test job description',
        salary: '$100,000 - $150,000',
        jobType: 'Full-time',
        url: 'https://example.com/job',
        postedAt: new Date(),
        isExternal: true,
      },
    });
    
    console.log(`Created external job: ${externalJob.id}`);

    // 3. Create an application for the external job
    const application = await prisma.jobApplication.create({
      data: {
        userId: testUser.id,
        jobId: externalJob.id,
        status: 'PENDING',
      },
      include: {
        job: true,
      },
    });
    
    console.log(`Created application: ${application.id}`);
    console.log('Test completed successfully!');
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    await prisma.$disconnect();
  }
}

main(); 