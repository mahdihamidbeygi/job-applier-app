import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

const s3Client = new S3Client({
  region: process.env.AWS_REGION!,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
  },
});

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await auth();
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Ensure params.id exists
    const id = params?.id;
    if (!id) {
      return NextResponse.json({ error: 'Invalid application ID' }, { status: 400 });
    }

    const application = await prisma.jobApplication.findUnique({
      where: {
        id,
        userId: session.user.id,
      },
    });

    if (!application) {
      return NextResponse.json({ error: 'Application not found' }, { status: 404 });
    }

    const formData = await request.formData();
    const file = formData.get('file') as File;
    const type = formData.get('type') as string;

    if (!file || !type) {
      return NextResponse.json(
        { error: 'File and type are required' },
        { status: 400 }
      );
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    const key = `applications/${application.id}/${type}/${file.name}`;

    const putCommand = new PutObjectCommand({
      Bucket: process.env.AWS_BUCKET_NAME!,
      Key: key,
      Body: buffer,
      ContentType: file.type,
    });

    await s3Client.send(putCommand);

    const getCommand = new PutObjectCommand({
      Bucket: process.env.AWS_BUCKET_NAME!,
      Key: key,
    });

    const url = await getSignedUrl(s3Client, getCommand, { expiresIn: 3600 });

    await prisma.jobApplication.update({
      where: { id: application.id },
      data: {
        [type === 'resume' ? 'resumeUsed' : 'coverLetter']: key,
      },
    });

    return NextResponse.json({ url });
  } catch (error) {
    console.error('Error handling file upload:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
} 