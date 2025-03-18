/*
  Warnings:

  - You are about to drop the column `gpa` on the `Education` table. All the data in the column will be lost.
  - You are about to drop the column `profileId` on the `Education` table. All the data in the column will be lost.
  - You are about to drop the column `profileId` on the `Experience` table. All the data in the column will be lost.
  - You are about to drop the column `skills` on the `Experience` table. All the data in the column will be lost.
  - You are about to drop the column `createdAt` on the `User` table. All the data in the column will be lost.
  - You are about to drop the column `updatedAt` on the `User` table. All the data in the column will be lost.
  - You are about to drop the `Certification` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `JobPreferences` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Profile` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Project` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Publication` table. If the table is not empty, all the data it contains will be lost.
  - Added the required column `userId` to the `Education` table without a default value. This is not possible if the table is not empty.
  - Added the required column `userId` to the `Experience` table without a default value. This is not possible if the table is not empty.
  - Made the column `location` on table `Experience` required. This step will fail if there are existing NULL values in that column.
  - Made the column `description` on table `Experience` required. This step will fail if there are existing NULL values in that column.

*/
-- DropForeignKey
ALTER TABLE "Certification" DROP CONSTRAINT "Certification_profileId_fkey";

-- DropForeignKey
ALTER TABLE "Education" DROP CONSTRAINT "Education_profileId_fkey";

-- DropForeignKey
ALTER TABLE "Experience" DROP CONSTRAINT "Experience_profileId_fkey";

-- DropForeignKey
ALTER TABLE "JobPreferences" DROP CONSTRAINT "JobPreferences_profileId_fkey";

-- DropForeignKey
ALTER TABLE "Profile" DROP CONSTRAINT "Profile_userId_fkey";

-- DropForeignKey
ALTER TABLE "Project" DROP CONSTRAINT "Project_profileId_fkey";

-- DropForeignKey
ALTER TABLE "Publication" DROP CONSTRAINT "Publication_profileId_fkey";

-- AlterTable
ALTER TABLE "Education" DROP COLUMN "gpa",
DROP COLUMN "profileId",
ADD COLUMN     "description" TEXT,
ADD COLUMN     "userId" TEXT NOT NULL;

-- AlterTable
ALTER TABLE "Experience" DROP COLUMN "profileId",
DROP COLUMN "skills",
ADD COLUMN     "userId" TEXT NOT NULL,
ALTER COLUMN "location" SET NOT NULL,
ALTER COLUMN "description" SET NOT NULL;

-- AlterTable
ALTER TABLE "User" DROP COLUMN "createdAt",
DROP COLUMN "updatedAt",
ALTER COLUMN "email" DROP NOT NULL;

-- DropTable
DROP TABLE "Certification";

-- DropTable
DROP TABLE "JobPreferences";

-- DropTable
DROP TABLE "Profile";

-- DropTable
DROP TABLE "Project";

-- DropTable
DROP TABLE "Publication";

-- CreateTable
CREATE TABLE "UserProfile" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "phone" TEXT,
    "location" TEXT,
    "summary" TEXT,
    "resumeUrl" TEXT,
    "linkedinUrl" TEXT,
    "githubUrl" TEXT,
    "portfolioUrl" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "UserProfile_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Skill" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "level" TEXT,
    "userId" TEXT NOT NULL,

    CONSTRAINT "Skill_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "UserProfile_userId_key" ON "UserProfile"("userId");

-- AddForeignKey
ALTER TABLE "UserProfile" ADD CONSTRAINT "UserProfile_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Experience" ADD CONSTRAINT "Experience_userId_fkey" FOREIGN KEY ("userId") REFERENCES "UserProfile"("userId") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Education" ADD CONSTRAINT "Education_userId_fkey" FOREIGN KEY ("userId") REFERENCES "UserProfile"("userId") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Skill" ADD CONSTRAINT "Skill_userId_fkey" FOREIGN KEY ("userId") REFERENCES "UserProfile"("userId") ON DELETE CASCADE ON UPDATE CASCADE;
