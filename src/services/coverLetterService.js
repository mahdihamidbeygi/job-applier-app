import { HumanMessage, SystemMessage } from '@langchain/core/messages';
import { OllamaService } from './ollamaService';

export class CoverLetterService {
  constructor() {
    this.llm = new OllamaService();
  }

  async generateCoverLetter(
    resumeData,
    jobTitle,
    companyName,
    jobDescription
  ) {
    const messages = [
      new SystemMessage(
        "You are a professional cover letter writer. Generate compelling cover letters that highlight relevant skills and experience."
      ),
      new HumanMessage(
        `Generate a professional cover letter for the following job application:

        Job Title: ${jobTitle}
        Company: ${companyName}
        Job Description: ${jobDescription}

        Candidate Information:
        Name: ${resumeData.fullName}
        Current Title: ${resumeData.title}
        Email: ${resumeData.email}
        Phone: ${resumeData.phone}
        Location: ${resumeData.location}
        Experience: ${resumeData.experience.map(exp => 
          `${exp.title} at ${exp.company} (${exp.startDate} - ${exp.endDate || 'Present'})`
        ).join(', ')}
        Skills: ${resumeData.skills.technical.join(', ')}
        Education: ${resumeData.education.map(edu => 
          `${edu.degree} in ${edu.field} from ${edu.school}`
        ).join(', ')}

        Requirements:
        1. Keep the tone professional but engaging
        2. Highlight relevant skills and experience that match the job requirements
        3. Show enthusiasm for the company and position
        4. Keep it concise (3-4 paragraphs)
        5. Include specific examples from the candidate's experience
        6. Address the job requirements directly
        7. End with a strong closing statement
        8. IMPORTANT: Use the exact values provided above - do not use placeholders like [Your Name] or [Your Email]
        9. Format Requirements:
           - Start with "Dear Hiring Manager"
           - Do not include any address headers or date
           - End with "Sincerely, [Full Name]"
           - Do not include contact information in the signature
           - Keep the content focused on the body paragraphs

        Generate a well-structured cover letter that follows these requirements.`
      )
    ];

    try {
      const response = await this.llm.invoke(messages);
      return response.content.toString().trim();
    } catch (error) {
      console.error('Error generating cover letter:', error);
      throw new Error('Failed to generate cover letter');
    }
  }
} 