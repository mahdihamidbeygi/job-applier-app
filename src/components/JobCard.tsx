'use client';

import { useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { ExternalLink } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface JobCardProps {
  job: {
    id: string;
    title: string;
    company: string;
    location: string;
    description: string;
    salary?: string;
    jobType?: string;
    platform: string;
    url: string;
    postedAt: string;
  };
  isSaved: boolean;
  userId?: string;
  savedJobs?: { jobId: string }[];
  onSave?: () => void;
}

export default function JobCard({ job, isSaved: initialIsSaved, userId, savedJobs, onSave }: JobCardProps) {
  const [isSaved, setIsSaved] = useState(initialIsSaved);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setIsSaved(!!savedJobs?.find(savedJob => savedJob.jobId === job.id));
  }, [savedJobs, job.id]);

  const handleSave = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/jobs/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ jobId: job.id }),
      });

      if (!response.ok) {
        throw new Error('Failed to save job');
      }

      setIsSaved(!isSaved);
      if (onSave) {
        onSave();
      }
    } catch (error) {
      console.error('Error saving job:', error);
      toast.error('Failed to save job');
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewDetails = () => {
    router.push(`/dashboard/jobs/${job.id}`);
  };

  const handleViewOriginal = () => {
    window.open(job.url, '_blank');
  };

  return (
    <div className="bg-slate-800 shadow rounded-lg p-6 mb-4">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-slate-100 cursor-pointer hover:text-slate-300" onClick={handleViewDetails}>
            {job.title}
          </h3>
          <p className="text-sm text-slate-300">{job.company}</p>
          {job.location && <p className="text-sm text-slate-400">{job.location}</p>}
        </div>
        <div className="flex space-x-2">
          {userId && (
            <button
              onClick={handleSave}
              disabled={isLoading}
              className="inline-flex items-center px-3 py-2 border border-slate-600 shadow-sm text-sm leading-4 font-medium rounded-md text-slate-100 bg-slate-700 hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500"
            >
              {isSaved ? 'Unsave' : 'Save'}
            </button>
          )}
          <button
            onClick={handleViewOriginal}
            className="inline-flex items-center px-3 py-2 border border-slate-600 shadow-sm text-sm leading-4 font-medium rounded-md text-slate-300 bg-slate-800 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500"
          >
            <ExternalLink className="h-4 w-4 mr-1" />
            View Original
          </button>
        </div>
      </div>
      <div className="mt-4">
        <p className="text-sm text-slate-400 line-clamp-3">{job.description}</p>
      </div>
      <div className="mt-4 flex justify-between items-center">
        <div className="flex space-x-4">
          {job.salary && <span className="text-sm text-slate-400">{job.salary}</span>}
          {job.jobType && <span className="text-sm text-slate-400">{job.jobType}</span>}
        </div>
        <span className="text-sm text-slate-400">
          Posted {formatDistanceToNow(new Date(job.postedAt))} ago
        </span>
      </div>
    </div>
  );
} 