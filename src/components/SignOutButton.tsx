'use client';

import { signOut } from "next-auth/react";

export default function SignOutButton() {
  return (
    <button
      onClick={() => signOut({ callbackUrl: "/" })}
      className="text-gray-500 hover:text-gray-700 px-3 py-2 rounded-md text-sm font-medium"
    >
      Sign Out
    </button>
  );
} 