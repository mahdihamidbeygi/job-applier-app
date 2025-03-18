import pdfParse from 'pdf-parse-fork';
import OpenAI from 'openai';
import crypto from 'crypto';

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Simple in-memory cache for parsed results
const parseCache = new Map<string, {
  result: ParsedResume;
  timestamp: number;
}>();

// Cache expiration time (24 hours)
const CACHE_EXPIRATION = 24 * 60 * 60 * 1000;

interface Publication {
  title: string;
  publisher: string;
  date: Date | null;
  description: string;
}

interface Certification {
  name: string;
  issuer: string;
  date: Date | null;
  url?: string;
}

interface DynamicSectionItem {
  title?: string;
  subtitle?: string;
  date?: Date | null;
  endDate?: Date | null;
  description?: string;
  url?: string;
  [key: string]: string | Date | null | undefined;
}

interface DynamicSection {
  type: string;
  title: string;
  items: DynamicSectionItem[];
}

interface ParsedResume {
  contactInfo: {
    name: string;
    email: string;
    phone: string;
    location: string;
    linkedInUrl?: string;
    githubUrl?: string;
  };
  summary: string;
  skills: string[];
  experience: {
    title: string;
    company: string;
    startDate: Date | null;
    endDate: Date | null;
    description: string;
  }[];
  education: {
    school: string;
    degree: string;
    field: string;
    startDate: Date | null;
    endDate: Date | null;
  }[];
  publications?: Publication[];
  certifications?: Certification[];
  additionalSections: DynamicSection[];
}

interface AIResponseExperience {
  title: string;
  company: string;
  startDate: string | null;
  endDate: string | null;
  description: string;
}

interface AIResponseEducation {
  school: string;
  degree: string;
  field: string;
  startDate: string | null;
  endDate: string | null;
}

interface AIResponsePublication {
  title: string;
  publisher: string;
  date: string | null;
  description: string;
}

interface AIResponseCertification {
  name: string;
  issuer: string;
  date: string | null;
  url?: string;
}

interface AIResponseDynamicSectionItem {
  title?: string;
  subtitle?: string;
  date?: string | null;
  endDate?: string | null;
  description?: string;
  url?: string;
  [key: string]: string | null | undefined;
}

interface AIResponseDynamicSection {
  type: string;
  title: string;
  items: AIResponseDynamicSectionItem[];
}

interface AIResponseData {
  contactInfo: {
    name: string;
    email: string;
    phone: string;
    location: string;
    linkedInUrl?: string;
    githubUrl?: string;
  };
  summary: string;
  skills: string[];
  experience: AIResponseExperience[];
  education: AIResponseEducation[];
  publications?: AIResponsePublication[];
  certifications?: AIResponseCertification[];
  additionalSections: AIResponseDynamicSection[];
}

function ensureBuffer(input: Buffer | ArrayBuffer | Uint8Array): Buffer {
  if (Buffer.isBuffer(input)) {
    return input;
  }
  if (input instanceof ArrayBuffer) {
    return Buffer.from(input);
  }
  if (input instanceof Uint8Array) {
    return Buffer.from(input);
  }
  throw new Error('Invalid input type: must be Buffer, ArrayBuffer, or Uint8Array');
}

function generateCacheKey(buffer: Buffer): string {
  return crypto.createHash('md5').update(buffer).digest('hex');
}

async function extractTextFromPDF(buffer: Buffer): Promise<string> {
  const data = await pdfParse(buffer, {
    max: 0,
    version: 'default'
  });
  
  if (!data || !data.text) {
    throw new Error('Failed to extract text from PDF');
  }
  
  return data.text;
}

