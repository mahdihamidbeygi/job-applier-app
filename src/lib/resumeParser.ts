// Server-side only
if (typeof window !== 'undefined') {
  throw new Error('This module can only be used on the server side');
}

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

// Maximum file size (10MB)
const MAX_FILE_SIZE = 10 * 1024 * 1024;

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

function cleanGluedWords(text: string): string {
  // Optimized regex patterns
  const patterns = [
    /([a-z])([A-Z])/g,  // camelCase
    /([a-zA-Z])(\d)/g,  // numbers
    /([a-zA-Z])([^a-zA-Z\s])/g,  // special chars
    /([a-zA-Z])([-_])/g,  // hyphens/underscores
    /[\u2028\u2029]/g,  // line separators
    /[^\x00-\x7F]/g,  // non-ASCII
    /\s+/g  // multiple spaces
  ];

  return patterns.reduce((text, pattern) => 
    text.replace(pattern, '$1 $2'), 
    text
  ).trim();
}

async function extractTextFromPDF(buffer: Buffer): Promise<string> {
  try {
    // Parse PDF using pdf-parse-fork
    const data = await pdfParse(buffer, {
      max: 0, // no limit on pages
      version: 'v2.0.550'
    });
    
    if (!data || !data.text) {
      throw new Error('Failed to extract text from PDF');
    }
    
    return cleanGluedWords(data.text);
  } catch (error) {
    console.error('Error extracting text from PDF:', error);
    throw new Error('Failed to extract text from PDF');
  }
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

  // Split text into sections based on common resume section headers
  const sections = text.split(/(?=^(?:Experience|Work Experience|Employment History|Professional Experience|Education|Skills|Summary|Objective|Certifications|Publications|Projects|Languages|Technical Skills|Core Competencies|Professional Summary))/m);
  
  // Process each section in parallel
  const sectionResults = await Promise.all(
    sections.map(async (section) => {
      if (!section.trim()) return null;

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
9. Use null for missing dates, empty string for missing text fields, and empty arrays for missing lists
10. For experience sections, extract ALL work experiences, not just the first one
11. Preserve the chronological order of experiences
12. If a section contains multiple experiences, parse each one separately
13. For job descriptions:
    - Preserve bullet points and their formatting
    - Keep each bullet point as a separate line
    - Maintain the original structure of the description
    - Don't combine bullet points into paragraphs
14. When you see bullet points in job descriptions:
    - Keep the bullet point characters (•, -, *, etc.)
    - Preserve the indentation and formatting
    - Keep each point on its own line
    - Don't merge them into paragraphs`
        }, {
          role: "user",
          content: `Extract information from this resume section:
${section}

Return it as a valid JSON object following this template:
${JSON.stringify(template, null, 2)}`
        }],
        temperature: 0.1
      });

      if (!completion.choices[0].message.content) {
        throw new Error('No content in AI response');
      }

      return JSON.parse(completion.choices[0].message.content.trim());
    })
  );

  // Filter out null results and merge
  const validResults = sectionResults.filter((result): result is AIResponseData => result !== null);
  return mergeChunkResults(validResults);
}

