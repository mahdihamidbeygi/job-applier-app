'use client';

import { signIn } from "next-auth/react";

export default function SignInButtons() {
  return (
    <div className="mt-8 space-y-6">
      <div className="text-center">
        <button
          onClick={() => signIn('google', { callbackUrl: "/dashboard" })}
          className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-gray-100 bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          Sign in with Google
        </button>
      </div>
    </div>
  );
} 