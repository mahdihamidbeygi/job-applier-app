'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';
import { ResumeData } from '@/types/resume';

interface ResumeDownloadProps {
  profile: {
    fullName: string;
    title: string;
    email: string;
    phone: string;
    location: string | null;
    linkedinUrl: string | null;
    githubUrl: string | null;
    summary: string;
    skills: string[];
    experience: Array<{
      company: string;
      position: string;
      startDate: Date;
      endDate: Date | null;
      description: string;
    }>;
    education: Array<{
      institution: string;
      degree: string;
      startDate: Date;
      endDate: Date | null;
      description: string;
    }>;
    projects: Array<{
      name: string;
      description: string;
      technologies: string[];
      url: string | null;
    }>;
    certifications: Array<{
      name: string;
      issuer: string;
      date: Date;
      url: string | null;
    }>;
  };
}

export function ResumeDownload({ profile }: ResumeDownloadProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleDownload = async () => {
    try {
      setIsLoading(true);

      // Transform profile data to match ResumeData type
      const resumeData: ResumeData = {
        fullName: profile.fullName,
        title: profile.title,
        email: profile.email,
        phone: profile.phone,
        location: profile.location || '',
        linkedin: profile.linkedinUrl || '',
        github: profile.githubUrl || '',
        summary: profile.summary,
        skills: {
          technical: profile.skills,
          soft: [], // Add soft skills if available in profile
        },
        experience: profile.experience.map(exp => ({
          title: exp.position,
          company: exp.company,
          location: '', // Location not stored in experience table
          startDate: exp.startDate.toISOString(),
          endDate: exp.endDate?.toISOString(),
          achievements: [exp.description],
        })),
        education: profile.education.map(edu => ({
          degree: edu.degree,
          school: edu.institution,
          location: '', // Location not stored in education table
          graduationYear: edu.endDate?.getFullYear().toString() || '',
          major: edu.degree, // Use degree as major since field is not stored
          description: edu.description,
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
          date: cert.date.toISOString(),
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