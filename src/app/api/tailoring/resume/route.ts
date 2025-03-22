import { NextRequest, NextResponse } from 'next/server';
import { convertMarkdownToPDF } from '@/lib/pdfConverter';
import { ResumeData } from '@/types/resume';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import fs from 'fs';
import path from 'path';
import { Skill, Experience, Education } from '@prisma/client';

export async function POST(request: NextRequest) {
  try {
    // Check authentication
    const session = await auth();
    if (!session?.user?.email) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    // Get user profile
    const profile = await prisma.userProfile.findFirst({
      where: { email: session.user.email },
      include: {
        skills: true,
        experience: true,
        education: true,
      },
    });

    if (!profile) {
      return NextResponse.json(
        { error: 'User profile not found' },
        { status: 404 }
      );
    }

    // Get job description from request
    const { jobDescription } = await request.json();
    
    if (!jobDescription) {
      return NextResponse.json(
        { error: 'Job description is required' },
        { status: 400 }
      );
    }

    // Read resume template
    const templatePath = path.join(process.cwd(), 'src', 'templates', 'resume.md');
    const template = fs.readFileSync(templatePath, 'utf-8');

    // Convert profile data to ResumeData format
    const resumeData: ResumeData = {
      fullName: profile.name,
      title: profile.summary || '',
      email: profile.email,
      phone: profile.phone || '',
      location: profile.location || '',
      linkedin: profile.linkedinUrl || '',
      github: profile.githubUrl || '',
      skills: {
        technical: profile.skills.map((skill: Skill) => skill.name),
        soft: []
      },
      experience: profile.experience.map((exp: Experience) => ({
        title: exp.title,
        company: exp.company,
        location: exp.location || '',
        startDate: exp.startDate,
        endDate: exp.endDate,
        achievements: (exp.description || '').split('\n')
      })),
      education: profile.education.map((edu: Education) => ({
        school: edu.school,
        degree: edu.degree,
        field: edu.field,
        startDate: edu.startDate,
        endDate: edu.endDate,
        description: edu.description || undefined
      }))
    };

    // Generate PDF
    const pdfBuffer = await convertMarkdownToPDF(template, resumeData);
    
    return new NextResponse(pdfBuffer, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="tailored-resume.pdf"',
      },
    });
  } catch (error) {
    console.error('Error generating tailored resume:', error);
    return NextResponse.json(
      { error: 'Failed to generate tailored resume' },
      { status: 500 }
    );
  }
} 