import { NextRequest, NextResponse } from 'next/server';
import { convertCoverLetterToPDF } from '@/lib/coverLetterConverter';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { ChatOllama } from '@langchain/community/chat_models/ollama';

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
      
    // Generate cover letter using Ollama
    const llm = new ChatOllama({
      model: "phi4",
      temperature: 0.5,
    });
    
    const prompt = `Write a professional cover letter following these rules:

1. Content:
   - Start directly with "Dear Hiring Manager"
   - No headers, no date, no address blocks
   - 3-4 paragraphs only
   - Focus on relevant experience and skills
   - Include specific examples from experience
   - Show enthusiasm for the role
   - End with "Sincerely, [Name]"

2. Format:
   - Justify all paragraphs
   - No bullet points
   - No numbering
   - No extra spacing between paragraphs
   - No questions or answers section

3. Style:
   - Professional tone
   - Action verbs
   - Specific achievements
   - Clear connection to job requirements

Job Description:
${jobDescription}

Candidate Information:
- Current Role: ${latestExp?.title || "professional"}
- Company: ${latestExp?.company || "various organizations"} 
- Key Skills: ${topSkills}
- Name: ${profile.name}

Write a compelling cover letter that immediately connects the candidate's experience to the job requirements.
if there are any questions in the job description, please answer them at the last paragraph of the cover letter.
Do not make any assumptions about the candidate's citizenship or residency situation until they mention it in the job description.
`;


    const completion = await llm.invoke(prompt);
    const coverLetterContent = completion.content as string || `
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
        'Content-Disposition': `attachment; filename="${profile.name.replace(" ", "_")}-Coverletter-${latestExp?.company}.pdf"`,
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