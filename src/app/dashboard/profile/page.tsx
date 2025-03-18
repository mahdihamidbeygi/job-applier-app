import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import Image from "next/image";
import { redirect } from "next/navigation";
import ProfileForm from "@/components/ProfileForm";
import ResumeUpload from "@/components/ResumeUpload";

export default async function ProfilePage() {
  const session = await auth();
  
  if (!session?.user?.id) {
    redirect('/auth/signin');
  }

  // First verify the user exists
  const user = await prisma.user.findUnique({
    where: { id: session.user.id },
    select: {
      id: true,
      name: true,
      email: true,
      image: true,
    }
  });

  if (!user) {
    redirect('/auth/signin');
  }

  let profile = await prisma.userProfile.findUnique({
    where: { userId: session.user.id },
    include: {
      user: {
        select: {
          name: true,
          email: true,
          image: true,
        }
      },
      experience: {
        orderBy: {
          startDate: 'desc'
        }
      },
      education: {
        orderBy: {
          startDate: 'desc'
        }
      },
      skills: true
    }
  });

  if (!profile) {
    try {
      profile = await prisma.userProfile.create({
        data: {
          userId: user.id,
          name: user.name || '',
          email: user.email || '',
          skills: {
            create: []
          }
        },
        include: {
          user: {
            select: {
              name: true,
              email: true,
              image: true,
            }
          },
          experience: true,
          education: true,
          skills: true
        }
      });
    } catch (error) {
      console.error('Error creating profile:', error);
      redirect('/auth/signin?error=profile-creation-failed');
    }
  }

  const stats = await prisma.$transaction([
    prisma.jobApplication.count({
      where: { userId: session.user.id },
    }),
    prisma.savedJob.count({
      where: { userId: session.user.id },
    }),
    prisma.jobApplication.count({
      where: {
        userId: session.user.id,
        status: {
          in: ['PENDING', 'SUBMITTED', 'INTERVIEWING'],
        },
      },
    }),
  ]);

  const [totalApplications, savedJobs, activeApplications] = stats;

  // Transform the data to match ProfileForm's expected types
  const formattedExperience = profile.experience.map(exp => ({
    ...exp,
    profileId: profile.id,
    skills: [],
    isEditing: false,
    isDirty: false,
    location: exp.location || null,
    description: exp.description || null
  }));

  const formattedEducation = profile.education.map(edu => ({
    ...edu,
    profileId: profile.id,
    isEditing: false,
    isDirty: false,
    gpa: null
  }));

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center space-x-6">
          {profile.user.image && (
            <Image
              src={profile.user.image}
              alt={profile.user.name || "Profile picture"}
              width={96}
              height={96}
              className="rounded-full"
            />
          )}
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{profile.user.name}</h1>
            <p className="text-gray-500">{profile.user.email}</p>
          </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Resume</h2>
        <ResumeUpload
          currentResume={profile.resumeUrl}
          lastUpdated={profile.updatedAt}
        />
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Professional Profile</h2>
        <ProfileForm
          initialData={{
            linkedInUrl: profile.linkedinUrl || "",
            githubUrl: profile.githubUrl || "",
            portfolioUrl: profile.portfolioUrl || "",
            bio: profile.summary || "",
            skills: profile.skills.map(skill => skill.name),
            experience: formattedExperience,
            education: formattedEducation
          }}
        />
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Account Statistics</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-lg font-medium text-gray-900">Applications</h3>
            <p className="text-3xl font-bold text-blue-600">{totalApplications}</p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-lg font-medium text-gray-900">Saved Jobs</h3>
            <p className="text-3xl font-bold text-blue-600">{savedJobs}</p>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-lg font-medium text-gray-900">Active Applications</h3>
            <p className="text-3xl font-bold text-blue-600">{activeApplications}</p>
          </div>
        </div>
      </div>
    </div>
  );
} 