import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="max-w-md w-full">
        <CardHeader>
          <CardTitle>Job Not Found</CardTitle>
          <CardDescription>
            The job you&apos;re looking for doesn&apos;t exist or has been removed.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild className="w-full">
            <Link href="/dashboard/jobs">
              Back to Jobs
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
} 