import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { auth } from "@/lib/auth";

export async function GET(
  request: Request,
  context: { params: { id: string } }
) {
  const session = await auth();

  if (!session?.user?.id) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  try {
    const params = await context.params;
    const jobId = params.id;

    if (!jobId) {
      return new NextResponse("Job ID is required", { status: 400 });
    }

    // Find the application for this job and user
    const application = await prisma.jobApplication.findFirst({
      where: {
        jobId,
        userId: session.user.id,
      },
      include: {
        job: true,
      },
    });

    if (!application) {
      return new NextResponse("Application not found", { status: 404 });
    }

    return NextResponse.json(application);
  } catch (error) {
    console.error("Error fetching application:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
  }
} 