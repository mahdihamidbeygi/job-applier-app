# Job Application Automation System Documentation

## Table of Contents
1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Setup Instructions](#setup-instructions)
4. [Package Documentation](#package-documentation)
5. [Features](#features)
6. [Architecture](#architecture)
7. [API Documentation](#api-documentation)
8. [Development Guide](#development-guide)

## Overview
The Job Application Automation System is a comprehensive platform designed to streamline the job application process. It helps users manage resumes, track applications, and automate job searches.

## Technology Stack

### Frontend
- **Next.js** (v14+): React framework for building the user interface
- **TailwindCSS**: Utility-first CSS framework for styling
- **shadcn/ui**: React components built with Radix UI and Tailwind

### Backend
- **NextAuth.js**: Authentication solution for Next.js applications
- **Prisma**: Type-safe ORM for database operations
- **PostgreSQL**: Primary database for storing application data

### File Storage
- **AWS SDK (v3)**: AWS services integration
  - `@aws-sdk/client-s3`: S3 operations
  - `@aws-sdk/s3-request-presigner`: Generate signed URLs for S3 objects

### Development Tools
- **TypeScript**: Type-safe JavaScript
- **ESLint**: Code linting
- **dotenv**: Environment variable management

## Setup Instructions

### Prerequisites
- Node.js (v18+)
- PostgreSQL
- AWS Account
- Google OAuth credentials (for authentication)

### Installation Steps
1. Clone the repository:
   \`\`\`bash
   git clone [repository-url]
   cd job-applier-app
   \`\`\`

2. Install dependencies:
   \`\`\`bash
   npm install
   \`\`\`

3. Configure environment variables:
   Copy \`.env.example\` to \`.env\` and fill in the values:
   \`\`\`
   # Database
   DATABASE_URL="postgresql://jobapplier:password@localhost:5432/jobapplier"

   # AWS
   AWS_ACCESS_KEY_ID="your-access-key"
   AWS_SECRET_ACCESS_KEY="your-secret-key"
   AWS_REGION="us-east-1"
   AWS_BUCKET_NAME="job-applier-files"

   # Auth
   NEXTAUTH_SECRET="your-secret"
   NEXTAUTH_URL="http://localhost:3000"
   GOOGLE_CLIENT_ID="your-client-id"
   GOOGLE_CLIENT_SECRET="your-client-secret"
   \`\`\`

4. Initialize the database:
   \`\`\`bash
   npx prisma generate
   npx prisma db push
   \`\`\`

5. Start the development server:
   \`\`\`bash
   npm run dev
   \`\`\`

## Package Documentation

### Core Packages

#### @aws-sdk/client-s3
- **Purpose**: Interact with AWS S3 for file storage
- **Key Features**:
  - File upload/download
  - Bucket management
  - Access control
- **Usage Example**:
  \`\`\`typescript
  import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
  
  const s3Client = new S3Client({
    region: process.env.AWS_REGION!,
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
    },
  });
  \`\`\`

#### Prisma
- **Purpose**: Database ORM
- **Key Features**:
  - Type-safe database queries
  - Schema management
  - Migration handling
- **Usage Example**:
  \`\`\`typescript
  import { PrismaClient } from '@prisma/client';
  
  const prisma = new PrismaClient();
  const user = await prisma.user.findUnique({
    where: { id: userId }
  });
  \`\`\`

#### NextAuth.js
- **Purpose**: Authentication system
- **Key Features**:
  - OAuth integration
  - Session management
  - Protected routes
- **Usage Example**:
  \`\`\`typescript
  import { getServerSession } from "next-auth";
  
  const session = await getServerSession();
  if (!session) {
    redirect('/auth/signin');
  }
  \`\`\`

## Features

### Current Features
1. **Authentication**
   - Google OAuth login
   - Session management
   - Protected routes

2. **File Storage**
   - S3 integration
   - Secure file upload
   - Signed URLs for access
   - Lifecycle management

### Planned Features

#### 1. Resume Management
- Resume upload interface
- Resume parsing and data extraction
- Resume version history
- Resume preview

#### 2. Job Application Tracking
- Application status board (Kanban style)
- Application timeline
- Follow-up reminders
- Interview scheduling

#### 3. Job Search Integration
- Job board aggregation
- Automated job matching
- Company research integration
- Salary data integration

#### 4. Analytics Dashboard
- Application success rate
- Response time analytics
- Interview conversion rate
- Job search trends

## Architecture

### Database Schema
The application uses PostgreSQL with Prisma as the ORM. Key models include:
- User
- Resume
- Application
- Job
- Company

### File Storage
AWS S3 is used for file storage with the following configuration:
- Server-side encryption
- Versioning enabled
- Lifecycle rules for cost optimization
- CORS configuration for web access

### Security Measures
1. **S3 Bucket Policy**:
   - Restricted access by referrer
   - Enforced HTTPS
   - Time-limited signed URLs

2. **Authentication**:
   - OAuth 2.0
   - Session-based auth
   - CSRF protection

## Development Guide

### Running Tests
\`\`\`bash
# Run unit tests
npm test

# Test file upload
npx ts-node -P src/scripts/tsconfig.json src/scripts/test-upload.ts
\`\`\`

### Code Style
- ESLint configuration enforces consistent code style
- TypeScript strict mode enabled
- Prettier for code formatting

### Best Practices
1. Always use TypeScript types
2. Follow the Next.js App Router patterns
3. Use server components where possible
4. Implement error boundaries
5. Add proper logging
6. Write tests for critical functionality

### Common Issues and Solutions
1. **S3 Permission Issues**
   - Check AWS credentials
   - Verify bucket policy
   - Ensure CORS configuration

2. **Database Connection**
   - Verify DATABASE_URL
   - Check PostgreSQL service
   - Run migrations

3. **Authentication Errors**
   - Verify OAuth credentials
   - Check NEXTAUTH_URL
   - Ensure proper callback URLs

## API Documentation

### File Upload API
\`\`\`typescript
POST /api/upload
Content-Type: multipart/form-data

Response:
{
  url: string;  // Signed URL for the uploaded file
  key: string;  // S3 object key
}
\`\`\`

### Application API
\`\`\`typescript
GET /api/applications
Response: Application[]

POST /api/applications
Body: {
  jobId: string;
  resumeId: string;
  status: string;
}

PATCH /api/applications/:id
Body: {
  status?: string;
  notes?: string;
}
\`\`\`

## Contributing
Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests. 