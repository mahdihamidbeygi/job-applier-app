'use client';

import { useState } from "react";

interface FileUploadProps {
  type: 'resume' | 'coverLetter';
  applicationId: string;
  currentFile?: string | null;
}

export default function FileUpload({
  type,
  applicationId,
  currentFile,
}: FileUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [file, setFile] = useState<string | null>(currentFile || null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', e.target.files[0]);
      formData.append('type', type);

      const response = await fetch(`/api/applications/${applicationId}/files`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to upload file');
      }

      const data = await response.json();
      setFile(data.url);
    } catch (error) {
      console.error('Error uploading file:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemove = async () => {
    if (!file || isUploading) return;
    setIsUploading(true);

    try {
      const response = await fetch(`/api/applications/${applicationId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          [type === 'resume' ? 'resumeUsed' : 'coverLetter']: null,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to remove file');
      }

      setFile(null);
    } catch (error) {
      console.error('Error removing file:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div>
      {file ? (
        <div className="flex items-center space-x-4">
          <a
            href={file}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-indigo-600 hover:text-indigo-500"
          >
            View {type === 'resume' ? 'Resume' : 'Cover Letter'}
          </a>
          <button
            onClick={handleRemove}
            disabled={isUploading}
            className="text-sm text-red-600 hover:text-red-500"
          >
            Remove
          </button>
        </div>
      ) : (
        <div>
          <label className="block">
            <span className="sr-only">Choose file</span>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={handleFileChange}
              disabled={isUploading}
              className="block w-full text-sm text-black
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-medium
                file:bg-indigo-50 file:text-indigo-700
                hover:file:bg-indigo-100
              "
            />
          </label>
          <p className="mt-1 text-xs text-gray-500">
            PDF, DOC, or DOCX up to 10MB
          </p>
        </div>
      )}
    </div>
  );
} 