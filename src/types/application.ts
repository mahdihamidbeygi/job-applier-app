export const ApplicationStatus = {
  PENDING: 'PENDING',
  SUBMITTED: 'SUBMITTED',
  INTERVIEWING: 'INTERVIEWING',
  OFFERED: 'OFFERED',
  REJECTED: 'REJECTED',
  WITHDRAWN: 'WITHDRAWN',
} as const;

export type ApplicationStatus = typeof ApplicationStatus[keyof typeof ApplicationStatus];

export interface JobApplication {
  id: string;
  userId: string;
  jobId: string;
  status: ApplicationStatus;
  notes?: string | null;
  resumeUsed?: string | null;
  coverLetter?: string | null;
  appliedAt: Date;
  updatedAt: Date;
  job: {
    id: string;
    title: string;
    company: string;
    location: string | null;
    description: string;
    platform: string;
    externalId: string;
    salary: string | null;
    jobType: string | null;
    url: string;
    postedAt: Date;
    isExternal: boolean;
  };
} 