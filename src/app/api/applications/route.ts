import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { auth } from "@/lib/auth";
import { CoverLetterService } from "@/services/coverLetterService";
import * as cheerio from 'cheerio';

export async function POST(request: Request) {
  const session = await auth();

  if (!session?.user?.id) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  try {
    const body = await request.json();
    const { jobId, status } = body;

    if (!jobId) {
      return new NextResponse("Job ID is required", { status: 400 });
    }

    // Check if job exists
    const job = await prisma.job.findUnique({
      where: { id: jobId },
    });

    if (!job) {
      return new NextResponse("Job not found", { status: 404 });
    }

    if (!job.description) {
      return new NextResponse("Job description is required", { status: 400 });
    }

    // Get user profile
    const profile = await prisma.userProfile.findUnique({
      where: { userId: session.user.id },
      include: {
        skills: true,
        experience: true,
        education: true,
      },
    });

    if (!profile) {
      return new NextResponse("Profile not found", { status: 404 });
    }

    // Convert profile data to ResumeData format
    const resumeData = {
      fullName: profile.name,
      title: profile.summary || '',
      email: profile.email,
      phone: profile.phone || '',
      location: profile.location || '',
      linkedin: profile.linkedinUrl || '',
      github: profile.githubUrl || '',
      summary: profile.summary || '',
      skills: {
        technical: profile.skills.map(skill => skill.name),
        soft: []
      },
      experience: profile.experience.map(exp => ({
        title: exp.title,
        company: exp.company,
        location: exp.location || '',
        startDate: new Date(exp.startDate),
        endDate: exp.endDate ? new Date(exp.endDate) : null,
        achievements: (exp.description || '').split('\n')
      })),
      education: profile.education.map(edu => ({
        degree: edu.degree,
        field: edu.field,
        school: edu.school,
        startDate: edu.startDate ? new Date(edu.startDate) : new Date(),
        endDate: edu.endDate ? new Date(edu.endDate) : null,
        description: ''
      })),
      projects: [],
      certifications: []
    };

    const jobResponse = await fetch(job.url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });
    const jobHtml = await jobResponse.text();
    const $ = cheerio.load(jobHtml);

    let jobDescription = '';

    // LinkedIn specific selectors
    if (job.url.includes('linkedin.com')) {
      jobDescription = $('.jobs-description__content').text().trim() || 
                      $('.description__text').text().trim() ||
                      $('.show-more-less-html__markup').text().trim();
    }
    // Indeed specific selectors  
    else if (job.url.includes('indeed.com')) {
      jobDescription = $('#jobDescriptionText').text().trim();
    }
    // Glassdoor specific selectors
    else if (job.url.includes('glassdoor.com')) {
      jobDescription = $('.jobDescriptionContent').text().trim() ||
                      $('.desc').text().trim();
    }
  job.description = jobDescription;

    // Generate cover letter
    const coverLetterService = new CoverLetterService();
    const coverLetter = await coverLetterService.generateCoverLetter(
      resumeData,
      job.title,
      job.company,
      job.description
    );

    if (!coverLetter) {
      return new NextResponse("Failed to generate cover letter", { status: 500 });
    }

    // Create the application with the generated cover letter
    const application = await prisma.jobApplication.create({
      data: {
        userId: session.user.id,
        jobId,
        status: status || "DRAFT",
        coverLetter,
      },
      include: {
        job: true,
      },
    });

    return NextResponse.json(application);
  } catch (error) {
    console.error("Error creating application:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
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