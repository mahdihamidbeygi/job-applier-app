'use client';

import { useState } from "react";

export default function FileUpload({
  type,
  applicationId,
  currentFile,
}) {
  const [isUploading, setIsUploading] = useState(false);
  const [file, setFile] = useState(currentFile || null);

  const handleFileChange = async (e) => {
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
            className="text-sm text-slate-300 hover:text-slate-100"
          >
            View {type === 'resume' ? 'Resume' : 'Cover Letter'}
          </a>
          <button
            onClick={handleRemove}
            disabled={isUploading}
            className="text-sm text-red-400 hover:text-red-300"
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
              className="block w-full text-sm"
            />
          </label>
          <p className="mt-1 text-xs text-slate-400">
            PDF, DOC, or DOCX up to 10MB
          </p>
        </div>
      )}
    </div>
  );
} 