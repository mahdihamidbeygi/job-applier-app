import fs from 'fs';
import path from 'path';

export async function generateResumeFromTemplate(data) {
  // Read the template file
  const templatePath = path.join(process.cwd(), 'src/templates/resume.md');
  let template = await fs.promises.readFile(templatePath, 'utf-8');

  // Replace template placeholders with actual data
  const replacements = {
    '[Your Full Name]': data.fullName || '',
    '[Your Professional Title]': data.title || '',
    '[Your Email]': data.email || '',
    '[Your Phone]': data.phone || '',
    '[Your Location]': data.location || '',
    '[LinkedIn Profile]': data.linkedin || '',
    '[GitHub Profile]': data.github || '',
    '[Current Date]': new Date().toLocaleDateString(),
  };

  // Replace all placeholders
  Object.entries(replacements).forEach(([key, value]) => {
    template = template.replace(new RegExp(key, 'g'), value);
  });

  // Replace Professional Summary
  if (data.summary) {
    template = template.replace(
      '[2-3 sentences highlighting your key strengths, years of experience, and career objectives]',
      data.summary
    );
  }

  // Replace Skills
  if (data.skills) {
    const technicalSkills = data.skills.technical
      .map(skill => `- ${skill}`)
      .join('\n');
    const softSkills = data.skills.soft
      .map(skill => `- ${skill}`)
      .join('\n');

    template = template.replace(
      '**Programming Languages:** [List your primary programming languages]',
      technicalSkills
    );
    template = template.replace(
      '[Key soft skill 1]\n[Key soft skill 2]\n[Key soft skill 3]',
      softSkills
    );
  }

  // Replace Experience
  if (data.experience && data.experience.length > 0) {
    const experienceSection = data.experience
      .map(exp => `
### ${exp.title}
${exp.company} | ${exp.location} | ${exp.startDate} - ${exp.endDate || 'Present'}
${exp.achievements.map(achievement => `- ${achievement}`).join('\n')}
`)
      .join('\n');

    template = template.replace(
      /### \[Job Title\].*?\[Key achievement or responsibility\]/gs,
      experienceSection
    );
  }

  // Replace Education
  if (data.education && data.education.length > 0) {
    const educationSection = data.education
      .map(edu => `
### ${edu.degree}
${edu.school} | ${edu.location} | ${edu.graduationYear}
- Major: ${edu.major}
${edu.gpa ? `- GPA: ${edu.gpa}` : ''}
${edu.courses ? `- Relevant Coursework: ${edu.courses.join(', ')}` : ''}
${edu.honors ? `- Honors/Awards: ${edu.honors.join(', ')}` : ''}
`)
      .join('\n');

    template = template.replace(
      /### \[Degree Name\].*?\[List any honors or awards\]/gs,
      educationSection
    );
  }

  // Replace Projects
  if (data.projects && data.projects.length > 0) {
    const projectsSection = data.projects
      .map(project => `
### ${project.name}
- ${project.description}
- Technologies: ${project.technologies.join(', ')}
- Results: ${project.results}
`)
      .join('\n');

    template = template.replace(
      /### \[Project Name\].*?\[Key achievements or results\]/gs,
      projectsSection
    );
  }

  // Replace Certifications
  if (data.certifications && data.certifications.length > 0) {
    const certificationsSection = data.certifications
      .map(cert => `- ${cert.name} | ${cert.issuer} | ${cert.date}`)
      .join('\n');

    template = template.replace(
      /\[Certification Name\] \| \[Issuing Organization\] \| \[Date\]/g,
      certificationsSection
    );
  }

  return template;
} 