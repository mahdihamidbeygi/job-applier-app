import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { PDFDocument, StandardFonts } from "pdf-lib";
import { NextResponse } from "next/server";

// Helper function to sanitize text for PDF
function sanitizeText(text: string): string {
  return text
    .replace(/[\u2010-\u2015]/g, '-') // Replace various hyphens with simple hyphen
    .replace(/[^\x00-\x7F]/g, '') // Remove non-ASCII characters
    .replace(/\s+/g, ' ') // Normalize whitespace
    .trim();
}

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const session = await auth();
    if (!session?.user) {
      return new Response("Unauthorized", { status: 401 });
    }

    // Ensure params is resolved
    const resolvedParams = await Promise.resolve(params);
    const jobId = resolvedParams.id;

    const job = await prisma.job.findUnique({
      where: { id: jobId }
    });

    if (!job) {
      return new Response("Job not found", { status: 404 });
    }

    const userProfile = await prisma.userProfile.findUnique({
      where: { userId: session.user.id },
      include: {
        experience: true,
        education: true,
        skills: true
      }
    });

    if (!userProfile) {
      return new Response("User profile not found", { status: 404 });
    }

    // Create PDF document
    const pdfDoc = await PDFDocument.create();
    const page = pdfDoc.addPage();
    const height = page.getHeight();
    const margin = 50;
    const lineHeight = 15;
    let yOffset = height - margin;
    const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const fontSize = 12;

    // Header
    page.drawText(sanitizeText(userProfile.name), {
      x: 50,
      y: yOffset,
      size: 24,
      font,
    });
    yOffset -= 30;

    page.drawText(sanitizeText(userProfile.email), {
      x: 50,
      y: yOffset,
      size: fontSize,
      font,
    });
    yOffset -= lineHeight;

    if (userProfile.phone) {
      page.drawText(sanitizeText(userProfile.phone), {
        x: 50,
        y: yOffset,
        size: fontSize,
        font,
      });
      yOffset -= lineHeight;
    }

    if (userProfile.location) {
      page.drawText(sanitizeText(userProfile.location), {
        x: 50,
        y: yOffset,
        size: fontSize,
        font,
      });
      yOffset -= lineHeight;
    }

    // Summary
    if (userProfile.summary) {
      yOffset -= lineHeight;
      page.drawText("Professional Summary", {
        x: 50,
        y: yOffset,
        size: 16,
        font,
      });
      yOffset -= lineHeight;

      const summaryLines = sanitizeText(userProfile.summary).split("\n");
      for (const line of summaryLines) {
        page.drawText(sanitizeText(line), {
          x: 50,
          y: yOffset,
          size: fontSize,
          font,
        });
        yOffset -= lineHeight;
      }
    }

    // Experience
    yOffset -= lineHeight;
    page.drawText("Experience", {
      x: 50,
      y: yOffset,
      size: 16,
      font,
    });
    yOffset -= lineHeight;

    for (const exp of userProfile.experience) {
      page.drawText(sanitizeText(`${exp.title} at ${exp.company}`), {
        x: 50,
        y: yOffset,
        size: fontSize + 2,
        font,
      });
      yOffset -= lineHeight;

      page.drawText(sanitizeText(exp.location), {
        x: 50,
        y: yOffset,
        size: fontSize,
        font,
      });
      yOffset -= lineHeight;

      const descLines = sanitizeText(exp.description).split("\n");
      for (const line of descLines) {
        page.drawText(sanitizeText(line), {
          x: 70,
          y: yOffset,
          size: fontSize,
          font,
        });
        yOffset -= lineHeight;
      }
      yOffset -= lineHeight;
    }

    // Education
    yOffset -= lineHeight;
    page.drawText("Education", {
      x: 50,
      y: yOffset,
      size: 16,
      font,
    });
    yOffset -= lineHeight;

    for (const edu of userProfile.education) {
      page.drawText(sanitizeText(`${edu.degree} in ${edu.field}`), {
        x: 50,
        y: yOffset,
        size: fontSize + 2,
        font,
      });
      yOffset -= lineHeight;

      page.drawText(sanitizeText(edu.school), {
        x: 50,
        y: yOffset,
        size: fontSize,
        font,
      });
      yOffset -= lineHeight;

      if (edu.description) {
        const descLines = sanitizeText(edu.description).split("\n");
        for (const line of descLines) {
          page.drawText(sanitizeText(line), {
            x: 70,
            y: yOffset,
            size: fontSize,
            font,
          });
          yOffset -= lineHeight;
        }
      }
      yOffset -= lineHeight;
    }

    // Skills
    yOffset -= lineHeight;
    page.drawText("Skills", {
      x: 50,
      y: yOffset,
      size: 16,
      font,
    });
    yOffset -= lineHeight;

    const skillsText = userProfile.skills.map(skill => sanitizeText(skill.name)).join(", ");
    page.drawText(skillsText, {
      x: 50,
      y: yOffset,
      size: fontSize,
      font,
    });

    const pdfBytes = await pdfDoc.save();

    return new NextResponse(pdfBytes, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="resume-${sanitizeText(job.company)}.pdf"`,
      },
    });
  } catch (error) {
    console.error("Error generating resume:", error);
    return new Response("Error generating resume", { status: 500 });
  }
} 