'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';

export function ResumeDownload({ profile }) {
  const [isLoading, setIsLoading] = useState(false);

  const handleDownload = async () => {
    try {
      setIsLoading(true);

      // Transform profile data
      const resumeData = {
        fullName: profile.fullName,
        title: profile.title,
        email: profile.email,
        phone: profile.phone,
        location: profile.location || '',
        linkedin: profile.linkedinUrl || '',
        github: profile.githubUrl || '',
        jobDescription: '', // Add empty job description
        skills: {
          technical: profile.skills,
          soft: [], // Add soft skills if available in profile
        },
        experience: profile.experience.map(exp => ({
          title: exp.position,
          company: exp.company,
          location: exp.location || profile.location || '',
          startDate: new Date(exp.startDate),
          endDate: exp.endDate ? new Date(exp.endDate) : null,
          description: exp.description || '',
          achievements: exp.description ? [exp.description] : [],
        })),
        education: profile.education.map(edu => ({
          school: edu.institution,
          degree: edu.degree,
          field: edu.description || '',
          startDate: new Date(edu.startDate),
          endDate: edu.endDate ? new Date(edu.endDate) : null,
          description: edu.description || '',
        })),
        projects: profile.projects.map(proj => ({
          name: proj.name,
          description: proj.description,
          technologies: proj.technologies,
          results: proj.url || '', // Use URL as results since results is not stored
        })),
        certifications: profile.certifications.map(cert => ({
          name: cert.name,
          issuer: cert.issuer,
          issueDate: cert.date,
        })),
      };

      // Make API request to generate resume
      const response = await fetch('/api/resume/download', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(resumeData),
      });

      if (!response.ok) {
        throw new Error('Failed to generate resume');
      }

      // Get the file content
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'resume.pdf';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading resume:', error);
      // You might want to show an error message to the user here
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Button
      variant="default"
      onClick={handleDownload}
      disabled={isLoading}
    >
      <Download className="mr-2 h-4 w-4" />
      {isLoading ? 'Generating PDF...' : 'Download Resume'}
    </Button>
  );
} 