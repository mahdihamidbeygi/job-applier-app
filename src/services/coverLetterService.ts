import { OpenAI } from '@langchain/openai';
import { ResumeData } from '@/types/resume';

export class CoverLetterService {
  private llm: OpenAI;

  constructor() {
    this.llm = new OpenAI({
      modelName: 'gpt-4',
      temperature: 0.7,
    });
  }

  async generateCoverLetter(
    resumeData: ResumeData,
    jobTitle: string,
    companyName: string,
    jobDescription: string
  ): Promise<string> {
    const prompt = `
      Generate a professional cover letter for the following job application:

      Job Title: ${jobTitle}
      Company: ${companyName}
      Job Description: ${jobDescription}

      Candidate Information:
      Name: ${resumeData.fullName}
      Current Title: ${resumeData.title}
      Experience: ${resumeData.experience.map(exp => 
        `${exp.title} at ${exp.company} (${exp.startDate} - ${exp.endDate || 'Present'})`
      ).join(', ')}
      Skills: ${resumeData.skills.technical.join(', ')}
      Education: ${resumeData.education.map(edu => 
        `${edu.degree} in ${edu.major} from ${edu.school}`
      ).join(', ')}

      Requirements:
      1. Keep the tone professional but engaging
      2. Highlight relevant skills and experience that match the job requirements
      3. Show enthusiasm for the company and position
      4. Keep it concise (3-4 paragraphs)
      5. Include specific examples from the candidate's experience
      6. Address the job requirements directly
      7. End with a strong closing statement

      Generate a well-structured cover letter that follows these requirements.
    `;

    try {
      const coverLetter = await this.llm.call(prompt);
      return coverLetter.trim();
    } catch (error) {
      console.error('Error generating cover letter:', error);
      throw new Error('Failed to generate cover letter');
    }
  }
} 