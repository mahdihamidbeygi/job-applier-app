import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import Image from "next/image";
import { redirect } from "next/navigation";
import ProfileForm from "@/components/ProfileForm";
import ResumeUpload from "@/components/ResumeUpload";
import { ResumeDownload } from "@/components/ResumeDownload";

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
      skills: true,
      publications: {
        orderBy: {
          date: 'desc'
        }
      },
      certifications: {
        orderBy: {
          date: 'desc'
        }
      }
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
          skills: true,
          publications: true,
          certifications: true
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
      <div className="bg-slate-800 shadow rounded-lg p-6">
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
            <h1 className="text-2xl font-bold text-slate-100">{profile.user.name}</h1>
            <p className="text-slate-300">{profile.user.email}</p>
          </div>
        </div>
      </div>

      <div className="bg-slate-800 shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-slate-100 mb-4">Resume</h2>
        <div className="space-y-4">
          <ResumeUpload
            currentResume={profile.resumeUrl}
            lastUpdated={profile.updatedAt}
          />
          <ResumeDownload 
            profile={{
              fullName: profile.name || '',
              title: profile.experience[0]?.title || 'Software Engineer',
              email: profile.email || '',
              phone: profile.phone || '',
              location: profile.location || null,
              linkedinUrl: profile.linkedinUrl || null,
              githubUrl: profile.githubUrl || null,
              summary: profile.summary || '',
              skills: profile.skills.map(skill => skill.name),
              experience: profile.experience.map(exp => ({
                company: exp.company,
                position: exp.title,
                startDate: exp.startDate,
                endDate: exp.endDate || null,
                description: exp.description || '',
              })),
              education: profile.education.map(edu => ({
                institution: edu.school,
                degree: edu.degree,
                startDate: edu.startDate,
                endDate: edu.endDate || null,
                description: edu.field || '',
              })),
              projects: [],
              certifications: profile.certifications.map(cert => ({
                name: cert.name,
                issuer: cert.issuer,
                date: cert.date,
                url: cert.url
              })),
              publications: profile.publications.map(pub => ({
                title: pub.title,
                publisher: pub.publisher,
                date: pub.date,
                description: pub.description,
                url: pub.url
              }))
            }} 
          />
        </div>
      </div>

      <div className="bg-slate-800 shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-slate-100 mb-4">Professional Profile</h2>
        <ProfileForm
          initialData={{
            linkedInUrl: profile.linkedinUrl || "",
            githubUrl: profile.githubUrl || "",
            portfolioUrl: profile.portfolioUrl || "",
            bio: profile.summary || "",
            skills: profile.skills.map(skill => skill.name),
            experience: formattedExperience,
            education: formattedEducation,
            publications: profile.publications.map(pub => ({
              ...pub,
              profileId: profile.id,
              isEditing: false,
              isDirty: false
            })),
            certifications: profile.certifications.map(cert => ({
              ...cert,
              profileId: profile.id,
              isEditing: false,
              isDirty: false
            }))
          }}
        />
      </div>

      <div className="bg-slate-800 shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-slate-100 mb-4">Account Statistics</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-700 p-4 rounded-lg">
            <h3 className="text-lg font-medium text-slate-100">Applications</h3>
            <p className="text-3xl font-bold text-blue-400">{totalApplications}</p>
          </div>
          <div className="bg-slate-700 p-4 rounded-lg">
            <h3 className="text-lg font-medium text-slate-100">Saved Jobs</h3>
            <p className="text-3xl font-bold text-blue-400">{savedJobs}</p>
          </div>
          <div className="bg-slate-700 p-4 rounded-lg">
            <h3 className="text-lg font-medium text-slate-100">Active Applications</h3>
            <p className="text-3xl font-bold text-blue-400">{activeApplications}</p>
          </div>
        </div>
      </div>
    </div>
  );
} 