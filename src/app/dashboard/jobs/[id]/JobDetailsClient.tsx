'use client';

import { Job, UserProfile } from "@prisma/client";
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { formatDistanceToNow, format } from 'date-fns';
import { Download, ExternalLink, MapPin, Clock, Building } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useState } from 'react';
import { Separator } from "@/components/ui/separator";
import { ErrorBoundary } from 'react-error-boundary';

interface UserProfileWithRelations extends UserProfile {
  experience: {
    title: string;
    company: string;
    location: string;
    startDate: Date;
    endDate: Date | null;
    description: string;
  }[];
  education: {
    school: string;
    degree: string;
    field: string;
    startDate: Date;
    endDate: Date | null;
    description: string | null;
  }[];
  skills: {
    name: string;
    level: string | null;
  }[];
}

interface JobDetailsClientProps {
  job: Job;
  userProfile: UserProfileWithRelations;
}

function ErrorFallback({ error }: { error: Error }) {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Something went wrong</CardTitle>
          <CardDescription>
            {error.message}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => window.location.reload()}>
            Try again
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default function JobDetailsClient({ job, userProfile }: JobDetailsClientProps) {
  console.log('JobDetailsClient rendering with:', { job, userProfile });
  
  const [isGeneratingResume, setIsGeneratingResume] = useState(false);
  const [isGeneratingCoverLetter, setIsGeneratingCoverLetter] = useState(false);

  const generateTailoredResume = async (): Promise<Blob> => {
    const response = await fetch(`/api/download/resume/${job.id}`, {
      method: 'GET',
    });
    
    if (!response.ok) {
      throw new Error('Failed to generate resume');
    }
    
    return response.blob();
  };

  const generateCoverLetter = async (): Promise<Blob> => {
    const response = await fetch(`/api/download/cover-letter/${job.id}`, {
      method: 'GET',
    });
    
    if (!response.ok) {
      throw new Error('Failed to generate cover letter');
    }
    
    return response.blob();
  };

  const handleGenerateResume = async () => {
    try {
      setIsGeneratingResume(true);
      const blob = await generateTailoredResume();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${job.company}_${job.title}_Resume.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error generating resume:', error);
      toast.error('Failed to generate resume');
    } finally {
      setIsGeneratingResume(false);
    }
  };

  const handleGenerateCoverLetter = async () => {
    try {
      setIsGeneratingCoverLetter(true);
      const blob = await generateCoverLetter();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${job.company}_${job.title}_CoverLetter.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error generating cover letter:', error);
      toast.error('Failed to generate cover letter');
    } finally {
      setIsGeneratingCoverLetter(false);
    }
  };

  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        {/* Job Details Card */}
        <Card>
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className="text-2xl font-bold">{job.title}</CardTitle>
                <CardDescription className="mt-2">
                  <div className="flex items-center text-lg text-muted-foreground">
                    <Building className="w-5 h-5 mr-2" />
                    {job.company}
                  </div>
                  <div className="flex items-center mt-1 text-muted-foreground">
                    <MapPin className="w-4 h-4 mr-2" />
                    {job.location}
                  </div>
                  <div className="flex items-center mt-1 text-muted-foreground">
                    <Clock className="w-4 h-4 mr-2" />
                    Posted {formatDistanceToNow(new Date(job.postedAt))} ago
                  </div>
                </CardDescription>
              </div>
              <Button variant="outline" asChild>
                <a href={job.url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="w-4 h-4 mr-2" />
                  View on LinkedIn
                </a>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div className="flex flex-wrap gap-6">
                {job.salary && (
                  <div className="flex items-center">
                    <div>
                      <h3 className="font-semibold text-sm text-muted-foreground">Salary</h3>
                      <p className="mt-1">{job.salary}</p>
                    </div>
                  </div>
                )}
                {job.jobType && (
                  <div className="flex items-center">
                    <div>
                      <h3 className="font-semibold text-sm text-muted-foreground">Employment Type</h3>
                      <p className="mt-1">{job.jobType}</p>
                    </div>
                  </div>
                )}
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold text-lg mb-3">Job Description</h3>
                <div className="prose max-w-none">
                  <div className="whitespace-pre-wrap text-muted-foreground">{job.description}</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Application Documents Card */}
        <Card>
          <CardHeader>
            <CardTitle>Application Documents</CardTitle>
            <CardDescription>
              Generate your tailored resume and cover letter for this position
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="border-2">
                <CardHeader>
                  <CardTitle className="text-lg">Resume</CardTitle>
                  <CardDescription>
                    Tailored to highlight relevant skills and experience
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button 
                    className="w-full"
                    onClick={handleGenerateResume}
                    disabled={isGeneratingResume}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    {isGeneratingResume ? 'Generating...' : 'Download Resume'}
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-2">
                <CardHeader>
                  <CardTitle className="text-lg">Cover Letter</CardTitle>
                  <CardDescription>
                    Customized to address job requirements
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button 
                    className="w-full"
                    onClick={handleGenerateCoverLetter}
                    disabled={isGeneratingCoverLetter}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    {isGeneratingCoverLetter ? 'Generating...' : 'Download Cover Letter'}
                  </Button>
                </CardContent>
              </Card>
            </div>
          </CardContent>
        </Card>

        {/* Profile Summary Card */}
        <Card>
          <CardHeader>
            <CardTitle>Your Profile Summary</CardTitle>
            <CardDescription>
              Information that will be used to generate your application documents
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold mb-2">Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {userProfile.skills.map((skill) => (
                    <span key={skill.name} className="px-2 py-1 bg-gray-100 rounded-md text-sm">
                      {skill.name}
                    </span>
                  ))}
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold mb-2">Experience</h3>
                <div className="space-y-4">
                  {userProfile.experience.map((exp) => (
                    <div key={`${exp.company}-${exp.title}`} className="border-l-2 border-gray-200 pl-4">
                      <h4 className="font-medium">{exp.title}</h4>
                      <p className="text-sm text-gray-600">{exp.company}</p>
                      <p className="text-sm text-gray-500">{exp.location}</p>
                      <p className="text-sm text-gray-500">
                        {format(new Date(exp.startDate), 'MMM yyyy')} - {exp.endDate ? format(new Date(exp.endDate), 'MMM yyyy') : 'Present'}
                      </p>
                      {exp.description && (
                        <p className="mt-2 text-sm text-gray-600">{exp.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="font-semibold mb-2">Education</h3>
                <div className="space-y-4">
                  {userProfile.education.map((edu) => (
                    <div key={`${edu.school}-${edu.degree}`} className="border-l-2 border-gray-200 pl-4">
                      <h4 className="font-medium">{edu.degree} in {edu.field}</h4>
                      <p className="text-sm text-gray-600">{edu.school}</p>
                      <p className="text-sm text-gray-500">
                        {format(new Date(edu.startDate), 'MMM yyyy')} - {edu.endDate ? format(new Date(edu.endDate), 'MMM yyyy') : 'Present'}
                      </p>
                      {edu.description && (
                        <p className="mt-2 text-sm text-gray-600">{edu.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </ErrorBoundary>
  );
} 