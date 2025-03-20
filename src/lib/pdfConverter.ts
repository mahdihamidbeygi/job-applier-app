import { jsPDF } from 'jspdf';
import { ResumeData } from '@/types/resume';

export async function convertMarkdownToPDF(markdown: string, data: ResumeData): Promise<Buffer> {
  return new Promise((resolve, reject) => {
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
      const formatDate = (dateString: string) => {
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

      // Header section
      y = addText(data.fullName, 24, { isBold: true, isCenter: true });
      y = addText(data.title, 16, { isCenter: true });
      y += 1;
      
      // Contact info - centered and compact
      const contactInfo = `${data.email} | ${data.phone} | ${data.location}`;
      const socialInfo = `${data.linkedin} | ${data.github}`;
      y = addText(contactInfo, 10, { isCenter: true });
      y = addText(socialInfo, 10, { isCenter: true });
      y += 2; // Added space after header section

      // Professional Summary
      y = addSectionTitle('PROFESSIONAL SUMMARY');
      y = addText(data.summary, 11, { maxWidth: contentWidth, justify: true });
      
      // Skills in 3 columns with bullet points
      y = addSectionTitle('TECHNICAL SKILLS');
      const skills = data.skills.technical;
      const skillsPerColumn = Math.ceil(skills.length / 3);
      const columnWidth = (contentWidth - 10) / 3;
      
      const startY = y;
      for (let col = 0; col < 3; col++) {
        y = startY;
        const startIndex = col * skillsPerColumn;
        const endIndex = Math.min(startIndex + skillsPerColumn, skills.length);
        const columnSkills = skills.slice(startIndex, endIndex);
        
        columnSkills.forEach((skill, index) => {
          const x = leftMargin + (col * (columnWidth + 5));
          y = addText(`• ${skill}`, 11, { 
            x,
            maxWidth: columnWidth 
          });
          if (index < columnSkills.length - 1) {
            y += 0.3;
          }
        });
      }
      
      const maxY = y;
      y = maxY;

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
        
        exp.achievements.forEach((achievement: string, i) => {
          y = addText(`• ${achievement.trim()}`, 11, { indent: 4, maxWidth: contentWidth - 6 });
          if (i < exp.achievements.length - 1) {
            y += 0.3;
          }
        });
        
        if (index < data.experience.length - 1) {
          y += 2; // Increased space between experiences
        }
      });

      // Projects (if any)
      if (data.projects.length > 0) {
        y = addSectionTitle('PROJECTS');
        data.projects.forEach((proj, index) => {
          y = addText(proj.name, 12, { isBold: true });
          y = addText(proj.description, 11, { indent: 2, maxWidth: contentWidth - 2, justify: true });
          y = addText(`Technologies: ${proj.technologies.join(' • ')}`, 11, { indent: 2 });
          if (proj.results) {
            y = addText(`Results: ${proj.results}`, 11, { indent: 2, justify: true });
          }
          
          if (index < data.projects.length - 1) {
            y += 2;
          }
        });
      }

      // Certifications (if any)
      if (data.certifications.length > 0) {
        y = addSectionTitle('CERTIFICATIONS');
        data.certifications.forEach((cert, index) => {
          const certTitle = `${cert.name} - ${cert.issuer}`;
          y = addText(certTitle, 11, { isBold: true, maxWidth: contentWidth - 50 });
          y -= (11 / 2);
          const certDate = formatDate(cert.date);
          addText(certDate, 11, { rightAlign: true });
          
          if (index < data.certifications.length - 1) {
            y += 2; // Increased space between certifications
          }
        });
      }

      // Education (always last)
      y = addSectionTitle('EDUCATION');
      data.education.forEach((edu, index) => {
        const eduTitle = `${edu.degree} in ${edu.major}`;
        y = addText(eduTitle, 12, { isBold: true, maxWidth: contentWidth - 50 });
        y -= (12 / 2);
        addText(edu.graduationYear.toString(), 11, { rightAlign: true });
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