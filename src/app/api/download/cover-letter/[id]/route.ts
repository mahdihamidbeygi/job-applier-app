import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { convertCoverLetterToPDF } from '@/lib/coverLetterConverter';

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

    // Generate PDF
    const pdfBuffer = await convertCoverLetterToPDF(
      jobApplication.coverLetter || ''
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