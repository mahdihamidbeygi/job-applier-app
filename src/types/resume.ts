export interface ResumeData {
  fullName: string;
  title: string;
  email: string;
  phone?: string;
  location?: string;
  linkedin?: string;
  github?: string;
  jobDescription?: string;
  skills: {
    technical: string[];
    soft: string[];
  };
  experience: Array<{
    company: string;
    title: string;
    location?: string;
    startDate: Date;
    endDate: Date | null;
    description?: string;
    achievements?: string[];
  }>;
  education: Array<{
    school: string;
    degree: string;
    field: string;
    startDate: Date;
    endDate: Date | null;
    description?: string;
  }>;
  projects?: Array<{
    name: string;
    description?: string;
    url?: string;
    technologies?: string[];
  }>;
  certifications?: Array<{
    name: string;
    issuer?: string;
    issueDate?: Date;
  }>;
}

export interface ResumeInfo {
  skills: {
    technical: string[];
    soft: string[];
  };
  workExperience: Array<{
    company: string;
    title: string;
    startDate: string;
    endDate: string;
    achievements: string[];
  }>;
  education: Array<{
    school: string;
    degree: string;
    startDate: string;
    endDate: string;
  }>;
  contactInformation: {
    name: string;
    email: string;
    phone?: string;
    location?: string;
  };
} 