async function parseWithAI(text: string): Promise<AIResponseData> {
  const template = {
    contactInfo: {
      name: "",
      email: "",
      phone: "",
      location: "",
      linkedInUrl: "",
      githubUrl: ""
    },
    summary: "",
    skills: [],
    experience: [{
      title: "",
      company: "",
      startDate: null,
      endDate: null,
      description: ""
    }],
    education: [{
      school: "",
      degree: "",
      field: "",
      startDate: null,
      endDate: null
    }],
    publications: [{
      title: "",
      publisher: "",
      date: null,
      description: ""
    }],
    certifications: [{
      name: "",
      issuer: "",
      date: null,
      url: ""
    }],
    additionalSections: [{
      type: "",
      title: "",
      items: [{
        title: "",
        subtitle: "",
        date: null,
        endDate: null,
        description: "",
        url: ""
      }]
    }]
  };

  const prompt = `Extract the following information from this resume and return it as a valid JSON object with no additional text or explanation.

The response must follow this JSON template structure, but you can add more sections under additionalSections if you find any other sections in the resume:
${JSON.stringify(template, null, 2)}

For LinkedIn and GitHub URLs:
1. Look for full URLs (e.g., "https://linkedin.com/in/username" or "https://github.com/username")
2. Look for text mentions (e.g., "linkedin.com/in/username" or "github.com/username")
3. Look for profile references (e.g., "LinkedIn: username" or "GitHub: username")
4. For LinkedIn, convert all URLs to format: "https://linkedin.com/in/username"
5. For GitHub, convert all URLs to format: "https://github.com/username"

For degree names, standardize the following formats:
1. Convert "MSc" or "M.Sc." to "Master of Science"
2. Convert "BSc" or "B.Sc." to "Bachelor of Science"
3. Convert "PhD" or "Ph.D." to "Doctor of Philosophy"
4. Convert "BA" or "B.A." to "Bachelor of Arts"
5. Convert "MA" or "M.A." to "Master of Arts"
6. Keep the field of study separate from the degree name

For any additional sections found in the resume:
1. Create a new section under additionalSections
2. Set an appropriate type (e.g., "publications", "certifications", "awards", etc.)
3. Give it a descriptive title
4. Extract all relevant information into the items array
5. Include dates where available in YYYY-MM-DD format
6. Include URLs if they exist

Resume text:
${text}`;

  const completion = await openai.chat.completions.create({
    model: "gpt-4",
    messages: [{
      role: "system",
      content: `You are a resume parser that extracts structured information from resumes. You must:
1. Return ONLY valid JSON without any additional text, markdown formatting, or explanation
2. Ensure the JSON structure exactly matches the provided template
3. Pay special attention to standardizing degree names (e.g., 'MSc' should become 'Master of Science')
4. Keep degree names separate from fields of study
5. Format all dates as YYYY-MM-DD
6. Never include any text outside the JSON structure
7. Ensure all JSON keys and values are properly quoted
8. Include all required fields from the template, even if empty
9. Use null for missing dates, empty string for missing text fields, and empty arrays for missing lists`
    }, {
      role: "user",
      content: prompt
    }],
    temperature: 0.1
  });

  if (!completion.choices[0].message.content) {
    throw new Error('No content in AI response');
  }

  try {
    const parsedData = JSON.parse(completion.choices[0].message.content.trim());
    
    // Validate the response structure
    if (!parsedData || typeof parsedData !== 'object') {
      throw new Error('Response is not an object');
    }

    if (!parsedData.contactInfo || typeof parsedData.contactInfo !== 'object') {
      console.warn('Missing or invalid contactInfo, using empty object');
      parsedData.contactInfo = template.contactInfo;
    }

    if (!Array.isArray(parsedData.skills)) {
      console.warn('Missing or invalid skills array, using empty array');
      parsedData.skills = [];
    }

    if (!Array.isArray(parsedData.experience)) {
      console.warn('Missing or invalid experience array, using empty array');
      parsedData.experience = [];
    }

    if (!Array.isArray(parsedData.education)) {
      console.warn('Missing or invalid education array, using empty array');
      parsedData.education = [];
    }

    if (!Array.isArray(parsedData.publications)) {
      console.warn('Missing or invalid publications array, using empty array');
      parsedData.publications = [];
    }

    if (!Array.isArray(parsedData.certifications)) {
      console.warn('Missing or invalid certifications array, using empty array');
      parsedData.certifications = [];
    }

    if (!Array.isArray(parsedData.additionalSections)) {
      console.warn('Missing or invalid additionalSections array, using empty array');
      parsedData.additionalSections = [];
    }

    return parsedData as AIResponseData;
  } catch (error) {
    console.error('Failed to parse AI response:', completion.choices[0].message.content);
    throw new Error(`Invalid JSON response from AI: ${error instanceof Error ? error.message : 'Unknown parsing error'}`);
  }
}

