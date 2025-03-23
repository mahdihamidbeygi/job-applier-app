import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-slate-900">
      <Card className="max-w-md w-full bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Job Not Found</CardTitle>
          <CardDescription className="text-slate-300">
            The job you&apos;re looking for doesn&apos;t exist or has been removed.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild className="w-full bg-indigo-600 hover:bg-indigo-700 text-slate-100">
            <Link href="/dashboard/jobs">
              Back to Jobs
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
} 