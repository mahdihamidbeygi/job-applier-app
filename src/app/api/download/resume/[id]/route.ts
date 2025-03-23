import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { convertMarkdownToPDF } from '@/lib/pdfConverter';
import { ResumeData } from '@/types/resume';
import { Skill, Experience, Education } from '@prisma/client';
import * as cheerio from 'cheerio';

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
      const jobResponse = await fetch(job.url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });
      const jobHtml = await jobResponse.text();
      const $ = cheerio.load(jobHtml);

      let jobDescription = '';

      // LinkedIn specific selectors
      if (job.url.includes('linkedin.com')) {
        jobDescription = $('.jobs-description__content').text().trim() || 
                        $('.description__text').text().trim() ||
                        $('.show-more-less-html__markup').text().trim();
      }
      // Indeed specific selectors  
      else if (job.url.includes('indeed.com')) {
        jobDescription = $('#jobDescriptionText').text().trim();
      }
      // Glassdoor specific selectors
      else if (job.url.includes('glassdoor.com')) {
        jobDescription = $('.jobDescriptionContent').text().trim() ||
                        $('.desc').text().trim();
      }
    job.description = jobDescription;

    console.log("jobDescription", jobDescription);
    // Transform profile data to match ResumeData type
    const resumeData: ResumeData = {
      jobDescription: job.description || '',
      fullName: userProfile.name || '',
      title: userProfile.experience[0]?.title || '',
      email: userProfile.email || '',
      phone: userProfile.phone || '',
      location: userProfile.location || '',
      linkedin: userProfile.linkedinUrl || '',
      github: userProfile.githubUrl || '',
      skills: {
        technical: userProfile.skills.map((skill: Skill) => skill.name),
        soft: [],
      },
      experience: userProfile.experience.map((exp: Experience) => ({
        title: exp.title,
        company: exp.company,
        location: exp.location || '',
        startDate: exp.startDate,
        endDate: exp.endDate,
        description: exp.description || '',
        achievements: exp.description ? exp.description.split('\n').filter((line: string) => line.trim()) : [],
      })),
      education: userProfile.education.map((edu: Education) => ({
        school: edu.school,
        degree: edu.degree,
        field: edu.field || '',
        startDate: edu.startDate,
        endDate: edu.endDate,
        description: edu.description || '',
      })),
      projects: [],
      certifications: [],
    };

    // Generate PDF using our template
    const pdfBuffer = await convertMarkdownToPDF('', resumeData);

    return new NextResponse(pdfBuffer, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${userProfile.name.replace(" ", "_")}-Resume-${job.company}.pdf"`,
      },
    });
  } catch (error) {
    console.error("Error generating resume:", error);
    return new Response("Error generating resume", { status: 500 });
  }
} 