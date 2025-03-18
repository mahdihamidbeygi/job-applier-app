import { Metadata } from "next";
import { notFound } from "next/navigation";
import { prisma } from "@/lib/prisma";
import ApplicationDetails from "@/components/ApplicationDetails";

interface ApplicationPageProps {
  params: {
    id: string;
  };
}

export async function generateMetadata(
  { params }: ApplicationPageProps
): Promise<Metadata> {
  // Ensure params is resolved
  const applicationId = await Promise.resolve(params.id);
  
  try {
    const application = await prisma.jobApplication.findUnique({
      where: { id: applicationId },
      include: {
        job: true,
      },
    });

    if (!application) {
      return {
        title: 'Application Not Found',
        description: 'The requested application could not be found.',
      };
    }

    return {
      title: `${application.job.title} at ${application.job.company}`,
      description: `Application details for ${application.job.title} position at ${application.job.company}`,
    };
  } catch (error) {
    console.error('Error generating metadata:', error);
    return {
      title: 'Application Details',
      description: 'View your job application details',
    };
  }
}

export default async function ApplicationPage({ params }: ApplicationPageProps) {
  // Ensure params is resolved
  const applicationId = await Promise.resolve(params.id);
  
  if (!applicationId) {
    notFound();
  }

  try {
    const application = await prisma.jobApplication.findUnique({
      where: { id: applicationId },
      include: {
        job: true,
      },
    });

    // If application not found, return 404
    if (!application) {
      notFound();
    }

    return (
      <div className="container mx-auto px-4 py-8">
        <ApplicationDetails application={application} />
      </div>
    );
  } catch (error) {
    console.error('Error fetching application:', error);
    throw error;
  }
} 