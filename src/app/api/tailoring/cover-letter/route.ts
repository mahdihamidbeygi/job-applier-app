import { NextRequest, NextResponse } from 'next/server';
import { convertCoverLetterToPDF } from '@/lib/coverLetterConverter';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import OpenAI from 'openai';
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

    // Get the latest experience
    const latestExp = profile.experience && profile.experience.length > 0 
      ? profile.experience[0] 
      : null;

    // Get the top skills (up to 3)
    const topSkills = profile.skills && profile.skills.length > 0
      ? profile.skills.slice(0, 3).map(skill => skill.name).join(", ")
      : "relevant technical skills";
      
    // Generate cover letter using OpenAI
    const openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });
    
    const prompt = `Write a professional cover letter for a job application. Use the following information:

Job Description:
${jobDescription}

Candidate Information:
- Current/Recent Role: ${latestExp?.title || "professional"}
- Current/Recent Company: ${latestExp?.company || "various organizations"} 
- Top Skills: ${topSkills}
- Full Name: ${profile.name}

The cover letter should be personalized to the job description while highlighting the candidate's relevant experience and skills. Keep it concise, professional and compelling.`;

    const completion = await openai.chat.completions.create({
      model: "gpt-4",
      messages: [
        {
          role: "system",
          content: "You are a professional cover letter writer who creates compelling, tailored cover letters."
        },
        {
          role: "user", 
          content: prompt
        }
      ],
      temperature: 0.7,
    });

    const coverLetterContent = completion.choices[0].message.content || `
Dear Hiring Manager,

I am writing to express my interest in the open position at your company as detailed in the job description. With my background as a ${latestExp?.title || "professional"} and expertise in ${topSkills}, I believe I am well-positioned to make valuable contributions to your team.

Throughout my career at ${latestExp?.company || "various organizations"}, I have developed strong skills in problem-solving, collaboration, and delivering high-quality results. My experience aligns well with the requirements outlined in the job description, particularly in:

• ${profile.skills[0]?.name || "Technical expertise"} - Applied to deliver successful solutions
• Effective collaboration - Working across teams to achieve business objectives
• Problem-solving - Identifying challenges and implementing appropriate solutions

I am particularly drawn to your company because of its reputation for innovation and excellence in the industry. I am confident that my combination of technical knowledge and professional experience would make me a strong addition to your team.

Thank you for considering my application. I look forward to the opportunity to discuss how my background and skills align with your needs.

Sincerely,
${profile.name}`;

    // Generate PDF
    const pdfBuffer = await convertCoverLetterToPDF(coverLetterContent);
    
    return new NextResponse(pdfBuffer, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="tailored-cover-letter.pdf"',
      },
    });
  } catch (error) {
    console.error('Error generating tailored cover letter:', error);
    return NextResponse.json(
      { error: 'Failed to generate tailored cover letter' },
      { status: 500 }
    );
  }
} 