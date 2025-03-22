import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import SignOutButton from "@/components/SignOutButton";
import Link from "next/link";
import Image from "next/image";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();

  if (!session) {
    redirect("/auth/signin");
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <nav className="bg-slate-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-slate-100">Job Applier</h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link
                  href="/dashboard"
                  className="border-indigo-500 text-slate-100 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Dashboard
                </Link>
                <Link
                  href="/dashboard/jobs"
                  className="border-transparent text-slate-300 hover:border-slate-300 hover:text-slate-100 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Jobs
                </Link>
                <Link
                  href="/dashboard/applications"
                  className="border-transparent text-slate-300 hover:border-slate-300 hover:text-slate-100 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Applications
                </Link>
                <Link
                  href="/dashboard/tailoring"
                  className="border-transparent text-slate-300 hover:border-slate-300 hover:text-slate-100 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Tailor Documents
                </Link>
                <Link
                  href="/dashboard/profile"
                  className="border-transparent text-slate-300 hover:border-slate-300 hover:text-slate-100 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Profile
                </Link>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex-shrink-0">
                <Image
                  width={32}
                  height={32}
                  className="rounded-full"
                  src={session.user?.image || `https://ui-avatars.com/api/?name=${session.user?.name}`}
                  alt={session.user?.name || "User"}
                />
              </div>
              <SignOutButton />
            </div>
          </div>
        </div>
      </nav>
      <main>
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">{children}</div>
      </main>
    </div>
  );
} 