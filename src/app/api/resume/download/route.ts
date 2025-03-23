import { NextRequest, NextResponse } from 'next/server';
import { convertMarkdownToPDF } from '@/lib/pdfConverter';
import { ResumeData } from '@/types/resume';

export async function POST(request: NextRequest) {
  try {
    const data: ResumeData = await request.json();

    // Generate PDF
    const pdfBuffer = await convertMarkdownToPDF('', data);
    
    return new NextResponse(pdfBuffer, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="resume.pdf"',
      },
    });
  } catch (error) {
    console.error('Error generating resume:', error);
    return NextResponse.json(
      { error: 'Failed to generate resume' },
      { status: 500 }
    );
  }
} 