export async function parseResume(pdfBuffer: Buffer | ArrayBuffer | Uint8Array): Promise<ParsedResume> {
  try {
    console.log('Starting resume parsing...');
    
    // Convert input to Buffer
    const buffer = ensureBuffer(pdfBuffer);
    
    // Generate cache key
    const cacheKey = generateCacheKey(buffer);
    
    // Check cache
    const cached = parseCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_EXPIRATION) {
      console.log('Returning cached parse result');
      return cached.result;
    }
    
    // Extract text from PDF
    console.log('Extracting text from PDF...');
    const text = await extractTextFromPDF(buffer);
    console.log('Extracted text length:', text.length);
    
    // Parse with AI
    console.log('Parsing with AI...');
    const parsedData = await parseWithAI(text);
    
    // Process dates and format response
    const result = formatResponse(parsedData);
    
    // Cache the result
    parseCache.set(cacheKey, {
      result,
      timestamp: Date.now()
    });
    
    // Quality checks
    performQualityChecks(result);
    
    return result;
  } catch (error) {
    console.error('Error parsing resume:', error);
    const errorMessage = error instanceof Error 
      ? `${error.message}\n${error.stack}`
      : 'Unknown error during resume parsing';
    throw new Error(`Failed to parse resume: ${errorMessage}`);
  }
}

function formatResponse(parsedData: AIResponseData): ParsedResume {
  const processDate = (dateStr: string | null | undefined): Date | null => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? null : date;
  };

  // Ensure all required fields exist with defaults
  const defaultData = {
    contactInfo: {
      name: '',
      email: '',
      phone: '',
      location: '',
      linkedInUrl: '',
      githubUrl: ''
    },
    summary: '',
    skills: [],
    experience: [],
    education: [],
    publications: [],
    certifications: [],
    additionalSections: []
  };

  return {
    contactInfo: {
      name: parsedData?.contactInfo?.name || defaultData.contactInfo.name,
      email: parsedData?.contactInfo?.email || defaultData.contactInfo.email,
      phone: parsedData?.contactInfo?.phone || defaultData.contactInfo.phone,
      location: parsedData?.contactInfo?.location || defaultData.contactInfo.location,
      linkedInUrl: parsedData?.contactInfo?.linkedInUrl || defaultData.contactInfo.linkedInUrl,
      githubUrl: parsedData?.contactInfo?.githubUrl || defaultData.contactInfo.githubUrl
    },
    summary: parsedData?.summary || defaultData.summary,
    skills: Array.isArray(parsedData?.skills) ? parsedData.skills : defaultData.skills,
    experience: Array.isArray(parsedData?.experience) ? parsedData.experience.map(exp => ({
      title: exp?.title || 'Unknown Position',
      company: exp?.company || 'Unknown Company',
      startDate: processDate(exp?.startDate),
      endDate: processDate(exp?.endDate),
      description: exp?.description || ''
    })) : defaultData.experience,
    education: Array.isArray(parsedData?.education) ? parsedData.education.map(edu => ({
      school: edu?.school || 'Unknown Institution',
      degree: edu?.degree || '',
      field: edu?.field || '',
      startDate: processDate(edu?.startDate),
      endDate: processDate(edu?.endDate)
    })) : defaultData.education,
    publications: Array.isArray(parsedData?.publications) ? parsedData.publications.map(pub => ({
      title: pub?.title || '',
      publisher: pub?.publisher || '',
      date: processDate(pub?.date),
      description: pub?.description || ''
    })) : defaultData.publications,
    certifications: Array.isArray(parsedData?.certifications) ? parsedData.certifications.map(cert => ({
      name: cert?.name || '',
      issuer: cert?.issuer || '',
      date: processDate(cert?.date),
      url: cert?.url || ''
    })) : defaultData.certifications,
    additionalSections: Array.isArray(parsedData?.additionalSections) ? parsedData.additionalSections.map(section => ({
      type: section?.type || '',
      title: section?.title || '',
      items: Array.isArray(section?.items) ? section.items.map(item => ({
        ...item,
        date: processDate(item?.date),
        endDate: processDate(item?.endDate)
      })) : []
    })) : defaultData.additionalSections
  };
}

function performQualityChecks(result: ParsedResume): void {
  if (!result.contactInfo.email && !result.contactInfo.phone) {
    console.warn('Warning: No contact information was extracted from the resume');
  }
  if (!result.summary) {
    console.warn('Warning: No summary/objective was extracted from the resume');
  }
  if (result.skills.length === 0) {
    console.warn('Warning: No skills were extracted from the resume');
  }
  if (result.experience.length === 0) {
    console.warn('Warning: No work experience was extracted from the resume');
  }
  if (result.education.length === 0) {
    console.warn('Warning: No education history was extracted from the resume');
  }
  if (!result.contactInfo.linkedInUrl && !result.contactInfo.githubUrl) {
    console.warn('Warning: No LinkedIn or GitHub URLs were extracted from the resume');
  }
} 