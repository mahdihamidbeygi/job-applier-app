'use client';

import { useCallback } from 'react';
import { useRouter } from "next/navigation";

const jobTypes = [
  "Full-time",
  "Part-time",
  "Contract",
  "Temporary",
  "Internship",
  "Remote",
];

export default function JobSearchForm({ initialValues }) {
  const router = useRouter();
  
  const handleSubmit = useCallback(
    (e) => {
      e.preventDefault();
      const formData = new FormData(e.currentTarget);
      const searchParams = new URLSearchParams();
      
      const query = formData.get("q");
      const location = formData.get("location");
      const type = formData.get("type");

      if (query) searchParams.set("q", query);
      if (location) searchParams.set("location", location);
      if (type) searchParams.set("type", type);

      router.push(`/dashboard/jobs?${searchParams.toString()}`);
    },
    [router]
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label htmlFor="q" className="block text-sm font-medium text-gray-700">
            Search
          </label>
          <input
            type="text"
            name="q"
            id="q"
            defaultValue={initialValues.query}
            placeholder="Job title, company, or keywords"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm text-black"
          />
        </div>

        <div>
          <label htmlFor="location" className="block text-sm font-medium text-gray-700">
            Location
          </label>
          <input
            type="text"
            name="location"
            id="location"
            defaultValue={initialValues.location}
            placeholder="City, state, or remote"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm text-black"
          />
        </div>

        <div>
          <label htmlFor="type" className="block text-sm font-medium text-gray-700">
            Job Type
          </label>
          <select
            name="type"
            id="type"
            defaultValue={initialValues.type}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm text-black"
          >
            <option value="">All Types</option>
            {jobTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-gray-100 bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          Search Jobs
        </button>
      </div>
    </form>
  );
} 