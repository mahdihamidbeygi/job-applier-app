import { jsPDF } from 'jspdf';
import { ResumeData } from '@/types/resume';
import { ChatOpenAI } from '@langchain/openai';
import { SystemMessage, HumanMessage, BaseMessage } from '@langchain/core/messages';

export async function convertMarkdownToPDF(markdown: string, data: ResumeData ): Promise<Buffer> {
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
      const formatDate = (dateString: string | Date) => {
        const date = new Date(dateString);
        return date.toISOString().substring(0, 7); // Gets YYYY-MM format
      };

      // Helper function to add text and return new Y position
      const addText = (text: string, fontSize: number, options: {
        isBold?: boolean,
        isCenter?: boolean,
        indent?: number,
        maxWidth?: number,
        isBullet?: boolean,
        rightAlign?: boolean,
        x?: number,
        justify?: boolean
      } = {}) => {
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
            lines.forEach((line: string, index: number) => {
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
      const addSectionTitle = (title: string) => {
        y += 3; // Increased space before section titles to separate sections
        y = addText(title.toUpperCase(), 14, { isBold: true });
        y += 1;
        return y;
      };      
      // Get skills from OpenAI
      const skillsPrompt = `extract six keyword skills for a resume based on the following:

      Job Description:
      ${data.jobDescription}
      
      Candidate Information:
      - Experience: ${data.experience}
      
      extract six keyword skills from the resume based on the job description`;
      
      const llm = new ChatOpenAI({
        modelName: 'gpt-4',
        temperature: 0.7,
      });

      const messages: BaseMessage[] = [
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
      
      // Use skills from OpenAI or fallback to resume data
      const skills = data.skills.technical.slice(0, 3).join(", ");
      // Ensure skills are always in array format
      const skillsArray: string[] = skillsContent 
        ? skillsContent.split(',').map((s: string) => s.trim()) 
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
      
      // Generate summary using OpenAI
      const summaryPrompt = `Write a concise professional summary for a resume based on the following:

Job Description:
${data.jobDescription}

Candidate Information:
- Resume: ${data}
- Current Role: ${professionalTitle}
- Key Skills: ${skills}

Keep it to 1-2 sentences focused on relevant experience and skills for this role.`;

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
        console.log(exp.location);
        if (exp.location) {
          y = addText(exp.location, 11, { indent: 2 });
        }
        
        const achievements = exp.achievements || [];
        if (achievements.length > 0) {
          achievements.forEach((achievement: string, i) => {
            y = addText(`• ${achievement.trim()}`, 11, { indent: 4, maxWidth: contentWidth - 6 });
            if (i < achievements.length - 1) {
              y += 0.3;
            }
          });
        } else if (exp.description) {
          // If there are no achievements but there is a description, use that
          y = addText(`• ${exp.description.trim()}`, 11, { indent: 4, maxWidth: contentWidth - 6 });
        }
        
        if (index < data.experience.length - 1) {
          y += 2; // Increased space between experiences
        }
      });

      // Projects section (if exists in data)
      if (data.projects && data.projects.length > 0) {
        y = addSectionTitle('PROJECTS');
        data.projects.forEach((project, index) => {
          const projectTitle = project.name;
          y = addText(projectTitle, 12, { isBold: true, maxWidth: contentWidth - 50 });
          
          if (project.url) {
            y -= (12 / 2);
            addText(project.url, 11, { rightAlign: true });
          }
          
          if (project.description) {
            y = addText(`• ${project.description.trim()}`, 11, { indent: 4, maxWidth: contentWidth - 6 });
          }

          if (project.technologies && project.technologies.length > 0) {
            y = addText(`Technologies: ${project.technologies.join(', ')}`, 11, { indent: 4, maxWidth: contentWidth - 6 });
          }

          if (index < (data.projects?.length ?? 0) - 1) {
            y += 2; // Space between projects
          }
        });
      }

      // Skip certifications section since it's not in the ResumeData interface
      // Certifications section (if exists in data)
      if (data.certifications && data.certifications.length > 0) {
        y = addSectionTitle('CERTIFICATIONS');
        data.certifications.forEach((cert, index) => {
          const certTitle = cert.name;
          y = addText(certTitle, 12, { isBold: true, maxWidth: contentWidth - 50 });
          
          if (cert.issuer) {
            y = addText(cert.issuer, 11, { indent: 2 });
          }

          if (cert.issueDate) {
            const issueYear = new Date(cert.issueDate).getFullYear().toString();
            y -= (12 / 2);
            addText(issueYear, 11, { rightAlign: true });
          }

          if (index < (data.certifications?.length ?? 0) - 1) {
            y += 2; // Space between certifications
          }
        });
      }
      // Education (always last)
      y = addSectionTitle('EDUCATION');
      data.education.forEach((edu, index) => {
        // Use edu.field instead of edu.major
        const eduTitle = `${edu.degree} in ${edu.field}`;
        y = addText(eduTitle, 12, { isBold: true, maxWidth: contentWidth - 50 });
        y -= (12 / 2);
        
        // Extract year from endDate or use "Present"
        const graduationYear = edu.endDate 
          ? new Date(edu.endDate).getFullYear().toString() 
          : "Present";
          
        addText(graduationYear, 11, { rightAlign: true });
        y = addText(`${edu.school}`, 11, { indent: 2 });
        
        if (index < data.education.length - 1) {
          y += 2; // Increased space between education entries
        }
      });

      // Convert to Buffer
      const pdfBuffer = Buffer.from(doc.output('arraybuffer'));
      resolve(pdfBuffer);
    } catch (error) {
      reject(error);
    }
  });
} 