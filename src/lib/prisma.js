import { PrismaClient } from "@prisma/client";

// Create a global prisma instance if it doesn't exist
export const prisma = global.prisma || new PrismaClient();

if (process.env.NODE_ENV !== "production") {
  global.prisma = prisma;
} 