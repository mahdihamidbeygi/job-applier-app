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
              <p className="text-sm text-gray-500">Current Resume</p>
              <a
                href={currentResume}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800"
              >
                View Resume
              </a>
            </div>
            {lastUpdated && (
              <p className="text-sm text-gray-500">
                Last updated: {new Date(lastUpdated).toLocaleDateString()}
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Upload New Resume
            </label>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={handleFileUpload}
              disabled={isUploading}
              className="block w-full text-sm text-black
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-medium
                file:bg-indigo-50 file:text-indigo-700
                hover:file:bg-indigo-100"
            />
          </div>
        </div>
      ) : (
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Upload Resume
          </label>
          <input
            type="file"
            accept=".pdf,.doc,.docx"
            onChange={handleFileUpload}
            disabled={isUploading}
            className="block w-full text-sm text-black
              file:mr-4 file:py-2 file:px-4
              file:rounded-md file:border-0
              file:text-sm file:font-medium
              file:bg-indigo-50 file:text-indigo-700
              hover:file:bg-indigo-100"
          />
        </div>
      )}

      {isUploading && (
        <div className="mt-4">
          <div className="animate-pulse flex space-x-4">
            <div className="flex-1 space-y-4 py-1">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 rounded"></div>
                <div className="h-4 bg-gray-200 rounded w-5/6"></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 text-sm text-red-600">
          {error}
        </div>
      )}
    </div>
  );
} 