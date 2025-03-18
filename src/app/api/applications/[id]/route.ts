import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { auth } from "@/lib/auth";

export async function PATCH(
  request: Request,
  { params }: { params: { id: string } }
) {
  const session = await auth();

  if (!session?.user?.id) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  // Ensure params.id exists
  const id = params?.id;
  if (!id) {
    return new NextResponse("Invalid application ID", { status: 400 });
  }

  try {
    const body = await request.json();
    const { status, notes, resumeUsed, coverLetter } = body;

    // Verify the application belongs to the user
    const application = await prisma.jobApplication.findUnique({
      where: {
        id,
        userId: session.user.id,
      },
    });

    if (!application) {
      return new NextResponse("Not found", { status: 404 });
    }

    const updatedApplication = await prisma.jobApplication.update({
      where: {
        id,
      },
      data: {
        ...(status && { status }),
        ...(notes && { notes }),
        ...(resumeUsed && { resumeUsed }),
        ...(coverLetter && { coverLetter }),
      },
      include: {
        job: true,
      },
    });

    return NextResponse.json(updatedApplication);
  } catch (error) {
    console.error("Error updating application:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
  }
}

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const session = await auth();

  if (!session?.user?.id) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  // Ensure params.id exists
  const id = params?.id;
  if (!id) {
    return new NextResponse("Invalid application ID", { status: 400 });
  }

  try {
    const application = await prisma.jobApplication.findUnique({
      where: {
        id,
        userId: session.user.id,
      },
      include: {
        job: true,
      },
    });

    if (!application) {
      return new NextResponse("Not found", { status: 404 });
    }

    return NextResponse.json(application);
  } catch (error) {
    console.error("Error fetching application:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: { id: string } }
) {
  const session = await auth();

  if (!session?.user?.id) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  // Ensure params.id exists
  const id = params?.id;
  if (!id) {
    return new NextResponse("Invalid application ID", { status: 400 });
  }

  try {
    // Verify the application belongs to the user
    const application = await prisma.jobApplication.findUnique({
      where: {
        id,
        userId: session.user.id,
      },
    });

    if (!application) {
      return new NextResponse("Not found", { status: 404 });
    }

    await prisma.jobApplication.delete({
      where: {
        id,
      },
    });

    return new NextResponse(null, { status: 204 });
  } catch (error) {
    console.error("Error deleting application:", error);
    return new NextResponse("Internal Server Error", { status: 500 });
  }
} 