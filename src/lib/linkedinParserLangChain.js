import { OpenAI } from '@langchain/openai';
import { StructuredOutputParser } from '@langchain/core/output_parsers';
import { PromptTemplate } from '@langchain/core/prompts';
import { z } from 'zod';

// Define the structure of the LinkedIn profile data
const linkedInProfileSchema = z.object({
  firstName: z.string(),
  lastName: z.string(),
  headline: z.string(),
  summary: z.string(),
  industryName: z.string(),
  locationName: z.string(),
  positions: z.array(z.object({
    title: z.string(),
    companyName: z.string(),
    location: z.string(),
    startDate: z.object({
      year: z.number(),
      month: z.number()
    }),
    endDate: z.object({
      year: z.number(),
      month: z.number()
    }).optional(),
    description: z.string()
  })),
  educations: z.array(z.object({
    schoolName: z.string(),
    degreeName: z.string(),
    fieldOfStudy: z.string(),
    startDate: z.object({
      year: z.number(),
      month: z.number()
    }),
    endDate: z.object({
      year: z.number(),
      month: z.number()
    }).optional(),
    activities: z.string()
  })),
  skills: z.array(z.string()),
  certifications: z.array(z.object({
    name: z.string(),
    authority: z.string(),
    licenseNumber: z.string(),
    startDate: z.object({
      year: z.number(),
      month: z.number()
    }).optional(),
    endDate: z.object({
      year: z.number(),
      month: z.number()
    }).optional()
  }))
});

/**
 * Parse LinkedIn profile HTML content using LangChain and OpenAI
 * @param htmlContent The HTML content of the LinkedIn profile page
 * @returns Structured LinkedIn profile data
 */
export async function parseLinkedInProfileWithLangChain(htmlContent) {
  if (!htmlContent) {
    return null;
  }
  
  try {
    // Check if API key is available
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      console.warn('OPENAI_API_KEY is not set. Cannot parse LinkedIn profile.');
      return null;
    }
    
    // Create a parser for structured output
    const parser = StructuredOutputParser.fromZodSchema(linkedInProfileSchema);
    const formatInstructions = parser.getFormatInstructions();
    
    // Create a prompt template
    const prompt = new PromptTemplate({
      template: `You are a professional LinkedIn profile parser. 
      Your task is to extract structured information from the HTML content of a LinkedIn profile page.
      
      HTML Content:
      {htmlContent}
      
      {formatInstructions}
      
      If you cannot find certain information, make a reasonable guess based on the available data.
      For dates, if only the year is available, use January (month=1) as the default month.
      For skills, extract both explicitly listed skills and skills mentioned in the experience descriptions.
      For certifications, extract as much detail as possible including the issuing authority and dates.
      
      Return the structured data according to the format instructions.`,
      inputVariables: ["htmlContent"],
      partialVariables: { formatInstructions }
    });
    
    // Create an OpenAI model instance
    const model = new OpenAI({
      modelName: "gpt-4",
      temperature: 0,
    });
    
    // Generate the prompt
    const input = await prompt.format({ htmlContent });
    
    // Call the model
    const response = await model.call(input);
    
    // Parse the response
    const parsedProfile = await parser.parse(response);
    
    return parsedProfile;
  } catch (error) {
    console.error('Error parsing LinkedIn profile with LangChain:', error);
    return null;
  }
}

/**
 * Fetch and parse a LinkedIn profile using LangChain
 * @param linkedInUrl The URL of the LinkedIn profile
 * @returns Structured LinkedIn profile data
 */
export async function fetchLinkedInProfileWithLangChain(linkedInUrl) {
  if (!linkedInUrl) {
    return null;
  }
  
  try {
    // In a real implementation, you would use a headless browser like Puppeteer
    // to fetch the HTML content of the LinkedIn profile page
    // For demonstration purposes, we'll use a mock HTML content
    
    console.log(`Would fetch LinkedIn profile HTML from: ${linkedInUrl}`);
    
    // Mock HTML content for demonstration
    const mockHtmlContent = `
    <html>
      <head>
        <title>Alex Tech | Senior Software Engineer at Tech Innovations Inc. | LinkedIn</title>
      </head>
      <body>
        <div class="profile-header">
          <h1>Alex Tech</h1>
          <h2>Senior Software Engineer at Tech Innovations Inc.</h2>
          <div class="location">San Francisco Bay Area</div>
          <div class="industry">Computer Software</div>
        </div>
        <div class="profile-summary">
          <p>Experienced software engineer with a passion for building scalable applications and solving complex problems.</p>
        </div>
        <div class="experience-section">
          <div class="experience-item">
            <h3>Senior Software Engineer</h3>
            <div class="company">Tech Innovations Inc.</div>
            <div class="location">San Francisco, CA</div>
            <div class="date">Jan 2020 - Present</div>
            <p>Developed and maintained scalable web applications using React, Node.js, and AWS. Led a team of 5 engineers.</p>
          </div>
          <div class="experience-item">
            <h3>Software Engineer</h3>
            <div class="company">Startup Solutions</div>
            <div class="location">San Francisco, CA</div>
            <div class="date">Mar 2018 - Dec 2019</div>
            <p>Built RESTful APIs and implemented frontend features using React and TypeScript.</p>
          </div>
        </div>
        <div class="education-section">
          <div class="education-item">
            <h3>University of California, Berkeley</h3>
            <div class="degree">Bachelor of Science, Computer Science</div>
            <div class="date">Sep 2014 - May 2018</div>
            <div class="activities">Computer Science Club, Hackathons</div>
          </div>
        </div>
        <div class="skills-section">
          <ul>
            <li>JavaScript</li>
            <li>React</li>
            <li>Node.js</li>
            <li>TypeScript</li>
            <li>GraphQL</li>
            <li>AWS</li>
            <li>Docker</li>
            <li>Kubernetes</li>
          </ul>
        </div>
        <div class="certifications-section">
          <div class="certification-item">
            <h3>AWS Certified Solutions Architect</h3>
            <div class="issuer">Amazon Web Services</div>
            <div class="date">Jun 2021</div>
            <div class="license">AWS-SA-12345</div>
          </div>
          <div class="certification-item">
            <h3>Professional Scrum Master I</h3>
            <div class="issuer">Scrum.org</div>
            <div class="date">Mar 2020</div>
            <div class="license">PSM-I-12345</div>
          </div>
        </div>
      </body>
    </html>
    `;
    
    // Parse the HTML content
    return await parseLinkedInProfileWithLangChain(mockHtmlContent);
  } catch (error) {
    console.error('Error fetching LinkedIn profile with LangChain:', error);
    return null;
  }
} 