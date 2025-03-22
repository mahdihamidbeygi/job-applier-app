import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { convertMarkdownToPDF } from '@/lib/pdfConverter';
import { ResumeData } from '@/types/resume';
import { Skill, Experience, Education } from '@prisma/client';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const session = await auth();
    if (!session?.user) {
      return new Response("Unauthorized", { status: 401 });
    }

    // Ensure params is resolved
    const resolvedParams = await Promise.resolve(params);
    const jobId = resolvedParams.id;

    const job = await prisma.job.findUnique({
      where: { id: jobId }
    });

    if (!job) {
      return new Response("Job not found", { status: 404 });
    }

    const userProfile = await prisma.userProfile.findUnique({
      where: { userId: session.user.id },
      include: {
        experience: true,
        education: true,
        skills: true
      }
    });

    if (!userProfile) {
      return new Response("User profile not found", { status: 404 });
    }

    // Transform profile data to match ResumeData type
    const resumeData: ResumeData = {
      jobDescription: job.description || '',
      fullName: userProfile.name || '',
      title: userProfile.experience[0]?.title || '',
      email: userProfile.email || '',
      phone: userProfile.phone || '',
      location: userProfile.location || '',
      linkedin: userProfile.linkedinUrl || '',
      github: userProfile.githubUrl || '',
      skills: {
        technical: userProfile.skills.map((skill: Skill) => skill.name),
        soft: [],
      },
      experience: userProfile.experience.map((exp: Experience) => ({
        title: exp.title,
        company: exp.company,
        location: exp.location || '',
        startDate: exp.startDate,
        endDate: exp.endDate,
        description: exp.description || '',
        achievements: exp.description ? exp.description.split('\n').filter((line: string) => line.trim()) : [],
      })),
      education: userProfile.education.map((edu: Education) => ({
        school: edu.school,
        degree: edu.degree,
        field: edu.field || '',
        startDate: edu.startDate,
        endDate: edu.endDate,
        description: edu.description || '',
      })),
      projects: [],
      certifications: [],
    };

    // Generate PDF using our template
    const pdfBuffer = await convertMarkdownToPDF('', resumeData);

    return new NextResponse(pdfBuffer, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="resume-${job.company}.pdf"`,
      },
    });
  } catch (error) {
    console.error("Error generating resume:", error);
    return new Response("Error generating resume", { status: 500 });
  }
} 