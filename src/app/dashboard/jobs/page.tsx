import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import EnhancedJobSearchForm from "@/components/EnhancedJobSearchForm";
import JobCard from "@/components/JobCard";
import { JobService } from "@/services/jobService";
import { Job } from "@/services/jobAggregatorService";

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function JobsPage({
  searchParams,
}: PageProps) {
  const session = await auth();
  
  if (!session?.user?.id) {
    return null;
  }

  const userId = session.user.id;
  const params = await searchParams;
  const query = String(params['q'] ?? '');
  const location = String(params['location'] ?? '');
  const type = String(params['type'] ?? '');
  
  // Ensure platforms is always an array
  let platforms: string[] = [];
  if (params['platforms']) {
    // If platforms is a string, convert it to an array with a single element
    if (typeof params['platforms'] === 'string') {
      platforms = [params['platforms']];
    } 
    // If platforms is already an array, use it as is
    else if (Array.isArray(params['platforms'])) {
      platforms = params['platforms'] as string[];
    }
  }

  // Default to LinkedIn and Indeed if no platforms specified
  if (platforms.length === 0) {
    platforms = ['linkedin'];
  }

  console.log(`Searching for jobs with query: "${query}", location: "${location}", type: "${type}", platforms:`, platforms);

  // Get jobs from database
  const jobs = await prisma.job.findMany({
    where: {
      AND: [
        {
          OR: [
            { title: { contains: query, mode: 'insensitive' } },
            { company: { contains: query, mode: 'insensitive' } },
            { description: { contains: query, mode: 'insensitive' } },
          ],
        },
        location ? { location: { contains: location, mode: 'insensitive' } } : {},
        type ? { jobType: { equals: type } } : {},
      ],
    },
    orderBy: { postedAt: 'desc' },
    include: {
      savedJobs: {
        where: { userId },
      },
    },
  });

  const savedJobIds = new Set(jobs.flatMap(job => 
    job.savedJobs.map(saved => saved.jobId)
  ));

  // Get external jobs if query is provided
  let externalJobs: Job[] = [];
  let scrapingErrors: string[] = [];
  
  if (query) {
    try {
      const jobService = new JobService();
      const result = await jobService.searchJobs(
        query, 
        location || undefined, 
        type || undefined, 
        platforms
      );
      
      externalJobs = result.jobs;
      scrapingErrors = result.errors;

      // Log the number of external jobs found
      console.log(`Found ${externalJobs.length} external jobs from platforms: ${platforms.join(', ')}`);
      
      // Store external jobs in database
      const storedJobs = await Promise.all(
        externalJobs.map(async (job) => {
          try {
            // Check if job already exists
            const existingJob = await prisma.job.findFirst({
              where: {
                OR: [
                  { externalId: job.externalId },
                  { url: job.url }
                ]
              }
            });

            if (existingJob) {
              console.log(`Job already exists in database: ${existingJob.id}`);
              return existingJob;
            }

            // Create new job in database
            const newJob = await prisma.job.create({
              data: {
                platform: job.platform,
                externalId: job.externalId,
                title: job.title,
                company: job.company,
                location: job.location || null,
                description: job.description || '',
                salary: job.salary || null,
                jobType: job.jobType || null,
                url: job.url,
                postedAt: job.postedAt || new Date(),
                isExternal: true
              }
            });
            console.log(`Stored new job in database: ${newJob.id}`);
            return newJob;
          } catch (error) {
            console.error('Error storing job:', error);
            return job; // Return original job if storage fails
          }
        })
      );

      // Replace external jobs with stored versions
      externalJobs = storedJobs;
      
      // Validate external jobs
      externalJobs = externalJobs.filter(job => {
        // Log job details for debugging
        console.log(`Validating job: platform=${job.platform}, id=${job.id || job.externalId}, title=${job.title ? 'present' : 'missing'}, company=${job.company ? 'present' : 'missing'}`);
        
        // Ensure job has required fields
        if (!job.title || !job.company) {
          console.log(`Filtering out job with missing title or company: ${job.id || job.externalId}`);
          
          // For LinkedIn jobs, try to provide default values instead of filtering
          if (job.platform.toLowerCase() === 'linkedin') {
            console.log(`Attempting to fix LinkedIn job ${job.id || job.externalId}`);
            job.title = job.title || `LinkedIn Job ${job.externalId}`;
            job.company = job.company || 'LinkedIn Company';
            return true;
          }
          
          return false;
        }
        
        // Ensure job has a URL
        if (!job.url) {
          console.log(`Job ${job.id || job.externalId} is missing URL, attempting to construct one`);
          // Try to construct a URL based on the platform
          switch (job.platform.toLowerCase()) {
            case 'linkedin':
              job.url = `https://www.linkedin.com/jobs/view/${job.externalId}`;
              break;
            case 'glassdoor':
              job.url = `https://www.glassdoor.com/job-listing/${job.externalId}`;
              break;
            default:
              // If we can't determine a valid URL, use a placeholder
              console.log(`Cannot construct URL for job ${job.id || job.externalId} from platform ${job.platform}`);
              job.url = `https://example.com/jobs/${job.platform}/${job.externalId}`;
              break;
          }
          console.log(`Constructed URL for job ${job.id || job.externalId}: ${job.url}`);
        }
        
        // Ensure URL is valid (starts with http)
        if (!job.url.startsWith('http')) {
          console.log(`Job ${job.id || job.externalId} has invalid URL: ${job.url}, fixing it`);
          job.url = `https://${job.url}`;
          console.log(`Fixed URL for job ${job.id || job.externalId}: ${job.url}`);
        }
        
        return true;
      });
    } catch (error) {
      console.error('Error fetching external jobs:', error);
      scrapingErrors.push(error instanceof Error ? error.message : String(error));
      // Continue with empty external jobs array
    }
  }

  // Combine database jobs with external jobs
  const allJobs = [
    ...jobs,
    ...externalJobs.filter(job => !savedJobIds.has(job.id))
  ];

  return (
    <div className="space-y-6">
      <div className="bg-slate-800 shadow rounded-lg p-6">
        <h1 className="text-2xl font-bold text-slate-100 mb-6">Find Jobs</h1>
        <EnhancedJobSearchForm initialValues={{ 
          query, 
          location, 
          type,
          platforms: platforms.length ? platforms : undefined
        }} />
      </div>

      {scrapingErrors.length > 0 && (
        <div className="bg-yellow-900 border-l-4 border-yellow-500 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-300" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-200">
                Some job sources couldn&apos;t be accessed. Results may be incomplete.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6">
        {allJobs.length > 0 ? (
          allJobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              isSaved={savedJobIds.has(job.id)}
              userId={userId}
            />
          ))
        ) : (
          <div className="bg-slate-800 shadow rounded-lg p-6 text-center">
            <p className="text-slate-300">
              {query 
                ? "No jobs found matching your criteria. Try broadening your search or selecting different platforms."
                : "Enter a search query to find jobs."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
} 