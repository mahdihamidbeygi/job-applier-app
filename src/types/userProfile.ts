export interface Experience {
  id: string;
  title: string;
  company: string;
  location: string;
  startDate: Date;
  endDate?: Date;
  description: string;
  userId: string;
}

export interface Education {
  id: string;
  school: string;
  degree: string;
  field: string;
  startDate: Date;
  endDate?: Date;
  description?: string;
  userId: string;
}

export interface Skill {
  id: string;
  name: string;
  level?: string;
  userId: string;
}

export interface UserProfile {
  id: string;
  userId: string;
  name: string;
  email: string;
  phone?: string;
  location?: string;
  summary?: string;
  resumeUrl?: string;
  linkedinUrl?: string;
  githubUrl?: string;
  portfolioUrl?: string;
  createdAt: Date;
  updatedAt: Date;
  experience: Experience[];
  education: Education[];
  skills: Skill[];
}

export interface UserProfileFormData {
  name: string;
  email: string;
  phone?: string;
  location?: string;
  summary?: string;
  linkedinUrl?: string;
  githubUrl?: string;
  portfolioUrl?: string;
  experience: Omit<Experience, 'id' | 'userId'>[];
  education: Omit<Education, 'id' | 'userId'>[];
  skills: Omit<Skill, 'id' | 'userId'>[];
} 