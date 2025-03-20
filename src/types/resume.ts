export interface ResumeData {
  fullName: string;
  title: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  github: string;
  summary: string;
  skills: {
    technical: string[];
    soft: string[];
  };
  experience: Array<{
    title: string;
    company: string;
    location: string;
    startDate: string;
    endDate?: string;
    achievements: string[];
  }>;
  education: Array<{
    degree: string;
    school: string;
    location: string;
    graduationYear: string;
    major: string;
    gpa?: string;
    courses?: string[];
    honors?: string[];
  }>;
  projects: Array<{
    name: string;
    description: string;
    technologies: string[];
    results: string;
  }>;
  certifications: Array<{
    name: string;
    issuer: string;
    date: string;
  }>;
} 