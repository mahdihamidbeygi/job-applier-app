import NextAuth, { DefaultSession, NextAuthConfig, Account, Session } from "next-auth";
import { PrismaAdapter } from "@auth/prisma-adapter";
import { prisma } from "@/lib/prisma";
import Google from "next-auth/providers/google";
import { AdapterUser } from "@auth/core/adapters";

// Extend the built-in session type
declare module "next-auth" {
  interface Session extends DefaultSession {
    user?: {
      id: string;
    } & DefaultSession["user"]
  }
}

export const config: NextAuthConfig = {
  adapter: PrismaAdapter(prisma),
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async session({ session, user }: { session: Session; user: AdapterUser }) {
      if (session.user) {
        session.user.id = user.id;
      }
      return session;
    },
    async signIn(params: { user: AdapterUser; account: Account | null }) {
      try {
        const { user, account } = params;
        if (!user.email) {
          return false;
        }

        // Check if user exists
        const existingUser = await prisma.user.findUnique({
          where: { email: user.email },
          include: {
            accounts: true,
            profile: true
          }
        });

        if (existingUser) {
          // If the user exists but doesn't have an account with this provider
          if (!existingUser.accounts.some(acc => acc.provider === account?.provider)) {
            // Link the new account to the existing user
            if (account) {
              await prisma.account.create({
                data: {
                  userId: existingUser.id,
                  type: account.type,
                  provider: account.provider,
                  providerAccountId: account.providerAccountId,
                  access_token: account.access_token,
                  token_type: account.token_type,
                  scope: account.scope,
                  id_token: account.id_token,
                }
              });
            }
          }

          // Create profile if it doesn't exist
          if (!existingUser.profile) {
            await prisma.userProfile.create({
              data: {
                userId: existingUser.id,
                name: user.name || '',
                email: user.email,
              }
            });
          }

          return true;
        }

        // If user doesn't exist, let NextAuth create the user and we'll create the profile
        const newUser = await prisma.user.create({
          data: {
            email: user.email,
            name: user.name,
            image: user.image,
          }
        });

        // Create their profile
        await prisma.userProfile.create({
          data: {
            userId: newUser.id,
            name: user.name || '',
            email: user.email,
          }
        });

        return true;
      } catch (error) {
        console.error('Error in signIn callback:', error);
        return false;
      }
    }
  },
  pages: {
    signIn: "/auth/signin",
    error: "/auth/error",
  },
  secret: process.env.NEXTAUTH_SECRET,
};

export const { handlers, auth, signIn, signOut } = NextAuth(config); 