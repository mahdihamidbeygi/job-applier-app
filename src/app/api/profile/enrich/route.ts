import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { enrichProfileFromSocialMedia } from '@/lib/profileEnricher';

export async function POST(req: NextRequest) {
  try {
    // Check if user is authenticated
    const session = await auth();
    if (!session?.user) {
      return NextResponse.json(
        { error: 'You must be logged in to enrich your profile' },
        { status: 401 }
      );
    }

    // Parse request body
    const body = await req.json();
    const { githubUrl } = body;

    // Validate input
    if (!githubUrl) {
      return NextResponse.json(
        { error: 'GitHub URL is required' },
        { status: 400 }
      );
    }

    // Call the enrichment function with only GitHub URL
    const enrichedData = await enrichProfileFromSocialMedia(githubUrl);

    // Return the enriched data
    return NextResponse.json({ data: enrichedData });
  } catch (error) {
    console.error('Error enriching profile:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'An error occurred while enriching your profile' },
      { status: 500 }
    );
  }
} 