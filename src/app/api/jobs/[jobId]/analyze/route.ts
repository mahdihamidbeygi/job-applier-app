import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { JobSkillsService } from '@/services/jobSkillsService';
import { ResumeData } from '@/types/resume';

export async function POST(
  request: Request,
  { params }: { params: { jobId: string } }
) {
  const session = await auth();

  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const resolvedParams = await Promise.resolve(params);
    const jobId = resolvedParams.jobId;
    
    const job = await prisma.job.findUnique({
      where: { id: jobId },
    });

    if (!job) {
      return NextResponse.json({ error: 'Job not found' }, { status: 404 });
    }

    const userProfile = await prisma.userProfile.findUnique({
      where: { userId: session.user.id },
      include: {
        skills: true,
        experience: true,
        education: true,
      },
    });

    if (!userProfile) {
      return NextResponse.json(
        { error: 'User profile not found' },
        { status: 404 }
      );
    }

    // Convert user profile to ResumeData format
    const resumeData: ResumeData = {
      fullName: userProfile.name,
      title: userProfile.experience[0]?.title || '',
      email: userProfile.email,
      phone: userProfile.phone || undefined,
      location: userProfile.location || undefined,
      linkedin: userProfile.linkedinUrl || undefined,
      github: userProfile.githubUrl || undefined,
      skills: {
        technical: userProfile.skills.map(skill => skill.name),
        soft: [], // You might want to add soft skills to your schema
      },
      experience: userProfile.experience.map(exp => ({
        company: exp.company,
        title: exp.title,
        location: exp.location || undefined,
        startDate: exp.startDate,
        endDate: exp.endDate,
        description: exp.description || undefined,
        achievements: [], // You might want to add achievements to your schema
      })),
      education: userProfile.education.map(edu => ({
        school: edu.school,
        degree: edu.degree,
        field: edu.field,
        startDate: edu.startDate,
        endDate: edu.endDate,
        description: edu.description || undefined,
      })),
    };

    // Initialize service
    const jobSkillsService = new JobSkillsService();

    // Extract skills from job description
    const jobSkills = await jobSkillsService.extractSkills(
      job.description || ''
    );

    // Match skills with resume
    const skillsMatch = await jobSkillsService.matchSkillsWithResume(
      jobSkills,
      resumeData
    );

    // Generate tailored resume
    const tailoredResume = await jobSkillsService.generateTailoredResume(
      resumeData,
      jobSkills,
      skillsMatch
    );

    // Generate cover letter
    const coverLetter = await jobSkillsService.generateTailoredCoverLetter(
      resumeData,
      jobSkills,
      skillsMatch,
      job.title,
      job.company
    );

    // Create or update job application
    const application = await prisma.jobApplication.upsert({
      where: {
        id: `${jobId}-${session.user.id}`,
      },
      update: {
        status: 'IN_PROGRESS',
        notes: JSON.stringify({
          jobSkills,
          skillsMatch,
          tailoredResume,
          coverLetter,
        }),
      },
      create: {
        id: `${jobId}-${session.user.id}`,
        jobId,
        userId: session.user.id,
        status: 'IN_PROGRESS',
        notes: JSON.stringify({
          jobSkills,
          skillsMatch,
          tailoredResume,
          coverLetter,
        }),
      },
    });

    return NextResponse.json({
      success: true,
      data: {
        jobSkills,
        skillsMatch,
        tailoredResume,
        coverLetter,
        application,
      },
    });
  } catch (error) {
    console.error('Error analyzing job:', error);
    return NextResponse.json(
      { error: 'Failed to analyze job' },
      { status: 500 }
    );
  }
} 