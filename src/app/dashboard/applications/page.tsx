import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import ApplicationCard from "@/components/ApplicationCard";
import ApplicationFilters from "@/components/ApplicationFilters";
import { ApplicationStatus, type JobApplication } from "@/types/application";

const applicationStatuses = Object.values(ApplicationStatus);

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function ApplicationsPage({
  searchParams,
}: PageProps) {
  const session = await auth();
  
  if (!session?.user?.id) {
    return null;
  }

  const userId = session.user.id;
  const params = await searchParams;
  const statusParam = String(params['status'] ?? '');
  const status = applicationStatuses.includes(statusParam as ApplicationStatus)
    ? (statusParam as ApplicationStatus)
    : undefined;
  const search = String(params['search'] ?? '');

  const applications = await prisma.jobApplication.findMany({
    where: {
      userId,
      ...(status ? { status } : {}),
      OR: search ? [
        { job: { title: { contains: search, mode: 'insensitive' } } },
        { job: { company: { contains: search, mode: 'insensitive' } } },
      ] : undefined,
    },
    include: {
      job: true,
    },
    orderBy: [
      { appliedAt: 'desc' },
    ],
  }) as JobApplication[];

  // Group applications by status
  const groupedApplications = applicationStatuses.reduce<Record<ApplicationStatus, JobApplication[]>>((acc, status) => {
    acc[status] = applications.filter(app => app.status === status);
    return acc;
  }, {} as Record<ApplicationStatus, JobApplication[]>);

  return (
    <div className="space-y-6">
      <div className="bg-slate-800 shadow rounded-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-slate-100">Job Applications</h1>
          <ApplicationFilters />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {applicationStatuses.map((status) => (
            <div key={status} className="bg-slate-700 p-4 rounded-lg">
              <h2 className="text-lg font-semibold text-slate-100 mb-4 flex justify-between items-center">
                {status.charAt(0) + status.slice(1).toLowerCase()}
                <span className="text-sm font-normal text-slate-300">
                  {groupedApplications[status].length}
                </span>
              </h2>
              <div className="space-y-4">
                {groupedApplications[status].map((application) => (
                  <ApplicationCard
                    key={application.id}
                    application={application}
                  />
                ))}
                {groupedApplications[status].length === 0 && (
                  <p className="text-sm text-slate-400 text-center py-4">
                    No applications in this status
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
} 