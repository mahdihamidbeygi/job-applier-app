import { OpenAI } from 'langchain/llms/openai';
import { PDFLoader } from 'langchain/document_loaders/fs/pdf';
import { RecursiveCharacterTextSplitter } from 'langchain/text_splitter';
import { PineconeStore } from 'langchain/vectorstores/pinecone';
import { OpenAIEmbeddings } from 'langchain/embeddings/openai';
import { PineconeClient } from '@pinecone-database/pinecone';

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
  private llm: OpenAI;
  private embeddings: OpenAIEmbeddings;
  private pinecone: PineconeClient;

  constructor() {
    this.llm = new OpenAI({
      modelName: 'gpt-4',
      temperature: 0.2,
    });
    this.embeddings = new OpenAIEmbeddings();
    this.pinecone = new PineconeClient();
  }

  async initialize() {
    await this.pinecone.init({
      environment: process.env.PINECONE_ENVIRONMENT!,
      apiKey: process.env.PINECONE_API_KEY!,
    });
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
    const splitDocs = await textSplitter.splitDocuments(docs);

    // Extract key information using LLM
    const prompt = `
      Analyze the following resume section and extract key information in JSON format:
      - Skills (technical and soft skills)
      - Work Experience (company, title, dates, key achievements)
      - Education (school, degree, dates)
      - Contact Information
      
      Resume section:
      {text}
      
      Return the information in a structured JSON format.
    `;

    const resumeInfo = await this.llm.call(prompt.replace('{text}', docs[0].pageContent));

    // Store vector embeddings
    const pineconeIndex = this.pinecone.Index('resumes');
    await PineconeStore.fromDocuments(splitDocs, this.embeddings, {
      pineconeIndex,
      namespace: 'resume-sections',
    });

    return JSON.parse(resumeInfo);
  }

  async tailorResume(resumeInfo: ResumeInfo, jobDescription: string) {
    const prompt = `
      Given the following resume information and job description, suggest modifications to tailor the resume:
      
      Resume: ${JSON.stringify(resumeInfo)}
      
      Job Description: ${jobDescription}
      
      Provide specific suggestions for:
      1. Skills to emphasize
      2. Experience highlights to focus on
      3. Achievements to showcase
      4. Keywords to include
      
      Return the suggestions in a structured JSON format.
    `;

    const suggestions = await this.llm.call(prompt);
    return JSON.parse(suggestions);
  }

  async matchJobToResume(resumeInfo: ResumeInfo, jobDescription: string) {
    const prompt = `
      Analyze the compatibility between the resume and job description:
      
      Resume: ${JSON.stringify(resumeInfo)}
      
      Job Description: ${jobDescription}
      
      Provide:
      1. Overall match score (0-100)
      2. Key matching skills
      3. Missing required skills
      4. Recommendations for improvement
      
      Return the analysis in a structured JSON format.
    `;

    const analysis = await this.llm.call(prompt);
    return JSON.parse(analysis);
  }
} 