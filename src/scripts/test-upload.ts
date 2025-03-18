import { config } from 'dotenv';
import { S3Client, PutObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import * as fs from 'fs';
import * as path from 'path';

config();

const s3Client = new S3Client({
  region: process.env.AWS_REGION!,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
  },
});

async function testFileUpload() {
  try {
    // Create a test file
    const testFilePath = path.join(__dirname, 'test-resume.txt');
    fs.writeFileSync(testFilePath, 'This is a test resume file');

    // Upload the file
    const fileContent = fs.readFileSync(testFilePath);
    const key = `test/test-resume-${Date.now()}.txt`;

    const putCommand = new PutObjectCommand({
      Bucket: process.env.AWS_BUCKET_NAME!,
      Key: key,
      Body: fileContent,
      ContentType: 'text/plain',
    });

    await s3Client.send(putCommand);
    console.log('File uploaded successfully');

    // Generate a signed URL
    const getCommand = new GetObjectCommand({
      Bucket: process.env.AWS_BUCKET_NAME!,
      Key: key,
    });

    const url = await getSignedUrl(s3Client, getCommand, { expiresIn: 3600 });
    console.log('File URL:', url);

    // Clean up
    fs.unlinkSync(testFilePath);
    console.log('Test completed successfully');
  } catch (error) {
    console.error('Error during test:', error);
  }
}

testFileUpload(); 