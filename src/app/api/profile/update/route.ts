import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

interface Experience {
  title: string;
  company: string;
  location: string | null;
  startDate: Date;
  endDate: Date | null;
  description: string | null;
  skills: string[];
}

interface Education {
  school: string;
  degree: string;
  field: string;
  startDate: Date;
  endDate: Date | null;
  gpa: number | null;
}

export async function PUT(request: Request) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const data = await request.json();
    const { linkedInUrl, githubUrl, portfolioUrl, bio, skills, experience, education } = data;

    // Basic URL validation
    const urlFields = { linkedInUrl, githubUrl, portfolioUrl };
    for (const [field, url] of Object.entries(urlFields)) {
      if (url && !isValidUrl(url)) {
        return NextResponse.json({ error: `Invalid ${field} URL` }, { status: 400 });
      }
    }

    // Update or create profile with experience and education
    const profile = await prisma.profile.upsert({
      where: {
        userId: session.user.id,
      },
      update: {
        linkedInUrl,
        githubUrl,
        portfolioUrl,
        bio,
        skills: skills || [],
        isProfileComplete: Boolean(linkedInUrl || githubUrl || portfolioUrl) && Boolean(skills?.length),
        ...(experience && {
          experience: {
            deleteMany: {},
            create: experience.map((exp: Experience) => ({
              title: exp.title,
              company: exp.company,
              location: exp.location,
              startDate: exp.startDate,
              endDate: exp.endDate,
              description: exp.description,
              skills: exp.skills || [],
            })),
          },
        }),
        ...(education && {
          education: {
            deleteMany: {},
            create: education.map((edu: Education) => ({
              school: edu.school,
              degree: edu.degree,
              field: edu.field,
              startDate: edu.startDate,
              endDate: edu.endDate,
              gpa: edu.gpa,
            })),
          },
        }),
      },
      create: {
        userId: session.user.id,
        linkedInUrl,
        githubUrl,
        portfolioUrl,
        bio,
        skills: skills || [],
        isProfileComplete: Boolean(linkedInUrl || githubUrl || portfolioUrl) && Boolean(skills?.length),
        ...(experience && {
          experience: {
            create: experience.map((exp: Experience) => ({
              title: exp.title,
              company: exp.company,
              location: exp.location,
              startDate: exp.startDate,
              endDate: exp.endDate,
              description: exp.description,
              skills: exp.skills || [],
            })),
          },
        }),
        ...(education && {
          education: {
            create: education.map((edu: Education) => ({
              school: edu.school,
              degree: edu.degree,
              field: edu.field,
              startDate: edu.startDate,
              endDate: edu.endDate,
              gpa: edu.gpa,
            })),
          },
        }),
      },
    });

    return NextResponse.json({ success: true, profile });
  } catch (error) {
    console.error('Error updating profile:', error);
    return NextResponse.json({ error: 'Error updating profile' }, { status: 500 });
  }
}

function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
} 