function mergeChunkResults(chunks: AIResponseData[]): AIResponseData {
  const merged: AIResponseData = {
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

  // Merge arrays and deduplicate
  chunks.forEach(chunk => {
    if (chunk.contactInfo) {
      merged.contactInfo = {
        ...merged.contactInfo,
        ...chunk.contactInfo
      };
    }
    if (chunk.summary) {
      merged.summary += (merged.summary ? ' ' : '') + chunk.summary;
    }
    if (Array.isArray(chunk.skills)) {
      merged.skills = [...new Set([...merged.skills, ...chunk.skills])];
    }
    if (Array.isArray(chunk.experience)) {
      // Sort experiences by date and merge
      const allExperiences = [...merged.experience, ...chunk.experience];
      merged.experience = allExperiences.sort((a, b) => {
        const dateA = a.startDate ? new Date(a.startDate).getTime() : 0;
        const dateB = b.startDate ? new Date(b.startDate).getTime() : 0;
        return dateB - dateA; // Most recent first
      });
    }
    if (Array.isArray(chunk.education)) {
      merged.education = [...merged.education, ...chunk.education];
    }
    if (Array.isArray(chunk.publications)) {
      merged.publications = [...(merged.publications || []), ...chunk.publications];
    }
    if (Array.isArray(chunk.certifications)) {
      merged.certifications = [...(merged.certifications || []), ...chunk.certifications];
    }
    if (Array.isArray(chunk.additionalSections)) {
      merged.additionalSections = [...merged.additionalSections, ...chunk.additionalSections];
    }
  });

  return merged;
}

export async function parseResume(pdfBuffer: Buffer | ArrayBuffer | Uint8Array): Promise<ParsedResume> {
  try {
    console.log('Starting resume parsing...');
    
    // Convert input to Buffer
    const buffer = ensureBuffer(pdfBuffer);
    
    // Validate file size
    if (buffer.length > MAX_FILE_SIZE) {
      throw new Error(`File size exceeds ${MAX_FILE_SIZE / (1024 * 1024)}MB limit`);
    }
    
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
    experience: Array.isArray(parsedData?.experience) ? parsedData.experience.map(exp => {
      // Parse the job description to handle bullet points
      const description = exp?.description || '';
      const parsedDescription = parseJobDescription(description);
      
      return {
        title: exp?.title || 'Unknown Position',
        company: exp?.company || 'Unknown Company',
        startDate: processDate(exp?.startDate),
        endDate: processDate(exp?.endDate),
        description: parsedDescription.join('\n') // Join bullet points with newlines
      };
    }) : defaultData.experience,
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

export function parseBulletPoints(text: string): string[] {
  // Remove any existing bullet points or numbers
  text = text.replace(/^[\s•*\-–—]\s*/gm, '')  // Remove bullet points
    .replace(/^\d+\.\s*/gm, '')  // Remove numbered lists
    .replace(/^[a-z]\)\s*/gm, '')  // Remove lettered lists
    .replace(/^\([a-z]\)\s*/gm, '')  // Remove parenthesized letters
    .replace(/^\[[a-z]\]\s*/gm, '');  // Remove bracketed letters

  // Split by common bullet point indicators
  const lines = text.split(/\n/);
  const bulletPoints: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    // Skip lines that are too short or look like headers
    if (trimmed.length < 10 || /^[A-Z\s]{10,}$/.test(trimmed)) continue;

    // Skip lines that are just punctuation or special characters
    if (/^[\s\p{P}]+$/u.test(trimmed)) continue;

    // Skip lines that are just numbers or dates
    if (/^\d+$/.test(trimmed) || /^\d{1,2}\/\d{1,2}\/\d{2,4}$/.test(trimmed)) continue;

    // Clean up the bullet point
    const cleaned = trimmed
      .replace(/^[\s•*\-–—]\s*/, '')  // Remove leading bullet points
      .replace(/^[\d\.\)\]]+\s*/, '')  // Remove leading numbers or letters
      .replace(/\s+/g, ' ')  // Normalize whitespace
      .trim();

    if (cleaned && cleaned.length >= 10) {
      bulletPoints.push(cleaned);
    }
  }

  return bulletPoints;
}

export function parseJobDescription(description: string): string[] {
  if (!description) return [];

  // First, try to detect if it's a bullet-pointed list
  const hasBulletPoints = /^[\s•*\-–—]\s/m.test(description) || 
                         /^\d+\.\s/m.test(description) || 
                         /^[a-z]\)\s/m.test(description);

  if (hasBulletPoints) {
    // Split by bullet points and clean each point
    return description
      .split(/\n/)
      .map(line => {
        // Remove bullet points and numbers
        const cleaned = line
          .replace(/^[\s•*\-–—]\s*/, '')  // Remove bullet points
          .replace(/^\d+\.\s*/, '')        // Remove numbered lists
          .replace(/^[a-z]\)\s*/, '')      // Remove lettered lists
          .replace(/^\([a-z]\)\s*/, '')    // Remove parenthesized letters
          .replace(/^\[[a-z]\]\s*/, '')    // Remove bracketed letters
          .replace(/\s+/g, ' ')            // Normalize whitespace
          .trim();

        // Skip empty lines, headers, and short lines
        if (!cleaned || 
            cleaned.length < 10 || 
            /^[A-Z\s]{10,}$/.test(cleaned) || 
            /^[\s\p{P}]+$/u.test(cleaned) || 
            /^\d+$/.test(cleaned) || 
            /^\d{1,2}\/\d{1,2}\/\d{2,4}$/.test(cleaned)) {
          return null;
        }

        return cleaned;
      })
      .filter((point): point is string => point !== null);
  } else {
    // If it's a paragraph, split by sentences and clean each one
    return description
      .split(/[.!?]+(?:\s+|$)/)  // Split by sentence endings
      .map(sentence => {
        const cleaned = sentence
          .replace(/\s+/g, ' ')  // Normalize whitespace
          .trim();

        // Skip empty sentences and very short ones
        if (!cleaned || cleaned.length < 10) return null;

        return cleaned;
      })
      .filter((sentence): sentence is string => sentence !== null);
  }
} 