import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { parseResume } from '@/lib/resumeParser';

// Log AWS configuration (without sensitive data)
console.log('AWS Configuration:', {
  region: process.env.AWS_REGION,
  bucketName: process.env.AWS_BUCKET_NAME,
  hasAccessKey: !!process.env.AWS_ACCESS_KEY_ID,
  hasSecretKey: !!process.env.AWS_SECRET_ACCESS_KEY,
});

const s3Client = new S3Client({
  region: process.env.AWS_REGION!,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
  },
});

export async function POST(request: Request) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const formData = await request.formData();
    const file = formData.get('file') as File;
    
    if (!file) {
      return NextResponse.json({ error: 'No file provided' }, { status: 400 });
    }

    console.log('File details:', {
      name: file.name,
      type: file.type,
      size: file.size,
    });

    // Validate file type
    if (!file.type.includes('pdf') && !file.type.includes('msword') && 
        !file.type.includes('application/vnd.openxmlformats-officedocument.wordprocessingml.document')) {
      return NextResponse.json({ 
        error: 'Invalid file type. Please upload a PDF or Word document.',
        allowedTypes: ['PDF', 'DOC', 'DOCX']
      }, { status: 400 });
    }

    // Generate a safe filename
    const timestamp = new Date().getTime();
    const safeFileName = `${timestamp}-${file.name.replace(/[^a-zA-Z0-9.-]/g, '_')}`;
    const key = `resumes/${session.user.id}/${safeFileName}`;

    console.log('Uploading file:', {
      key,
      contentType: file.type,
      userId: session.user.id,
    });

    // Convert File to Buffer
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // Parse resume if it's a PDF
    let parsedResume = null;
    if (file.type.includes('pdf')) {
      try {
        parsedResume = await parseResume(buffer);
        console.log('Parsed resume:', parsedResume);
      } catch (parseError) {
        console.error('Error parsing resume:', parseError);
        // Continue with upload even if parsing fails
      }
    }

    // Upload file to S3
    try {
      await s3Client.send(new PutObjectCommand({
        Bucket: process.env.AWS_BUCKET_NAME,
        Key: key,
        Body: buffer,
        ContentType: file.type,
      }));
      console.log('File uploaded successfully to S3');
    } catch (s3Error) {
      console.error('S3 upload error:', s3Error);
      throw s3Error;
    }

    const fileUrl = `https://${process.env.AWS_BUCKET_NAME}.s3.${process.env.AWS_REGION}.amazonaws.com/${key}`;

    // Get or create user profile with parsed information
    const profile = await prisma.userProfile.upsert({
      where: {
        userId: session.user.id,
      },
      update: {
        resumeUrl: fileUrl,
        updatedAt: new Date(),
        ...(parsedResume && {
          summary: parsedResume.summary || undefined,
          skills: {
            deleteMany: {},
            create: parsedResume.skills.map(skill => ({
              name: skill,
              level: null
            }))
          },
          phone: parsedResume.contactInfo.phone,
          location:parsedResume.contactInfo.location,
          linkedinUrl: parsedResume.contactInfo.linkedInUrl || undefined,
          githubUrl: parsedResume.contactInfo.githubUrl || undefined,
          experience: {
            deleteMany: {},
            create: parsedResume.experience.map(exp => ({
              title: exp.title,
              company: exp.company,
              location: exp.location || '',
              startDate: exp.startDate || new Date(),
              endDate: exp.endDate,
              description: exp.description || '',
            })),
          },
          education: {
            deleteMany: {},
            create: parsedResume.education.map(edu => ({
              school: edu.school,
              degree: edu.degree,
              field: edu.field,
              startDate: edu.startDate || new Date(),
              endDate: edu.endDate,
              description: null,
            })),
          },
          publications: {
            deleteMany: {},
            create: parsedResume.publications?.map(pub => ({
              title: pub.title,
              publisher: pub.publisher,
              date: pub.date,
              description: pub.description || '',
              url: null,
            })) || [],
          },
          certifications: {
            deleteMany: {},
            create: parsedResume.certifications?.map(cert => ({
              name: cert.name,
              issuer: cert.issuer,
              date: cert.date,
              url: cert.url || null,
            })) || [],
          }
        }),
      },
      create: {
        userId: session.user.id,
        name: parsedResume?.contactInfo.name || session.user.name || '',
        email: session.user.email || '',
        resumeUrl: fileUrl,
        summary: parsedResume?.summary,
        phone: parsedResume?.contactInfo.phone,
        location: parsedResume?.contactInfo.location,
        linkedinUrl: parsedResume?.contactInfo.linkedInUrl,
        githubUrl: parsedResume?.contactInfo.githubUrl,
        skills: {
          create: parsedResume?.skills.map(skill => ({
            name: skill,
            level: null
          })) || []
        },
        publications: {
          create: parsedResume?.publications?.map(pub => ({
            title: pub.title,
            publisher: pub.publisher,
            date: pub.date,
            description: pub.description || '',
            url: null,
          })) || []
        },
        certifications: {
          create: parsedResume?.certifications?.map(cert => ({
            name: cert.name,
            issuer: cert.issuer,
            date: cert.date,
            url: cert.url || null,
          })) || []
        }
      },
    });

    // Update user's name if it was extracted and not already set
    if (parsedResume?.contactInfo.name && !session.user.name) {
      await prisma.user.update({
        where: { id: session.user.id },
        data: { name: parsedResume.contactInfo.name }
      });
    }

    return NextResponse.json({ 
      success: true,
      url: fileUrl,
      updatedAt: profile.updatedAt,
      fileName: safeFileName,
      parsedData: parsedResume ? {
        contactInfo: {
          name: parsedResume.contactInfo.name,
          location: parsedResume.contactInfo.location,
          phone: parsedResume.contactInfo.phone,
          linkedInUrl: parsedResume.contactInfo.linkedInUrl,
          githubUrl: parsedResume.contactInfo.githubUrl,
          // Don't send sensitive info like email/phone in response
        },
        summary: parsedResume.summary,
        skills: parsedResume.skills,
        experienceCount: parsedResume.experience.length,
        educationCount: parsedResume.education.length,
      } : null,
    });
  } catch (error) {
    console.error('Error uploading file:', error);
    return NextResponse.json({ 
      error: 'Error uploading file',
      details: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined
    }, { status: 500 });
  }
} 