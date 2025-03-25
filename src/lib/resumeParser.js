// Server-side only
if (typeof window !== 'undefined') {
  throw new Error('This module can only be used on the server side');
}

import pdfParse from 'pdf-parse-fork';
import { ChatOpenAI } from '@langchain/openai';
import crypto from 'crypto';

// Initialize OpenAI client
const llm = new ChatOpenAI({
  modelName: 'gpt-4',
  temperature: 0.1,
});

// Simple in-memory cache for parsed results
const parseCache = new Map();

// Cache expiration time (24 hours)
const CACHE_EXPIRATION = 24 * 60 * 60 * 1000;

// Maximum file size (10MB)
const MAX_FILE_SIZE = 10 * 1024 * 1024;

function ensureBuffer(input) {
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

function generateCacheKey(buffer) {
  return crypto.createHash('md5').update(buffer).digest('hex');
}

function cleanGluedWords(text) {
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

async function extractTextFromPDF(buffer) {
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

async function parseWithAI(text) {
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
      description: "",
      location: null,
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

  const prompt = `Parse the following resume text and extract structured information. Return a JSON object with the following structure:

${JSON.stringify(template, null, 2)}

Resume text:
${text}

Rules:
1. Extract all contact information including name, email, phone, location, and social media URLs
2. Create a concise professional summary
3. Extract all skills mentioned
4. Parse work experience with dates, titles, companies, and descriptions
5. Parse education history with schools, degrees, and dates
6. Extract any publications or certifications
7. Identify and parse any additional sections
8. Dates should be in ISO format (YYYY-MM-DD) or null if not found
9. All text fields should be properly formatted and cleaned
10. Maintain the exact structure of the template

Return only the JSON object, no additional text.`;

  try {
    const response = await llm.invoke([
      new SystemMessage("You are a professional resume parser. Extract structured information from resume text and return it in a specific JSON format."),
      new HumanMessage(prompt)
    ]);

    const content = typeof response.content === 'string' ? response.content : '';
    const parsedData = JSON.parse(content);
    return parsedData;
  } catch (error) {
    console.error('Error parsing resume with AI:', error);
    throw new Error('Failed to parse resume with AI');
  }
}

function mergeChunkResults(chunks) {
  if (!chunks || chunks.length === 0) {
    return null;
  }

  // Initialize merged result with the first chunk
  const merged = { ...chunks[0] };

  // Merge contact info (take the most complete)
  chunks.forEach(chunk => {
    if (chunk.contactInfo) {
      Object.keys(chunk.contactInfo).forEach(key => {
        if (!merged.contactInfo[key] && chunk.contactInfo[key]) {
          merged.contactInfo[key] = chunk.contactInfo[key];
        }
      });
    }
  });

  // Merge skills (unique)
  const skillsSet = new Set();
  chunks.forEach(chunk => {
    if (chunk.skills) {
      chunk.skills.forEach(skill => skillsSet.add(skill));
    }
  });
  merged.skills = Array.from(skillsSet);

  // Merge experience (unique by title and company)
  const experienceMap = new Map();
  chunks.forEach(chunk => {
    if (chunk.experience) {
      chunk.experience.forEach(exp => {
        const key = `${exp.title}-${exp.company}`;
        if (!experienceMap.has(key) || 
            (exp.description && exp.description.length > (experienceMap.get(key).description?.length || 0))) {
          experienceMap.set(key, exp);
        }
      });
    }
  });
  merged.experience = Array.from(experienceMap.values());

  // Merge education (unique by school and degree)
  const educationMap = new Map();
  chunks.forEach(chunk => {
    if (chunk.education) {
      chunk.education.forEach(edu => {
        const key = `${edu.school}-${edu.degree}`;
        if (!educationMap.has(key)) {
          educationMap.set(key, edu);
        }
      });
    }
  });
  merged.education = Array.from(educationMap.values());

  // Merge publications (unique by title)
  const publicationsMap = new Map();
  chunks.forEach(chunk => {
    if (chunk.publications) {
      chunk.publications.forEach(pub => {
        if (!publicationsMap.has(pub.title)) {
          publicationsMap.set(pub.title, pub);
        }
      });
    }
  });
  merged.publications = Array.from(publicationsMap.values());

  // Merge certifications (unique by name)
  const certificationsMap = new Map();
  chunks.forEach(chunk => {
    if (chunk.certifications) {
      chunk.certifications.forEach(cert => {
        if (!certificationsMap.has(cert.name)) {
          certificationsMap.set(cert.name, cert);
        }
      });
    }
  });
  merged.certifications = Array.from(certificationsMap.values());

  // Merge additional sections (unique by type and title)
  const sectionsMap = new Map();
  chunks.forEach(chunk => {
    if (chunk.additionalSections) {
      chunk.additionalSections.forEach(section => {
        const key = `${section.type}-${section.title}`;
        if (!sectionsMap.has(key)) {
          sectionsMap.set(key, section);
        } else {
          // Merge items within the same section
          const existingSection = sectionsMap.get(key);
          const itemsMap = new Map();
          [...existingSection.items, ...section.items].forEach(item => {
            const itemKey = item.title || item.subtitle || JSON.stringify(item);
            if (!itemsMap.has(itemKey)) {
              itemsMap.set(itemKey, item);
            }
          });
          existingSection.items = Array.from(itemsMap.values());
        }
      });
    }
  });
  merged.additionalSections = Array.from(sectionsMap.values());

  return merged;
}

function validatePhoneNumber(phone) {
  if (!phone) return '';
  // Remove all non-numeric characters
  const cleaned = phone.replace(/\D/g, '');
  // Format as (XXX) XXX-XXXX
  return cleaned.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
}

export async function parseResume(pdfBuffer) {
  try {
    // Ensure input is a Buffer
    const buffer = ensureBuffer(pdfBuffer);

    // Check file size
    if (buffer.length > MAX_FILE_SIZE) {
      throw new Error(`File size exceeds maximum limit of ${MAX_FILE_SIZE / (1024 * 1024)}MB`);
    }

    // Generate cache key
    const cacheKey = generateCacheKey(buffer);

    // Check cache
    const cachedResult = parseCache.get(cacheKey);
    if (cachedResult && Date.now() - cachedResult.timestamp < CACHE_EXPIRATION) {
      return cachedResult.result;
    }

    // Extract text from PDF
    const text = await extractTextFromPDF(buffer);

    // Split text into chunks if needed (GPT-4 has a token limit)
    const chunks = [];
    const chunkSize = 4000; // Approximate characters per chunk
    for (let i = 0; i < text.length; i += chunkSize) {
      chunks.push(text.slice(i, i + chunkSize));
    }

    // Parse each chunk
    const chunkResults = await Promise.all(
      chunks.map(chunk => parseWithAI(chunk))
    );

    // Merge results
    const mergedResult = mergeChunkResults(chunkResults);

    if (!mergedResult) {
      throw new Error('Failed to parse resume');
    }

    // Format the response
    const formattedResult = formatResponse(mergedResult);

    // Perform quality checks
    performQualityChecks(formattedResult);

    // Cache the result
    parseCache.set(cacheKey, {
      result: formattedResult,
      timestamp: Date.now()
    });

    return formattedResult;
  } catch (error) {
    console.error('Error parsing resume:', error);
    throw error;
  }
}

function formatResponse(parsedData) {
  const processDate = (dateStr) => {
    if (!dateStr) return null;
    try {
      const date = new Date(dateStr);
      return isNaN(date.getTime()) ? null : date;
    } catch (error) {
      return null;
    }
  };

  return {
    contactInfo: {
      name: parsedData.contactInfo?.name || '',
      email: parsedData.contactInfo?.email || '',
      phone: validatePhoneNumber(parsedData.contactInfo?.phone),
      location: parsedData.contactInfo?.location || '',
      linkedInUrl: parsedData.contactInfo?.linkedInUrl || '',
      githubUrl: parsedData.contactInfo?.githubUrl || ''
    },
    summary: parsedData.summary || '',
    skills: parsedData.skills || [],
    experience: (parsedData.experience || []).map(exp => ({
      title: exp.title || '',
      company: exp.company || '',
      location: exp.location || null,
      startDate: processDate(exp.startDate),
      endDate: processDate(exp.endDate),
      description: exp.description || ''
    })),
    education: (parsedData.education || []).map(edu => ({
      school: edu.school || '',
      degree: edu.degree || '',
      field: edu.field || '',
      startDate: processDate(edu.startDate),
      endDate: processDate(edu.endDate)
    })),
    publications: (parsedData.publications || []).map(pub => ({
      title: pub.title || '',
      publisher: pub.publisher || '',
      date: processDate(pub.date),
      description: pub.description || ''
    })),
    certifications: (parsedData.certifications || []).map(cert => ({
      name: cert.name || '',
      issuer: cert.issuer || '',
      date: processDate(cert.date),
      url: cert.url || ''
    })),
    additionalSections: (parsedData.additionalSections || []).map(section => ({
      type: section.type || '',
      title: section.title || '',
      items: (section.items || []).map(item => ({
        title: item.title || '',
        subtitle: item.subtitle || '',
        date: processDate(item.date),
        endDate: processDate(item.endDate),
        description: item.description || '',
        url: item.url || ''
      }))
    }))
  };
}

function performQualityChecks(result) {
  // Check required fields
  if (!result.contactInfo.name) {
    throw new Error('Missing required field: name');
  }
  if (!result.contactInfo.email) {
    throw new Error('Missing required field: email');
  }

  // Validate email format
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(result.contactInfo.email)) {
    throw new Error('Invalid email format');
  }

  // Check for minimum content
  if (!result.summary) {
    throw new Error('Missing required field: summary');
  }
  if (!result.skills.length) {
    throw new Error('Missing required field: skills');
  }
  if (!result.experience.length) {
    throw new Error('Missing required field: experience');
  }
  if (!result.education.length) {
    throw new Error('Missing required field: education');
  }
}

export function parseBulletPoints(text) {
  if (!text) return [];
  
  // Split by common bullet point characters
  const bulletPoints = text.split(/[•\-\*]/)
    .map(point => point.trim())
    .filter(point => point.length > 0);
  
  // If no bullet points found, try splitting by newlines
  if (bulletPoints.length === 0) {
    return text.split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0);
  }
  
  return bulletPoints;
}

export function parseJobDescription(description) {
  if (!description) return [];
  
  // Split into sections based on common headers
  const sections = description.split(/(?=\b(?:Requirements|Qualifications|Responsibilities|Skills|Experience|Education|About|Overview)\b)/i);
  
  // Extract bullet points from each section
  const bulletPoints = sections.flatMap(section => {
    // Remove section headers
    const content = section.replace(/^(?:Requirements|Qualifications|Responsibilities|Skills|Experience|Education|About|Overview):/i, '').trim();
    
    // Parse bullet points
    return parseBulletPoints(content);
  });
  
  return bulletPoints;
} 