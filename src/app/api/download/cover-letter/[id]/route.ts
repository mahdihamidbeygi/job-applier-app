import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { convertCoverLetterToPDF } from '@/lib/coverLetterConverter';
import { Skill, Experience, Education } from '@prisma/client';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return new NextResponse('Unauthorized', { status: 401 });
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
      return new NextResponse('Profile not found', { status: 404 });
    }

    // Ensure params.id is available
    const { id } = await Promise.resolve(params);

    const jobApplication = await prisma.jobApplication.findUnique({
      where: { id },
      include: { job: true }
    });

    if (!jobApplication) {
      return new NextResponse('Job application not found', { status: 404 });
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
        technical: profile.skills.map((skill: Skill) => skill.name),
        soft: []
      },
      experience: profile.experience.map((exp: Experience) => ({
        title: exp.title,
        company: exp.company,
        location: exp.location || '',
        startDate: exp.startDate.toISOString(),
        endDate: exp.endDate?.toISOString(),
        achievements: (exp.description || '').split('\n')
      })),
      education: profile.education.map((edu: Education) => ({
        degree: edu.degree,
        major: edu.field,
        school: edu.school,
        location: '',
        graduationYear: edu.endDate ? new Date(edu.endDate).getFullYear().toString() : ''
      })),
      projects: [],
      certifications: []
    };

    // Generate PDF
    const pdfBuffer = await convertCoverLetterToPDF(
      jobApplication.coverLetter || '',
      resumeData
    );

    // Return PDF with appropriate headers
    return new NextResponse(pdfBuffer, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="cover-letter.pdf"`,
      },
    });
  } catch (error) {
    console.error('Error generating cover letter PDF:', error);
    return new NextResponse('Error generating PDF', { status: 500 });
  }
} 