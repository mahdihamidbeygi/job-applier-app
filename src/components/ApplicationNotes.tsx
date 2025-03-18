'use client';

import { useState } from "react";

interface ApplicationNotesProps {
  applicationId: string;
  initialNotes?: string | null;
}

export default function ApplicationNotes({
  applicationId,
  initialNotes,
}: ApplicationNotesProps) {
  const [notes, setNotes] = useState(initialNotes || '');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const response = await fetch(`/api/applications/${applicationId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ notes }),
      });

      if (!response.ok) {
        throw new Error('Failed to save notes');
      }
    } catch (error) {
      console.error('Error saving notes:', error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Add notes about your application..."
        className="w-full h-32 p-2 border rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
      />
      <button
        onClick={handleSave}
        disabled={isSaving}
        className="px-4 py-2 text-sm font-medium text-gray-100 bg-indigo-600 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
      >
        {isSaving ? 'Saving...' : 'Save Notes'}
      </button>
    </div>
  );
} 