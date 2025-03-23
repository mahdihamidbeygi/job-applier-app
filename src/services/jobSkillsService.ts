import { HumanMessage, SystemMessage, BaseMessage } from '@langchain/core/messages';
import { ResumeData } from '@/types/resume';
import { OllamaService } from './ollamaService';

interface JobSkills {
  technical: string[];
  soft: string[];
  required: string[];
  preferred: string[];
}

interface SkillMatch {
  matchingSkills: string[];
  missingSkills: string[];
  matchScore: number;
  recommendations: string[];
}

export class JobSkillsService {
  private llm: OllamaService;

  constructor() {
    this.llm = new OllamaService();
  }

  async extractSkills(jobDescription: string): Promise<JobSkills> {
    const messages: BaseMessage[] = [
      new SystemMessage(
        "You are a job skills analyzer. Extract and categorize skills from job descriptions. You must ALWAYS respond with valid JSON."
      ),
      new HumanMessage(
        `Analyze the following job description and extract skills. You MUST respond with a valid JSON object only, no other text.

        Job Description: ${jobDescription}
        
        The JSON object must have these exact fields:
        {
          "technical": string[], // Array of technical skills
          "soft": string[], // Array of soft skills
          "required": string[], // Array of required skills
          "preferred": string[] // Array of preferred skills
        }
        
        Example response:
        {
          "technical": ["JavaScript", "React", "Node.js"],
          "soft": ["Communication", "Leadership"],
          "required": ["5+ years experience", "Bachelor's degree"],
          "preferred": ["AWS", "TypeScript"]
        }
        
        Remember: Respond with ONLY the JSON object, no other text or explanation.`
      )
    ];

    let response;
    try {
      response = await this.llm.invoke(messages);
      const content = response.content.toString().trim();
      
      // Try to find JSON in the response if it's wrapped in other text
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      const jsonStr = jsonMatch ? jsonMatch[0] : content;
      
      const parsed = JSON.parse(jsonStr);
      
      // Validate the structure
      if (!parsed.technical || !parsed.soft || !parsed.required || !parsed.preferred) {
        throw new Error('Invalid response structure');
      }
      
      return parsed as JobSkills;
    } catch (error) {
      console.error('Error extracting skills:', error);
      console.error('Raw response:', response?.content.toString());
      throw new Error('Failed to extract skills from job description');
    }
  }

  async matchSkillsWithResume(
    jobSkills: JobSkills,
    resumeData: ResumeData
  ): Promise<SkillMatch> {
    const messages: BaseMessage[] = [
      new SystemMessage(
        "You are a skills matching expert. Analyze how well a candidate's skills match job requirements. You must ALWAYS respond with valid JSON."
      ),
      new HumanMessage(
        `Compare the following job skills with the candidate's resume. You MUST respond with a valid JSON object only, no other text.

        Job Skills:
        Technical: ${jobSkills.technical.join(', ')}
        Soft: ${jobSkills.soft.join(', ')}
        Required: ${jobSkills.required.join(', ')}
        Preferred: ${jobSkills.preferred.join(', ')}

        Candidate's Skills:
        Technical: ${resumeData.skills.technical.join(', ')}
        Soft: ${resumeData.skills.soft.join(', ')}
        Experience: ${resumeData.experience.map(exp => 
          `${exp.title} at ${exp.company} (${exp.startDate} - ${exp.endDate || 'Present'})`
        ).join(', ')}
        Education: ${resumeData.education.map(edu => 
          `${edu.degree} in ${edu.field} from ${edu.school}`
        ).join(', ')}

        The JSON object must have these exact fields:
        {
          "matchingSkills": string[], // Array of skills that match between job and candidate
          "missingSkills": string[], // Array of required skills that candidate lacks
          "matchScore": number, // Number between 0-100 indicating overall match
          "recommendations": string[] // Array of suggestions to improve match
        }
        
        Example response:
        {
          "matchingSkills": ["JavaScript", "React"],
          "missingSkills": ["AWS", "TypeScript"],
          "matchScore": 75,
          "recommendations": ["Consider learning AWS", "Add TypeScript to your skill set"]
        }
        
        Remember: Respond with ONLY the JSON object, no other text or explanation.`
      )
    ];

    let response;
    try {
      response = await this.llm.invoke(messages);
      const content = response.content.toString().trim();
      
      // Try to find JSON in the response if it's wrapped in other text
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      const jsonStr = jsonMatch ? jsonMatch[0] : content;
      
      const parsed = JSON.parse(jsonStr);
      
      // Validate the structure
      if (!parsed.matchingSkills || !parsed.missingSkills || 
          typeof parsed.matchScore !== 'number' || !parsed.recommendations) {
        throw new Error('Invalid response structure');
      }
      
      return parsed as SkillMatch;
    } catch (error) {
      console.error('Error matching skills:', error);
      console.error('Raw response:', response?.content.toString());
      throw new Error('Failed to match skills with resume');
    }
  }

