# AI-Powered Job Application Assistant

An intelligent job application automation system that helps streamline your job search process using AI and automation.

## Features

- **Smart Resume Management**
  - PDF resume parsing and analysis
  - Automatic resume tailoring for specific jobs
  - Skills and experience extraction
  - Vector storage for efficient matching

- **Multi-Platform Job Search**
  - Integration with LinkedIn, Indeed (RSS feed and scraping), and other platforms
  - Automated job matching based on your profile
  - Smart filtering and ranking of opportunities
  - Both internal and external application support

- **AI-Powered Features**
  - Resume-job matching analysis
  - Automatic cover letter generation
  - Job description analysis
  - Application success prediction

- **Automated Application Process**
  - One-click applications for supported platforms
  - Automated form filling for external applications
  - Application tracking and status monitoring
  - Smart duplicate detection

## Technology Stack

- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Backend**: Node.js, Prisma
- **AI/ML**: OpenAI GPT-4, LangChain
- **Vector Database**: Pinecone
- **Web Automation**: Puppeteer
- **Job Data Sources**: Indeed RSS feed, web scraping
- **Other Tools**: PDF parsing, form automation

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/job-applier-app.git
   cd job-applier-app
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Fill in your API keys and configuration values in the `.env` file.

4. Initialize the database:
   ```bash
   npx prisma generate
   npx prisma db push
   ```

5. Run the development server:
   ```bash
   npm run dev
   ```

6. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Configuration

The application requires several API keys and configurations to work properly:

- OpenAI API key for AI features
- Pinecone API key for vector storage
- LinkedIn API credentials (optional)
- Indeed configuration:
  - RSS feed (enabled by default, no API key required)
  - Scraping fallback (with Puppeteer support)
- PostgreSQL database connection

Refer to `.env.example` for all required environment variables.

## Indeed Integration

The application supports two methods for fetching Indeed job listings:

1. **RSS Feed** (Recommended): Uses Indeed's public RSS feed to fetch job listings without requiring an API key. This method is more reliable and less likely to be blocked.
   - Enable with `INDEED_USE_RSS_FEED=true` in your `.env` file
   - Supports pagination to fetch more than the default 25 results per request
   - Provides structured job data with minimal processing

2. **Web Scraping** (Fallback): Uses direct HTTP requests and Puppeteer for headless browsing when the RSS feed is not available.
   - Configure with `INDEED_ENABLE_PUPPETEER` and `INDEED_MAX_RETRIES` in your `.env` file
   - Used automatically if RSS feed is disabled or fails

## Usage

1. **Profile Setup**
   - Upload your resume
   - Connect your LinkedIn profile (optional)
   - Set your job preferences

2. **Job Search**
   - Select target platforms
   - Set search criteria
   - Review matched opportunities

3. **Application Process**
   - Review job-specific resume suggestions
   - Generate tailored cover letters
   - Submit applications automatically

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is designed to assist with job applications but should be used responsibly and in accordance with each job platform's terms of service. Always review applications before submission and ensure compliance with platform policies.
