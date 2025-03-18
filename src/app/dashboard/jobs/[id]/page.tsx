import { Metadata } from "next";
import { notFound } from "next/navigation";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import JobDetailsClient from "./JobDetailsClient";

interface JobDetailsPageProps {
  params: {
    id: string;
  };
}

export async function generateMetadata({ params }: JobDetailsPageProps): Promise<Metadata> {
  const resolvedParams = await Promise.resolve(params);
  const job = await prisma.job.findFirst({
    where: {
      OR: [
        { id: resolvedParams.id },
        { id: { contains: resolvedParams.id.split('-').pop() || '' } }
      ]
    }
  });

  if (!job) {
    return {
      title: "Job Not Found",
      description: "The job you&apos;re looking for doesn&apos;t exist or has been removed."
    };
  }

  return {
    title: `${job.title} at ${job.company}`,
    description: `Job opportunity for ${job.title} position at ${job.company}`,
  };
}

export default async function JobDetailsPage({ params }: JobDetailsPageProps) {
  try {
    const resolvedParams = await Promise.resolve(params);
    const jobId = resolvedParams.id;
    const lastIdPart = jobId.split('-').pop() || '';
    
    console.log('Attempting to fetch job with ID:', jobId);
    console.log('Last part of ID:', lastIdPart);

    const session = await auth();
    
    if (!session?.user?.id) {
      console.log('No authenticated user found');
      return notFound();
    }
    console.log('Authenticated user ID:', session.user.id);

    const [job, userProfile] = await Promise.all([
      prisma.job.findFirst({
        where: {
          OR: [
            { id: jobId },
            { id: { contains: lastIdPart } }
          ]
        }
      }),
      prisma.userProfile.findUnique({
        where: { userId: session.user.id },
        include: {
          skills: true,
          experience: true,
          education: true,
        },
      }),
    ]);

    console.log('Found job:', job ? 'Yes' : 'No');
    console.log('Found user profile:', userProfile ? 'Yes' : 'No');

    if (!job) {
      console.log('Job not found in database');
      notFound();
    }

    if (!userProfile) {
      console.log('User profile not found');
      throw new Error("Please complete your profile before applying to jobs");
    }

    return (
      <div className="min-h-screen bg-background">
        <JobDetailsClient job={job} userProfile={userProfile} />
      </div>
    );
  } catch (error) {
    console.error('Error in JobDetailsPage:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("An unexpected error occurred");
  }
} 