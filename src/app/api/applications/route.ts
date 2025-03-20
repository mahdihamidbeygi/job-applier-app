import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { auth } from "@/lib/auth";
import { CoverLetterService } from "@/services/coverLetterService";

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
        startDate: exp.startDate.toISOString(),
        endDate: exp.endDate?.toISOString(),
        achievements: (exp.description || '').split('\n')
      })),
      education: profile.education.map(edu => ({
        degree: edu.degree,
        major: edu.field,
        school: edu.school,
        location: '',
        graduationYear: edu.endDate ? new Date(edu.endDate).getFullYear().toString() : ''
      })),
      projects: [],
      certifications: []
    };

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