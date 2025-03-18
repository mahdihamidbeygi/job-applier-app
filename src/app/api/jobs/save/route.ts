import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { auth } from "@/lib/auth";
import { PrismaClientKnownRequestError } from "@prisma/client/runtime/library";

export async function POST(request: Request) {
  const session = await auth();

  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = await request.json();
    const { jobId } = body;

    if (!jobId) {
      return NextResponse.json(
        { error: "Job ID is required" },
        { status: 400 }
      );
    }

    // Check if the job exists
    const job = await prisma.job.findUnique({
      where: {
        id: jobId,
      },
    });

    if (!job) {
      return NextResponse.json(
        { error: "Job not found. Cannot save a non-existent job." },
        { status: 404 }
      );
    }

    // Check if the job is already saved
    const existingSavedJob = await prisma.savedJob.findFirst({
      where: {
        userId: session.user.id,
        jobId,
      },
    });

    if (existingSavedJob) {
      return NextResponse.json(
        { message: "Job already saved" },
        { status: 200 }
      );
    }

    // Create the saved job record
    const savedJob = await prisma.savedJob.create({
      data: {
        userId: session.user.id,
        jobId,
      },
    });

    return NextResponse.json(savedJob);
  } catch (error: unknown) {
    console.error("Error saving job:", error);
    
    // Handle Prisma errors more specifically
    if (error instanceof PrismaClientKnownRequestError) {
      if (error.code === 'P2003') {
        return NextResponse.json(
          { error: "Foreign key constraint violation. The job or user does not exist." },
          { status: 400 }
        );
      }
    }
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: "Internal Server Error", details: errorMessage },
      { status: 500 }
    );
  }
}

export async function DELETE(request: Request) {
  const session = await auth();

  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = await request.json();
    const { jobId } = body;

    if (!jobId) {
      return NextResponse.json(
        { error: "Job ID is required" },
        { status: 400 }
      );
    }

    const savedJob = await prisma.savedJob.findFirst({
      where: {
        userId: session.user.id,
        jobId,
      },
    });

    if (!savedJob) {
      return NextResponse.json(
        { error: "Saved job not found" },
        { status: 404 }
      );
    }

    await prisma.savedJob.delete({
      where: {
        id: savedJob.id,
      },
    });

    return NextResponse.json({ success: true });
  } catch (error: unknown) {
    console.error("Error unsaving job:", error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: "Internal Server Error", details: errorMessage },
      { status: 500 }
    );
  }
} 