-- AlterTable
ALTER TABLE "Profile" ADD COLUMN "bio" TEXT,
    ADD COLUMN "githubUrl" TEXT,
    ADD COLUMN "isProfileComplete" BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN "portfolioUrl" TEXT,
    ADD COLUMN "resumeLastUpdated" TIMESTAMP(3); 