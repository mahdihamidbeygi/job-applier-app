'use client';

import { UserProfile } from "@prisma/client";
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { formatDistanceToNow, format } from 'date-fns';
import { Download, ExternalLink, MapPin, Clock, Building, Loader2 } from 'lucide-react';
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
  job: {
    id: string;
    platform: string;
    externalId: string;
    title: string;
    company: string;
    location: string | null;
    description: string;
    salary: string | null;
    jobType: string | null;
    url: string;
    postedAt: Date;
    isExternal: boolean;
  };
  userProfile: UserProfileWithRelations;
}

function ErrorFallback({ error }: { error: Error }) {
  return (
    <div className="p-4 bg-red-900 border border-red-700 rounded-md">
      <h2 className="text-lg font-semibold text-red-100 mb-2">Something went wrong:</h2>
      <pre className="text-sm text-red-200 whitespace-pre-wrap">{error.message}</pre>
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
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to generate resume');
    }
    
    return response.blob();
  };

  const generateCoverLetter = async (): Promise<Blob> => {
    // First, try to find an existing job application
    let jobApplication = await fetch(`/api/applications/job/${job.id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }).then(res => res.json()).catch(() => null);

    // If no application exists, create one
    if (!jobApplication) {
      jobApplication = await fetch('/api/applications', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          jobId: job.id,
          status: 'DRAFT'
        }),
      }).then(res => res.json());
    }

    // Now generate the cover letter using the application ID
    const response = await fetch(`/api/download/cover-letter/${jobApplication.id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to generate cover letter: ${errorText}`);
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
      toast.error(error instanceof Error ? error.message : 'Failed to generate cover letter');
    } finally {
      setIsGeneratingCoverLetter(false);
    }
  };

  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        {/* Job Details Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className="text-2xl font-bold text-slate-100">{job.title}</CardTitle>
                <div className="mt-2">
                  <div className="flex items-center text-lg text-slate-300">
                    <Building className="w-5 h-5 mr-2" />
                    {job.company}
                  </div>
                  <div className="flex items-center mt-1 text-slate-300">
                    <MapPin className="w-4 h-4 mr-2" />
                    {job.location}
                  </div>
                  <div className="flex items-center mt-1 text-slate-300">
                    <Clock className="w-4 h-4 mr-2" />
                    Posted {formatDistanceToNow(new Date(job.postedAt))} ago
                  </div>
                </div>
              </div>
              <Button 
                variant="outline" 
                asChild
                className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-slate-100"
              >
                <a href={job.url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="w-4 h-4 mr-2" />
                  View on LinkedIn
                </a>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <Card className="bg-slate-800 border-slate-700">
                <CardContent>
                  <div className="space-y-6">
                    <div className="flex flex-wrap gap-6">
                      {job.salary && (
                        <div className="flex items-center">
                          <div>
                            <h3 className="font-semibold text-sm text-slate-300">Salary</h3>
                            <p className="mt-1 text-slate-100">{job.salary}</p>
                          </div>
                        </div>
                      )}
                      {job.jobType && (
                        <div className="flex items-center">
                          <div>
                            <h3 className="font-semibold text-sm text-slate-300">Employment Type</h3>
                            <p className="mt-1 text-slate-100">{job.jobType}</p>
                          </div>
                        </div>
                      )}
                    </div>

                    <Separator className="bg-slate-700" />

                    <div>
                      <h3 className="font-semibold text-lg text-slate-100 mb-3">Job Description</h3>
                      <div className="prose max-w-none">
                        <div className="whitespace-pre-wrap text-slate-300">{job.description}</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Application Documents Card */}
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-slate-100">Application Documents</CardTitle>
                  <CardDescription className="text-slate-300">
                    Download your tailored resume and cover letter for this position
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-4">
                    <Button
                      onClick={handleGenerateResume}
                      disabled={isGeneratingResume}
                      className="bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      {isGeneratingResume ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Generating Resume...
                        </>
                      ) : (
                        <>
                          <Download className="mr-2 h-4 w-4" />
                          Download Resume
                        </>
                      )}
                    </Button>
                    <Button
                      onClick={handleGenerateCoverLetter}
                      disabled={isGeneratingCoverLetter}
                      className="bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      {isGeneratingCoverLetter ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Generating Cover Letter...
                        </>
                      ) : (
                        <>
                          <Download className="mr-2 h-4 w-4" />
                          Download Cover Letter
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Profile Summary Card */}
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-slate-100">Your Profile Summary</CardTitle>
                  <CardDescription className="text-slate-300">
                    Information that will be used to generate your application documents
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    <div>
                      <h3 className="font-semibold text-slate-100 mb-2">Skills</h3>
                      <div className="flex flex-wrap gap-2">
                        {userProfile.skills.map((skill) => (
                          <span key={skill.name} className="px-2 py-1 bg-slate-700 text-slate-200 rounded-md text-sm">
                            {skill.name}
                          </span>
                        ))}
                      </div>
                    </div>

                    <Separator className="bg-slate-700" />

                    <div>
                      <h3 className="font-semibold text-slate-100 mb-2">Experience</h3>
                      <div className="space-y-4">
                        {userProfile.experience.map((exp) => (
                          <div key={`${exp.company}-${exp.title}`} className="border-l-2 border-slate-700 pl-4">
                            <h4 className="font-medium text-slate-100">{exp.title}</h4>
                            <p className="text-sm text-slate-300">{exp.company}</p>
                            <p className="text-sm text-slate-400">{exp.location}</p>
                            <p className="text-sm text-slate-400">
                              {format(new Date(exp.startDate), 'MMM yyyy')} - {exp.endDate ? format(new Date(exp.endDate), 'MMM yyyy') : 'Present'}
                            </p>
                            {exp.description && (
                              <p className="mt-2 text-sm text-slate-300">{exp.description}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    <Separator className="bg-slate-700" />

                    <div>
                      <h3 className="font-semibold text-slate-100 mb-2">Education</h3>
                      <div className="space-y-4">
                        {userProfile.education.map((edu) => (
                          <div key={`${edu.school}-${edu.degree}`} className="border-l-2 border-slate-700 pl-4">
                            <h4 className="font-medium text-slate-100">{edu.degree} in {edu.field}</h4>
                            <p className="text-sm text-slate-300">{edu.school}</p>
                            <p className="text-sm text-slate-400">
                              {format(new Date(edu.startDate), 'MMM yyyy')} - {edu.endDate ? format(new Date(edu.endDate), 'MMM yyyy') : 'Present'}
                            </p>
                            {edu.description && (
                              <p className="mt-2 text-sm text-slate-300">{edu.description}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </CardContent>
        </Card>
      </div>
    </ErrorBoundary>
  );
} 