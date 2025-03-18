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
    const { jobId } = body;

    if (!jobId) {
      return NextResponse.json({ error: "Job ID is required" }, { status: 400 });
    }

    console.log(`Creating application for job ID: ${jobId} by user: ${session.user.id}`);

    // Check if job exists
    const job = await prisma.job.findUnique({
      where: { id: jobId },
    });

    if (!job) {
      console.error(`Job not found with ID: ${jobId}`);
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    // Check if application already exists
    const existingApplication = await prisma.jobApplication.findFirst({
      where: {
        userId: session.user.id,
        jobId,
      },
    });

    if (existingApplication) {
      console.log(`Application already exists for job ID: ${jobId} by user: ${session.user.id}`);
      return NextResponse.json(
        { 
          message: "Application already exists", 
          applicationId: existingApplication.id 
        }, 
        { status: 200 }
      );
    }

    // Create the application
    const application = await prisma.jobApplication.create({
      data: {
        userId: session.user.id,
        jobId,
        status: "PENDING",
      },
      include: {
        job: true,
      },
    });

    console.log(`Application created successfully with ID: ${application.id}`);
    return NextResponse.json(application);
  } catch (error) {
    console.error("Error creating application:", error);
    return NextResponse.json(
      { error: "Internal Server Error", details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}

export async function GET(request: Request) {
  const session = await auth();

  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    // Get query parameters
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const search = url.searchParams.get('search');
    
    // Build the where clause with proper typing
    const where: {
      userId: string;
      status?: string;
      OR?: Array<{
        job: {
          title?: { contains: string; mode: 'insensitive' };
          company?: { contains: string; mode: 'insensitive' };
        }
      }>;
    } = {
      userId: session.user.id,
    };
    
    // Add status filter if provided and not 'ALL'
    if (status && status !== 'ALL') {
      where.status = status;
    }
    
    // Add search filter if provided
    if (search) {
      where.OR = [
        { job: { title: { contains: search, mode: 'insensitive' } } },
        { job: { company: { contains: search, mode: 'insensitive' } } },
      ];
    }
    
    // Get applications
    const applications = await prisma.jobApplication.findMany({
      where,
      include: {
        job: true,
      },
      orderBy: {
        updatedAt: 'desc',
      },
    });

    return NextResponse.json(applications);
  } catch (error) {
    console.error("Error fetching applications:", error);
    return NextResponse.json(
      { error: "Internal Server Error", details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
} 