import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import DateFormatter from "@/components/DateFormatter";

export default async function DashboardPage() {
  const session = await auth();
  
  if (!session?.user?.id) {
    return null;
  }

  const [applications, savedJobs] = await Promise.all([
    prisma.jobApplication.findMany({
      where: { userId: session.user.id },
      include: { job: true },
      orderBy: { appliedAt: 'desc' },
      take: 5,
    }),
    prisma.savedJob.findMany({
      where: { userId: session.user.id },
      include: { job: true },
      orderBy: { savedAt: 'desc' },
      take: 5,
    }),
  ]);

  const applicationStats = await prisma.jobApplication.groupBy({
    by: ['status'],
    where: { userId: session.user.id },
    _count: true,
  });

  return (
    <div className="space-y-6">
      <div className="bg-slate-800 shadow rounded-lg p-6">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">Application Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {applicationStats.map((stat) => (
            <div key={stat.status} className="bg-slate-700 p-4 rounded-lg">
              <dt className="text-sm font-medium text-slate-300">{stat.status}</dt>
              <dd className="mt-1 text-3xl font-semibold text-slate-100">{stat._count}</dd>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-800 shadow rounded-lg p-6">
          <h2 className="text-xl font-bold text-slate-100 mb-4">Recent Applications</h2>
          <div className="space-y-4">
            {applications.map((application) => (
              <div key={application.id} className="border-b border-slate-700 pb-4">
                <h3 className="text-lg font-medium text-slate-100">{application.job.title}</h3>
                <p className="text-sm text-slate-300">{application.job.company}</p>
                <div className="mt-2 flex justify-between items-center">
                  <span className="text-sm text-slate-400">
                    Applied <DateFormatter date={application.appliedAt} />
                  </span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-900 text-blue-200">
                    {application.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-800 shadow rounded-lg p-6">
          <h2 className="text-xl font-bold text-slate-100 mb-4">Saved Jobs</h2>
          <div className="space-y-4">
            {savedJobs.map((saved) => (
              <div key={saved.id} className="border-b border-slate-700 pb-4">
                <h3 className="text-lg font-medium text-slate-100">{saved.job.title}</h3>
                <p className="text-sm text-slate-300">{saved.job.company}</p>
                <div className="mt-2 flex justify-between items-center">
                  <span className="text-sm text-slate-400">
                    Saved <DateFormatter date={saved.savedAt} />
                  </span>
                  <a
                    href={saved.job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-indigo-400 hover:text-indigo-300"
                  >
                    View Job
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
} 