  async generateTailoredResume(
    resumeData: ResumeData,
    jobSkills: JobSkills,
    skillMatch: SkillMatch
  ): Promise<ResumeData> {
    const messages: BaseMessage[] = [
      new SystemMessage(
        "You are a resume tailoring expert. Optimize resumes to highlight relevant skills and experience. You must ALWAYS respond with valid JSON."
      ),
      new HumanMessage(
        `Tailor the following resume to better match the job requirements. You MUST respond with a valid JSON object only, no other text.

        Current Resume: ${JSON.stringify(resumeData)}

        Job Skills:
        Technical: ${jobSkills.technical.join(', ')}
        Soft: ${jobSkills.soft.join(', ')}
        Required: ${jobSkills.required.join(', ')}
        Preferred: ${jobSkills.preferred.join(', ')}

        Skill Match Analysis:
        Matching Skills: ${skillMatch.matchingSkills.join(', ')}
        Missing Skills: ${skillMatch.missingSkills.join(', ')}
        Match Score: ${skillMatch.matchScore}
        Recommendations: ${skillMatch.recommendations.join(', ')}

        Return a tailored version of the resume in the same JSON format as the input, with these optimizations:
        1. Reorder skills to highlight matching ones first
        2. Enhance experience descriptions to emphasize relevant achievements
        3. Add keywords from job requirements
        4. Optimize education section to highlight relevant qualifications
        5. Add any missing required skills as "Learning" or "In Progress"
        6. Emphasize transferable skills that could substitute for missing required skills
        
        The response must maintain the exact same structure as the input ResumeData, just with optimized content.
        Remember: Respond with ONLY the JSON object, no other text or explanation.`
      )
    ];

    let response;
    try {
      response = await this.llm.invoke(messages);
      const content = response.content.toString().trim();
      
      // Try to find JSON in the response if it's wrapped in other text
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      const jsonStr = jsonMatch ? jsonMatch[0] : content;
      
      const parsed = JSON.parse(jsonStr);
      
      // Validate the structure matches ResumeData
      if (!parsed.fullName || !parsed.title || !parsed.skills || 
          !parsed.experience || !parsed.education) {
        throw new Error('Invalid response structure');
      }
      
      return parsed as ResumeData;
    } catch (error) {
      console.error('Error tailoring resume:', error);
      console.error('Raw response:', response?.content.toString());
      throw new Error('Failed to tailor resume');
    }
  }

  async generateTailoredCoverLetter(
    resumeData: ResumeData,
    jobSkills: JobSkills,
    skillMatch: SkillMatch,
    jobTitle: string,
    companyName: string
  ): Promise<string> {
    const messages: BaseMessage[] = [
      new SystemMessage(
        "You are a cover letter tailoring expert. Generate compelling cover letters that highlight relevant skills and experience."
      ),
      new HumanMessage(
        `Generate a tailored cover letter for the following job application:

        Job Title: ${jobTitle}
        Company: ${companyName}

        Job Skills:
        Technical: ${jobSkills.technical.join(', ')}
        Soft: ${jobSkills.soft.join(', ')}
        Required: ${jobSkills.required.join(', ')}
        Preferred: ${jobSkills.preferred.join(', ')}

        Candidate Information:
        Name: ${resumeData.fullName}
        Current Title: ${resumeData.title}
        Experience: ${resumeData.experience.map(exp => 
          `${exp.title} at ${exp.company} (${exp.startDate} - ${exp.endDate || 'Present'})`
        ).join(', ')}
        Skills: ${resumeData.skills.technical.join(', ')}
        Education: ${resumeData.education.map(edu => 
          `${edu.degree} in ${edu.field} from ${edu.school}`
        ).join(', ')}

        Skill Match Analysis:
        Matching Skills: ${skillMatch.matchingSkills.join(', ')}
        Missing Skills: ${skillMatch.missingSkills.join(', ')}
        Match Score: ${skillMatch.matchScore}
        Recommendations: ${skillMatch.recommendations.join(', ')}

        Requirements:
        1. Keep the tone professional but engaging
        2. Highlight relevant skills and experience that match the job requirements
        3. Show enthusiasm for the company and position
        4. Keep it concise (3-4 paragraphs)
        5. Include specific examples from the candidate's experience
        6. Address the job requirements directly
        7. End with a strong closing statement
        8. For any missing required skills, explain how your existing skills or experience can compensate
        9. Mention your willingness to learn and adapt to new technologies
        10. Emphasize transferable skills that could be valuable in this role

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