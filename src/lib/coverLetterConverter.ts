import { jsPDF } from 'jspdf';
import { ResumeData } from '@/types/resume';

export async function convertCoverLetterToPDF(
  coverLetter: string,
  data: ResumeData
): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    try {
      const doc = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
      });

      // Set initial position
      let y = 15;
      const leftMargin = 25; // Wider margins for cover letter
      const rightMargin = 185;
      const contentWidth = rightMargin - leftMargin - 2;

      // Helper function to format date
      const formatDate = () => {
        const date = new Date();
        return date.toISOString().split('T')[0];
      };

      // Helper function to add text and return new Y position
      const addText = (text: string, fontSize: number, options: {
        isBold?: boolean,
        isCenter?: boolean,
        indent?: number,
        maxWidth?: number,
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
          
          if (options.justify) {
            // Full justification for all lines except the last one
            lines.forEach((line: string, index: number) => {
              if (index < lines.length - 1) {
                // Calculate the space needed to justify
                const lineWidth = doc.getTextWidth(line);
                const spaceToDistribute = effectiveWidth - lineWidth;
                const words = line.split(' ');
                const spacesCount = words.length - 1;
                
                if (spacesCount > 0) {
                  // Calculate additional space between words
                  const extraSpacePerGap = spaceToDistribute / spacesCount;
                  
                  // Position each word with calculated spacing
                  let currentX = x;
                  words.forEach((word, wordIndex) => {
                    doc.text(word, currentX, y);
                    if (wordIndex < words.length - 1) {
                      const wordWidth = doc.getTextWidth(word);
                      currentX += wordWidth + doc.getTextWidth(' ') + extraSpacePerGap;
                    }
                  });
                } else {
                  // Single word lines are left-aligned
                  doc.text(line, x, y);
                }
              } else {
                // Last line is left-aligned
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

      // Header with contact information
      y = addText(data.fullName, 12, { isBold: true });
      y = addText(data.email, 11);
      y = addText(data.phone, 11);
      y = addText(data.location, 11);

      // Date
      y = addText(formatDate(), 11);
      y += 4;

      // Cover letter content with justified paragraphs
      const paragraphs = coverLetter.split('\n\n');
      paragraphs.forEach((paragraph, index) => {
        if (paragraph.trim()) {
          y = addText(paragraph.trim(), 11, { 
            justify: true, 
            maxWidth: contentWidth 
          });
          if (index < paragraphs.length - 1) {
            y += 2;
          }
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