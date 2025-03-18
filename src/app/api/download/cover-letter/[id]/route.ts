import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { PDFDocument, StandardFonts } from "pdf-lib";
import { NextResponse } from "next/server";
import { format } from "date-fns";

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return new Response("Unauthorized", { status: 401 });
    }

    const job = await prisma.job.findUnique({
      where: { id: params.id }
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
    const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const fontSize = 12;
    const lineHeight = fontSize * 1.2;
    const { height } = page.getSize();

    let yOffset = height - 50;

    // Date
    const today = format(new Date(), "MMMM d, yyyy");
    page.drawText(today, {
      x: 50,
      y: yOffset,
      size: fontSize,
      font,
    });
    yOffset -= lineHeight * 2;

    // Company Information
    page.drawText(job.company, {
      x: 50,
      y: yOffset,
      size: fontSize,
      font,
    });
    yOffset -= lineHeight;

    if (job.location) {
      page.drawText(job.location, {
        x: 50,
        y: yOffset,
        size: fontSize,
        font,
      });
      yOffset -= lineHeight * 2;
    }

    // Salutation
    page.drawText("Dear Hiring Manager,", {
      x: 50,
      y: yOffset,
      size: fontSize,
      font,
    });
    yOffset -= lineHeight * 2;

    // Opening Paragraph
    const openingText = `I am writing to express my strong interest in the ${job.title} position at ${job.company}. With my background in ${userProfile.experience[0]?.title || "relevant field"} and passion for ${job.company}, I am confident in my ability to contribute effectively to your team.`;
    const openingLines = splitTextIntoLines(openingText, 80);
    for (const line of openingLines) {
      page.drawText(line, {
        x: 50,
        y: yOffset,
        size: fontSize,
        font,
      });
      yOffset -= lineHeight;
    }
    yOffset -= lineHeight;

    // Experience Paragraph
    const latestExperience = userProfile.experience[0];
    if (latestExperience) {
      const experienceText = `In my current role as ${latestExperience.title} at ${latestExperience.company}, I have developed strong skills in ${latestExperience.description}. This experience has prepared me well for the challenges and opportunities that come with the ${job.title} position.`;
      const experienceLines = splitTextIntoLines(experienceText, 80);
      for (const line of experienceLines) {
        page.drawText(line, {
          x: 50,
          y: yOffset,
          size: fontSize,
          font,
        });
        yOffset -= lineHeight;
      }
      yOffset -= lineHeight;
    }

    // Skills Paragraph
    if (userProfile.skills.length > 0) {
      const skillsText = `My key skills include ${userProfile.skills.map(skill => skill.name).join(", ")}, which align well with the requirements of this position.`;
      const skillsLines = splitTextIntoLines(skillsText, 80);
      for (const line of skillsLines) {
        page.drawText(line, {
          x: 50,
          y: yOffset,
          size: fontSize,
          font,
        });
        yOffset -= lineHeight;
      }
      yOffset -= lineHeight;
    }

    // Closing
    const closingText = `I am excited about the opportunity to bring my skills and experience to ${job.company} and would welcome the chance to discuss how I can contribute to your team.`;
    const closingLines = splitTextIntoLines(closingText, 80);
    for (const line of closingLines) {
      page.drawText(line, {
        x: 50,
        y: yOffset,
        size: fontSize,
        font,
      });
      yOffset -= lineHeight;
    }
    yOffset -= lineHeight * 2;

    // Signature
    page.drawText("Sincerely,", {
      x: 50,
      y: yOffset,
      size: fontSize,
      font,
    });
    yOffset -= lineHeight * 2;

    page.drawText(userProfile.name, {
      x: 50,
      y: yOffset,
      size: fontSize,
      font,
    });
    yOffset -= lineHeight;

    page.drawText(userProfile.email, {
      x: 50,
      y: yOffset,
      size: fontSize,
      font,
    });
    yOffset -= lineHeight;

    if (userProfile.phone) {
      page.drawText(userProfile.phone, {
        x: 50,
        y: yOffset,
        size: fontSize,
        font,
      });
    }

    const pdfBytes = await pdfDoc.save();

    return new NextResponse(pdfBytes, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="cover-letter-${job.company}.pdf"`,
      },
    });
  } catch (error) {
    console.error("Error generating cover letter:", error);
    return new Response("Error generating cover letter", { status: 500 });
  }
}

function splitTextIntoLines(text: string, maxCharsPerLine: number): string[] {
  const words = text.split(" ");
  const lines: string[] = [];
  let currentLine = "";

  for (const word of words) {
    if (currentLine.length + word.length + 1 <= maxCharsPerLine) {
      currentLine += (currentLine.length === 0 ? "" : " ") + word;
    } else {
      lines.push(currentLine);
      currentLine = word;
    }
  }

  if (currentLine.length > 0) {
    lines.push(currentLine);
  }

  return lines;
} 