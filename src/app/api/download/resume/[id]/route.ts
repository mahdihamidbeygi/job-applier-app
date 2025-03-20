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
      fullName: userProfile.name || '',
      title: userProfile.experience[0]?.title || '',
      email: userProfile.email || '',
      phone: userProfile.phone || '',
      location: userProfile.location || '',
      linkedin: userProfile.linkedinUrl || '',
      github: userProfile.githubUrl || '',
      summary: userProfile.summary || '',
      skills: {
        technical: userProfile.skills.map((skill: Skill) => skill.name),
        soft: [],
      },
      experience: userProfile.experience.map((exp: Experience) => ({
        title: exp.title,
        company: exp.company,
        location: exp.location || '',
        startDate: exp.startDate.toISOString(),
        endDate: exp.endDate?.toISOString(),
        achievements: exp.description ? exp.description.split('\n').filter((line: string) => line.trim()) : [],
      })),
      education: userProfile.education.map((edu: Education) => ({
        degree: edu.degree,
        school: edu.school,
        location: '', // Education model doesn't have location
        graduationYear: edu.endDate?.getFullYear().toString() || '',
        major: edu.field || '',
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