'use client';

import { useState } from "react";
import { useRouter } from "next/navigation";
import DateFormatter from "./DateFormatter";

const statusColors = {
  PENDING: "bg-yellow-100 text-yellow-800",
  SUBMITTED: "bg-blue-100 text-blue-800",
  INTERVIEWING: "bg-purple-100 text-purple-800",
  OFFERED: "bg-green-100 text-green-800",
  REJECTED: "bg-red-100 text-red-800",
  WITHDRAWN: "bg-gray-100 text-gray-800",
};

export default function ApplicationCard({ application }) {
  const [isUpdating, setIsUpdating] = useState(false);
  const router = useRouter();

  const handleStatusUpdate = async (newStatus) => {
    if (isUpdating) return;
    setIsUpdating(true);

    try {
      const response = await fetch(`/api/applications/${application.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          status: newStatus,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update status');
      }

      router.refresh();
    } catch (error) {
      console.error('Error updating application status:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="bg-slate-800 shadow rounded-lg p-6">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-medium text-slate-100">
            {application.job.title}
          </h3>
          <p className="mt-1 text-sm text-slate-300">
            {application.job.company}
          </p>
          <div className="mt-2 flex items-center space-x-4">
            <span className="text-sm text-slate-300">
              Applied <DateFormatter date={application.appliedAt} />
            </span>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[application.status]}`}>
              {application.status}
            </span>
          </div>
        </div>
        <select
          value={application.status}
          onChange={(e) => handleStatusUpdate(e.target.value)}
          disabled={isUpdating}
          className="ml-4 block pl-3 pr-10 py-2 text-base border-slate-600 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md text-slate-100 bg-slate-700"
        >
          {Object.keys(statusColors).map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
} 