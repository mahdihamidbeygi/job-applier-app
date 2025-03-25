import { jsPDF } from 'jspdf';
import { ChatOllama } from '@langchain/community/chat_models/ollama';
import { SystemMessage, HumanMessage } from '@langchain/core/messages';

export async function convertMarkdownToPDF(markdown, data) {
  return new Promise(async (resolve, reject) => {
    try {
      const doc = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
      });

      // Set initial position
      let y = 15;
      const leftMargin = 5;
      const rightMargin = 205;
      const contentWidth = rightMargin - leftMargin - 2;

      // Helper function to format date
      const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toISOString().substring(0, 7); // Gets YYYY-MM format
      };

      // Helper function to add text and return new Y position
      const addText = (text, fontSize, options = {}) => {
        doc.setFontSize(fontSize);
        if (options.isBold) {
          doc.setFont('helvetica', 'bold');
        } else {
          doc.setFont('helvetica', 'normal');
        }
        
        // Check if we need a new page
        if (y > 280) {
          doc.addPage();
          y = 15;
        }

        const x = options.x !== undefined ? options.x :
                 options.isCenter ? (rightMargin + leftMargin) / 2 : 
                 options.indent ? leftMargin + options.indent : 
                 leftMargin;

        if (options.isCenter) {
          doc.text(text, x, y, { align: 'center' });
        } else if (options.rightAlign) {
          doc.text(text, rightMargin, y, { align: 'right' });
        } else {
          const effectiveWidth = options.maxWidth || contentWidth - (options.indent || 0);
          const lines = doc.splitTextToSize(text, effectiveWidth);
          
          if (options.justify && lines.length > 1) {
            // Only justify multi-line paragraphs
            lines.forEach((line, index) => {
              if (index < lines.length - 1) { // Don't justify the last line
                doc.text(line, x, y, { align: 'justify', maxWidth: effectiveWidth });
              } else {
                doc.text(line, x, y);
              }
              y += fontSize / 2;
            });
            y -= fontSize / 2; // Adjust for the last increment
          } else {
            doc.text(lines, x, y);
            y += (lines.length - 1) * (fontSize / 2);
          }
        }

        y += fontSize / 2;
        return y;
      };

      // Add section title with consistent formatting
      const addSectionTitle = (title) => {
        y += 3; // Increased space before section titles to separate sections
        y = addText(title.toUpperCase(), 14, { isBold: true });
        y += 1;
        return y;
      };      

      // Get skills from Ollama
      const llm = new ChatOllama({
        model: "phi4",
        temperature: 0.6,
      });

      const skillsPrompt = `Extract exactly 6 most relevant technical skills following these rules:

1. Skills must be:
   - Technical and specific (e.g., "Python" not "Programming")
   - Found in both job description and candidate experience
   - Current and in-demand
   - Single words or short phrases (max 2 words)

2. Format:
   - Return ONLY the skills
   - Separate with commas
   - No numbering or bullets
   - No explanations

Job Description:
${data.jobDescription}

Candidate Experience:
${data.experience.map(exp => exp.title + ': ' + exp.description).join('\n')}

Return exactly 6 skills that best match the job requirements.`;
      
      const messages = [
        new SystemMessage(
          "you are a perfect resume writer, extract six keyword skills from the resume based on the job description, skills should be separated by comma."
        ),
        new HumanMessage(skillsPrompt)
      ];

      const skillsCompletion = await llm.invoke(messages);
      
      // Get the content as string and handle potential complex message content
      const skillsContent = typeof skillsCompletion.content === 'string' 
        ? skillsCompletion.content 
        : '';
      
      // Use skills from Ollama or fallback to resume data
      const skills = data.skills.technical.slice(0, 3).join(", ");
      // Ensure skills are always in array format
      const skillsArray = skillsContent 
        ? skillsContent.split(',').map(s => s.trim()) 
        : data.skills.technical;
      
      // Header section
      y = addText(data.fullName, 24, { isBold: true, isCenter: true });
      
      // Use just one professional title
      let professionalTitle = data.title;
      if (!professionalTitle || professionalTitle.trim() === '') {
        if (data.experience && data.experience.length > 0) {
          professionalTitle = data.experience[0].title;
        } else {
          professionalTitle = "Data Scientist";
        }
      }
      // Only use the first part if there are multiple titles separated by |
      if (professionalTitle.includes('|')) {
        professionalTitle = professionalTitle.split('|')[0].trim();
      }
      // Only use the first part if there are multiple titles separated by &
      if (professionalTitle.includes('&')) {
        professionalTitle = professionalTitle.split('&')[0].trim();
      }
      
      y = addText("Data Scientist", 16, { isCenter: true });
      y += 1;
      
      // Contact info - centered and compact
      const contactInfo = `${data.email} | ${data.phone || ''} | ${data.location || ''}`;
      const socialInfo = `${data.linkedin || ''} | ${data.github || ''}`;
      y = addText(contactInfo, 10, { isCenter: true });
      y = addText(socialInfo, 10, { isCenter: true });
      y += 2; // Added space after header section

      // Professional Summary - more concise version
      const yearsOfExperience = data.experience && data.experience.length > 0 
        ? Math.max(...data.experience.map(exp => {
            const start = new Date(exp.startDate).getFullYear();
            const end = exp.endDate ? new Date(exp.endDate).getFullYear() : new Date().getFullYear();
            return end - start;
          }))
        : 5;
      
      // Generate summary using Ollama
      const summaryPrompt = `Write a professional summary for a resume. Return ONLY the summary text, no explanations.

Rules:
1. Length: 2-3 sentences only
2. Format: Start with role and years of experience
3. Content:
   - Include key skills from job description
   - Match experience level from job requirements
   - Use action verbs (leverage, drive, contribute)
   - Focus on relevance to the role

   Job Description:
${data.jobDescription}

Candidate Information:
- Current Role: ${professionalTitle}
- Key Skills: ${skills}

Return only the summary text.`;

      const summaryCompletion = await llm.invoke([
        new SystemMessage("You are a professional resume writer who creates compelling, tailored summaries."),
        new HumanMessage(summaryPrompt)
      ]);

      // Get the content as string and handle potential complex message content
      const summaryContent = typeof summaryCompletion.content === 'string' 
        ? summaryCompletion.content 
        : '';
      
      const summary = summaryContent.replace(/^"|"$/g, '') || 
        `${yearsOfExperience}+ years of experience as a ${professionalTitle} with expertise in ${skills}. Proven track record of delivering high-quality solutions while collaborating effectively across teams to solve complex problems.`;
      
      y = addSectionTitle('PROFESSIONAL SUMMARY');
      y = addText(summary, 11, { maxWidth: contentWidth, justify: true });
      
      // Skills in 3 columns with bullet points
      y = addSectionTitle('TECHNICAL SKILLS');
      
      // Display all skills in a single line with comma separators
      const skillsText = skillsArray.join(', ');
      
      y = addText(skillsText, 11, {
        maxWidth: contentWidth,
        justify: true
      });

      // Experience
      y = addSectionTitle('PROFESSIONAL EXPERIENCE');
      data.experience.forEach((exp, index) => {
        const titleCompany = `${exp.title}, ${exp.company}`;
        y = addText(titleCompany, 12, { isBold: true, maxWidth: contentWidth - 50 });
        
        const startDate = formatDate(exp.startDate);
        const endDate = exp.endDate ? formatDate(exp.endDate) : 'Present';
        const dateRange = `${startDate} - ${endDate}`;
        y -= (12 / 2);
        addText(dateRange, 11, { rightAlign: true });
        if (exp.location) {
          y = addText(exp.location, 11, { indent: 2 });
        }
        
        const achievements = exp.achievements || [];
        if (achievements.length > 0) {
          achievements.forEach((achievement, i) => {
            y = addText(`• ${achievement.trim()}`, 11, { indent: 4, maxWidth: contentWidth - 6 });
            if (i < achievements.length - 1) {
              y += 0.3;
            }
          });
        }
        
        // Add space between experiences
        if (index < data.experience.length - 1) {
          y += 2;
        }
      });

      // Education
      if (data.education && data.education.length > 0) {
        y = addSectionTitle('EDUCATION');
        data.education.forEach((edu, index) => {
          const degreeSchool = `${edu.degree}, ${edu.school}`;
          y = addText(degreeSchool, 12, { isBold: true });
          
          const dateRange = `${edu.startDate ? formatDate(edu.startDate) : ''} - ${edu.endDate ? formatDate(edu.endDate) : 'Present'}`;
          y -= (12 / 2);
          addText(dateRange, 11, { rightAlign: true });
          
          if (edu.location) {
            y = addText(edu.location, 11, { indent: 2 });
          }
          
          if (edu.gpa) {
            y = addText(`GPA: ${edu.gpa}`, 11, { indent: 2 });
          }
          
          if (edu.honors && edu.honors.length > 0) {
            y = addText(`Honors: ${edu.honors.join(', ')}`, 11, { indent: 2 });
          }
          
          if (index < data.education.length - 1) {
            y += 2;
          }
        });
      }

      // Projects
      if (data.projects && data.projects.length > 0) {
        y = addSectionTitle('PROJECTS');
        data.projects.forEach((project, index) => {
          y = addText(project.name, 12, { isBold: true });
          
          if (project.description) {
            y = addText(project.description, 11, { indent: 2 });
          }
          
          if (project.technologies && project.technologies.length > 0) {
            y = addText(`Technologies: ${project.technologies.join(', ')}`, 11, { indent: 2 });
          }
          
          if (project.results) {
            y = addText(`Results: ${project.results}`, 11, { indent: 2 });
          }
          
          if (index < data.projects.length - 1) {
            y += 2;
          }
        });
      }

      // Certifications
      if (data.certifications && data.certifications.length > 0) {
        y = addSectionTitle('CERTIFICATIONS');
        data.certifications.forEach((cert, index) => {
          const certText = `${cert.name}${cert.issuer ? ` - ${cert.issuer}` : ''}`;
          y = addText(certText, 11);
          
          if (cert.date) {
            y -= (11 / 2);
            addText(formatDate(cert.date), 11, { rightAlign: true });
          }
          
          if (index < data.certifications.length - 1) {
            y += 1;
          }
        });
      }

      // Convert to Buffer
      const pdfBuffer = Buffer.from(doc.output('arraybuffer'));
      resolve(pdfBuffer);
    } catch (error) {
      reject(error);
    }
  });
} 