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
}

interface Education {
  school: string;
  degree: string;
  field: string;
  startDate: Date;
  endDate: Date | null;
  description: string | null;
}

interface Publication {
  title: string;
  publisher: string;
  date: Date | null;
  description: string | null;
  url: string | null;
}

interface Certification {
  name: string;
  issuer: string;
  date: Date | null;
  url: string | null;
}

export async function PUT(request: Request) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const data = await request.json();
    const { 
      linkedinUrl, 
      githubUrl, 
      portfolioUrl,
      summary,
      skills,
      experience,
      education,
      publications,
      certifications,
      phone,
      location
    } = data;

    // Basic URL validation
    const urlFields = { linkedinUrl, githubUrl, portfolioUrl };
    for (const [field, url] of Object.entries(urlFields)) {
      if (url && !isValidUrl(url)) {
        return NextResponse.json({ error: `Invalid ${field} URL` }, { status: 400 });
      }
    }

    // Update or create profile with all sections
    const profile = await prisma.userProfile.upsert({
      where: {
        userId: session.user.id,
      },
      update: {
        linkedinUrl,
        githubUrl,
        portfolioUrl,
        summary,
        phone,
        location,
        ...(skills && {
          skills: {
            deleteMany: {},
            create: skills.map((skill: string) => ({
              name: skill,
              level: null
            })),
          },
        }),
        ...(experience && {
          experience: {
            deleteMany: {},
            create: experience.map((exp: Experience) => ({
              title: exp.title,
              company: exp.company,
              location: exp.location || '',
              startDate: exp.startDate,
              endDate: exp.endDate,
              description: exp.description || '',
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
              description: edu.description,
            })),
          },
        }),
        ...(publications && {
          publications: {
            deleteMany: {},
            create: publications.map((pub: Publication) => ({
              title: pub.title,
              publisher: pub.publisher,
              date: pub.date,
              description: pub.description,
              url: pub.url,
            })),
          },
        }),
        ...(certifications && {
          certifications: {
            deleteMany: {},
            create: certifications.map((cert: Certification) => ({
              name: cert.name,
              issuer: cert.issuer,
              date: cert.date,
              url: cert.url,
            })),
          },
        }),
      },
      create: {
        userId: session.user.id,
        name: session.user.name || '',
        email: session.user.email || '',
        linkedinUrl,
        githubUrl,
        portfolioUrl,
        summary,
        phone,
        location,
        ...(skills && {
          skills: {
            create: skills.map((skill: string) => ({
              name: skill,
              level: null
            })),
          },
        }),
        ...(experience && {
          experience: {
            create: experience.map((exp: Experience) => ({
              title: exp.title,
              company: exp.company,
              location: exp.location || '',
              startDate: exp.startDate,
              endDate: exp.endDate,
              description: exp.description || '',
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
              description: edu.description,
            })),
          },
        }),
        ...(publications && {
          publications: {
            create: publications.map((pub: Publication) => ({
              title: pub.title,
              publisher: pub.publisher,
              date: pub.date,
              description: pub.description,
              url: pub.url,
            })),
          },
        }),
        ...(certifications && {
          certifications: {
            create: certifications.map((cert: Certification) => ({
              name: cert.name,
              issuer: cert.issuer,
              date: cert.date,
              url: cert.url,
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