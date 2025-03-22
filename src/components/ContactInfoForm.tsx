'use client';

import { useState } from 'react';
import { ExclamationCircleIcon } from '@heroicons/react/24/outline';

interface ContactInfoFormProps {
  initialData: {
    name: string;
    email: string;
    phone?: string;
    location?: string;
  };
}

export default function ContactInfoForm({ initialData }: ContactInfoFormProps) {
  const [formData, setFormData] = useState(initialData);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await fetch('/api/profile/contact', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error('Failed to update contact information');
      }

      setSuccessMessage('Contact information updated successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-slate-200">
          Full Name
        </label>
        <input
          type="text"
          id="name"
          name="name"
          value={formData.name}
          onChange={handleChange}
          className="mt-1 block w-full rounded-md border-slate-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm text-slate-100 bg-slate-700 placeholder-slate-400"
          required
        />
      </div>
      
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-slate-200">
          Email
        </label>
        <input
          type="email"
          id="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          className="mt-1 block w-full rounded-md border-slate-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm text-slate-100 bg-slate-700 placeholder-slate-400"
          required
        />
      </div>
      
      <div>
        <label htmlFor="phone" className="block text-sm font-medium text-slate-200">
          Phone Number
        </label>
        <input
          type="tel"
          id="phone"
          name="phone"
          value={formData.phone || ''}
          onChange={handleChange}
          placeholder="+1 (555) 123-4567"
          className="mt-1 block w-full rounded-md border-slate-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm text-slate-100 bg-slate-700 placeholder-slate-400"
        />
      </div>
      
      <div>
        <label htmlFor="location" className="block text-sm font-medium text-slate-200">
          Location
        </label>
        <input
          type="text"
          id="location"
          name="location"
          value={formData.location || ''}
          onChange={handleChange}
          placeholder="City, State, Country"
          className="mt-1 block w-full rounded-md border-slate-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm text-slate-100 bg-slate-700 placeholder-slate-400"
        />
      </div>

      {error && (
        <div className="rounded-md bg-red-900 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <ExclamationCircleIcon className="h-5 w-5 text-red-300" aria-hidden="true" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-200">{error}</h3>
            </div>
          </div>
        </div>
      )}

      {successMessage && (
        <div className="rounded-md bg-green-900 p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-green-200">{successMessage}</h3>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isSubmitting}
          className={`inline-flex items-center px-4 py-2 border border-slate-600 text-sm font-medium rounded-md text-slate-100 bg-slate-700 hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500 ${
            isSubmitting ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {isSubmitting ? 'Saving...' : 'Save Contact Info'}
        </button>
      </div>
    </form>
  );
}