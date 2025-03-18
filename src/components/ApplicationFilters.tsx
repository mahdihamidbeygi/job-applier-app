'use client';

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

const applicationStatuses = [
  "ALL",
  "PENDING",
  "SUBMITTED",
  "INTERVIEWING",
  "OFFERED",
  "REJECTED",
  "WITHDRAWN",
];

export default function ApplicationFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentStatus = searchParams.get("status") || "ALL";
  const currentSearch = searchParams.get("search") || "";

  const handleStatusChange = useCallback(
    (status: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (status === "ALL") {
        params.delete("status");
      } else {
        params.set("status", status);
      }
      router.push(`/dashboard/applications?${params.toString()}`);
    },
    [router, searchParams]
  );

  const handleSearch = useCallback(
    (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const formData = new FormData(e.currentTarget);
      const search = formData.get("search") as string;
      
      const params = new URLSearchParams(searchParams.toString());
      if (search) {
        params.set("search", search);
      } else {
        params.delete("search");
      }
      router.push(`/dashboard/applications?${params.toString()}`);
    },
    [router, searchParams]
  );

  return (
    <div className="flex flex-col sm:flex-row gap-4">
      <form onSubmit={handleSearch} className="flex-1">
        <input
          type="text"
          name="search"
          defaultValue={currentSearch}
          placeholder="Search applications..."
          className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm text-black placeholder-black"
        />
      </form>

      <select
        value={currentStatus}
        onChange={(e) => handleStatusChange(e.target.value)}
        className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm text-black"
      >
        {applicationStatuses.map((status) => (
          <option key={status} value={status}>
            {status.charAt(0) + status.slice(1).toLowerCase()}
          </option>
        ))}
      </select>
    </div>
  );
} 