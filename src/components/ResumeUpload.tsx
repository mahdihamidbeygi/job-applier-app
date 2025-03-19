'use client';

import { useState } from 'react';

interface ResumeUploadProps {
  currentResume: string | null;
  lastUpdated: Date | null;
}

export default function ResumeUpload({ currentResume, lastUpdated }: ResumeUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const uploadResponse = await fetch('/api/profile/upload', {
        method: 'POST',
        body: formData,
      });

      if (!uploadResponse.ok) {
        const data = await uploadResponse.json();
        throw new Error(data.error || 'Error uploading resume');
      }

      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error uploading resume');
      setIsUploading(false);
    }
  };

  return (
    <div>
      {currentResume ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Current Resume</p>
              <a
                href={currentResume}
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-300 hover:text-slate-100"
              >
                View Resume
              </a>
            </div>
            {lastUpdated && (
              <p className="text-sm text-slate-400">
                Last updated: {new Date(lastUpdated).toLocaleDateString()}
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300">
              Upload New Resume
            </label>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={handleFileUpload}
              disabled={isUploading}
              className="block w-full text-sm"
            />
          </div>
        </div>
      ) : (
        <div>
          <label className="block text-sm font-medium text-slate-300">
            Upload Resume
          </label>
          <input
            type="file"
            accept=".pdf,.doc,.docx"
            onChange={handleFileUpload}
            disabled={isUploading}
            className="block w-full text-sm"
          />
        </div>
      )}

      {isUploading && (
        <div className="mt-4">
          <div className="animate-pulse flex space-x-4">
            <div className="flex-1 space-y-4 py-1">
              <div className="h-4 bg-slate-700 rounded w-3/4"></div>
              <div className="space-y-2">
                <div className="h-4 bg-slate-700 rounded"></div>
                <div className="h-4 bg-slate-700 rounded w-5/6"></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 text-sm text-red-400">
          {error}
        </div>
      )}
    </div>
  );
} 