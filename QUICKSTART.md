# Quick Start Guide - Job Application Automation System

## Essential Packages Overview

### 1. Next.js
- **What it does**: Modern React framework for building web applications
- **Why we use it**: Provides server-side rendering, routing, and API routes
- **Key features we use**:
  - App Router
  - Server Components
  - API Routes
  - Built-in TypeScript support

### 2. AWS SDK v3
- **What it does**: Interacts with AWS services
- **Why we use it**: Handles file storage in S3
- **Main packages**:
  - `@aws-sdk/client-s3`: Core S3 operations
  - `@aws-sdk/s3-request-presigner`: Generate temporary URLs for files

### 3. Prisma
- **What it does**: Database ORM (Object-Relational Mapping)
- **Why we use it**: Makes database operations type-safe and easy
- **Key features**:
  - Auto-generated TypeScript types
  - SQL query builder
  - Schema management

### 4. NextAuth.js
- **What it does**: Authentication for Next.js
- **Why we use it**: Handles user login/sessions
- **Features we use**:
  - Google OAuth
  - Session management
  - Protected routes

## Quick Setup Steps

1. **Install Node.js dependencies**:
   \`\`\`bash
   npm install
   \`\`\`

2. **Set up PostgreSQL database**:
   \`\`\`bash
   # Create database and user
   sudo -u postgres psql
   CREATE DATABASE jobapplier;
   CREATE USER jobapplier WITH PASSWORD 'password';
   GRANT ALL PRIVILEGES ON DATABASE jobapplier TO jobapplier;
   \`\`\`

3. **Configure AWS S3**:
   - Create S3 bucket
   - Get access keys
   - Set up bucket policy

4. **Set up environment**:
   \`\`\`bash
   cp .env.example .env
   # Edit .env with your values
   \`\`\`

5. **Initialize database**:
   \`\`\`bash
   npx prisma generate
   npx prisma db push
   \`\`\`

6. **Start development server**:
   \`\`\`bash
   npm run dev
   \`\`\`

## Common Commands

### Database Operations
\`\`\`bash
# Generate Prisma client
npx prisma generate

# Push schema changes
npx prisma db push

# Open Prisma Studio (database UI)
npx prisma studio
\`\`\`

### Development
\`\`\`bash
# Start dev server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint
\`\`\`

### Testing
\`\`\`bash
# Run tests
npm test

# Test file upload
npx ts-node -P src/scripts/tsconfig.json src/scripts/test-upload.ts
\`\`\`

## Key Files and Directories

\`\`\`
job-applier-app/
├── src/
│   ├── app/              # Next.js app router
│   ├── components/       # React components
│   ├── lib/             # Utility functions
│   └── services/        # Business logic
├── prisma/
│   └── schema.prisma    # Database schema
├── public/              # Static files
└── .env                 # Environment variables
\`\`\`

## Getting Help

1. **Database Issues**:
   - Check DATABASE_URL in .env
   - Verify PostgreSQL is running
   - Check user permissions

2. **AWS Issues**:
   - Verify AWS credentials
   - Check S3 bucket permissions
   - Confirm CORS settings

3. **Authentication Issues**:
   - Verify Google OAuth credentials
   - Check NEXTAUTH_URL setting
   - Ensure callback URLs are correct

## Next Steps

1. Set up your development environment
2. Create a test user
3. Upload a test resume
4. Create your first job application

For detailed documentation, see DOCUMENTATION.md 