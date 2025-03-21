import { ChatOpenAI } from '@langchain/openai';
import { PDFLoader } from '@langchain/community/document_loaders/fs/pdf';
import { RecursiveCharacterTextSplitter } from '@langchain/textsplitters';
import { OpenAIEmbeddings } from '@langchain/openai';
import { HumanMessage, SystemMessage, BaseMessage } from '@langchain/core/messages';

interface ResumeInfo {
  skills: {
    technical: string[];
    soft: string[];
  };
  workExperience: Array<{
    company: string;
    title: string;
    startDate: string;
    endDate: string;
    achievements: string[];
  }>;
  education: Array<{
    school: string;
    degree: string;
    startDate: string;
    endDate: string;
  }>;
  contactInformation: {
    name: string;
    email: string;
    phone?: string;
    location?: string;
  };
}

export class ResumeService {
  private llm: ChatOpenAI;
  private embeddings: OpenAIEmbeddings;

  constructor() {
    this.llm = new ChatOpenAI({
      modelName: 'gpt-4',
      temperature: 0.2,
    });
    this.embeddings = new OpenAIEmbeddings();
  }

  async parseResume(pdfPath: string): Promise<ResumeInfo> {
    // Load PDF
    const loader = new PDFLoader(pdfPath);
    const docs = await loader.load();

    // Split text into chunks
    const textSplitter = new RecursiveCharacterTextSplitter({
      chunkSize: 1000,
      chunkOverlap: 200,
    });
    await textSplitter.splitDocuments(docs);

    // Extract key information using LLM
    const messages: BaseMessage[] = [
      new SystemMessage(
        "You are a resume parser. Extract key information from resumes in a structured format."
      ),
      new HumanMessage(
        `Analyze the following resume section and extract key information in JSON format:
        - Skills (technical and soft skills)
        - Work Experience (company, title, dates, key achievements)
        - Education (school, degree, dates)
        - Contact Information
        
        Resume section:
        ${docs[0].pageContent}
        
        Return the information in a structured JSON format.`
      )
    ];

    const response = await this.llm.invoke(messages);
    return JSON.parse(response.content.toString());
  }

  async tailorResume(resumeInfo: ResumeInfo, jobDescription: string) {
    const messages: BaseMessage[] = [
      new SystemMessage(
        "You are a resume tailoring expert. Generate suggestions for customizing resumes."
      ),
      new HumanMessage(
        `Given the following resume information and job description, suggest modifications to tailor the resume:
        
        Resume: ${JSON.stringify(resumeInfo)}
        
        Job Description: ${jobDescription}
        
        Provide specific suggestions for:
        1. Skills to emphasize
        2. Experience highlights to focus on
        3. Achievements to showcase
        4. Keywords to include
        
        Return the suggestions in a structured JSON format.`
      )
    ];

    const response = await this.llm.invoke(messages);
    return JSON.parse(response.content.toString());
  }

  async matchJobToResume(resumeInfo: ResumeInfo, jobDescription: string) {
    const messages: BaseMessage[] = [
      new SystemMessage(
        "You are a job matching expert. Analyze compatibility between resumes and job descriptions."
      ),
      new HumanMessage(
        `Analyze the compatibility between the resume and job description:
        
        Resume: ${JSON.stringify(resumeInfo)}
        
        Job Description: ${jobDescription}
        
        Provide:
        1. Overall match score (0-100)
        2. Key matching skills
        3. Missing required skills
        4. Recommendations for improvement
        
        Return the analysis in a structured JSON format.`
      )
    ];

    const response = await this.llm.invoke(messages);
    return JSON.parse(response.content.toString());
  }
} 