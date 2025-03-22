import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export async function PUT(request: Request) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { name, email, phone, location } = await request.json();

    // Validate input
    if (!name || !email) {
      return NextResponse.json({ error: 'Name and email are required' }, { status: 400 });
    }

    // Update the user profile contact information
    const profile = await prisma.userProfile.update({
      where: {
        userId: session.user.id,
      },
      data: {
        name,
        email,
        phone,
        location,
      },
    });

    return NextResponse.json({ 
      success: true, 
      profile: { 
        name: profile.name, 
        email: profile.email, 
        phone: profile.phone, 
        location: profile.location 
      } 
    });
  } catch (error) {
    console.error('Error updating contact information:', error);
    return NextResponse.json({ error: 'Error updating contact information' }, { status: 500 });
  }
} 