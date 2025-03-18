import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { auth } from "@/lib/auth";

export async function POST(request: Request) {
  const session = await auth();

  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = await request.json();
    const { 
      platform, 
      externalId, 
      title, 
      company, 
      location, 
      description, 
      salary, 
      jobType, 
      postedAt 
    } = body;
    
    let { url } = body;

    // Validate required fields
    if (!platform || !externalId || !title || !company || !description) {
      return NextResponse.json(
        { error: "Missing required fields", details: "platform, externalId, title, company, and description are required" },
        { status: 400 }
      );
    }

    // Ensure URL is valid
    if (!url || !url.startsWith('http')) {
      console.log(`Invalid URL provided for ${platform} job ${externalId}: "${url}". Attempting to construct a valid URL.`);
      
      // Construct a URL based on the platform and externalId
      switch (platform.toLowerCase()) {
        case 'linkedin':
          url = `https://www.linkedin.com/jobs/view/${externalId}`;
          break;
        case 'indeed':
          url = `https://www.indeed.com/viewjob?jk=${externalId}`;
          break;
        case 'glassdoor':
          url = `https://www.glassdoor.com/job-listing/${externalId}`;
          break;
        default:
          console.log(`Cannot construct URL for ${platform} job ${externalId}`);
          // Use a placeholder URL if we can't construct a valid one
          url = `https://example.com/jobs/${platform}/${externalId}`;
          break;
      }
      
      console.log(`Constructed URL for ${platform} job ${externalId}: ${url}`);
    }

    // Check if job already exists
    let job = await prisma.job.findFirst({
      where: {
        platform,
        externalId,
      },
    });

    // If job doesn't exist, create it
    if (!job) {
      console.log(`Creating new ${platform} job: ${title} at ${company}`);
      job = await prisma.job.create({
        data: {
          platform,
          externalId,
          title,
          company,
          location: location || null,
          description,
          salary: salary || null,
          jobType: jobType || null,
          url,
          postedAt: postedAt ? new Date(postedAt) : new Date(),
          isExternal: true,
        },
      });
      console.log(`Created job with ID: ${job.id}`);
    } else {
      console.log(`Found existing job with ID: ${job.id}`);
      
      // Update the job if it exists but has missing or outdated information
      if (!job.url || job.url !== url || !job.description || job.description.length < description.length) {
        console.log(`Updating existing job with ID: ${job.id} with new information`);
        job = await prisma.job.update({
          where: { id: job.id },
          data: {
            title: title || job.title,
            company: company || job.company,
            location: location || job.location,
            description: description.length > job.description.length ? description : job.description,
            salary: salary || job.salary,
            jobType: jobType || job.jobType,
            url: url || job.url,
          },
        });
        console.log(`Updated job with ID: ${job.id}`);
      }
    }

    return NextResponse.json(job);
  } catch (error) {
    console.error("Error creating external job:", error);
    return NextResponse.json(
      { error: "Internal Server Error", details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
} 