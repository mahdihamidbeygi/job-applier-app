'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface EnhancedJobSearchFormProps {
  initialValues?: {
    query?: string;
    location?: string;
    type?: string;
    remote?: boolean;
    experienceLevel?: string;
    datePosted?: string;
    platforms?: string[];
  };
}

export default function EnhancedJobSearchForm({ initialValues = {} }: EnhancedJobSearchFormProps) {
  const router = useRouter();
  const [query, setQuery] = useState(initialValues.query || '');
  const [location, setLocation] = useState(initialValues.location || '');
  const [jobType, setJobType] = useState(initialValues.type || '');
  const [remote, setRemote] = useState(initialValues.remote || false);
  const [experienceLevel, setExperienceLevel] = useState(initialValues.experienceLevel || '');
  const [datePosted, setDatePosted] = useState(initialValues.datePosted || '');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(
    Array.isArray(initialValues.platforms) 
      ? initialValues.platforms 
      : initialValues.platforms 
        ? [initialValues.platforms as string] 
        : ['linkedin', 'indeed']
  );
  const [isLoading, setIsLoading] = useState(false);

  const jobPlatforms = [
    { id: 'linkedin', name: 'LinkedIn' },
    { id: 'indeed', name: 'Indeed' },
    { id: 'glassdoor', name: 'Glassdoor' },
    { id: 'ziprecruiter', name: 'ZipRecruiter' },
    { id: 'monster', name: 'Monster' }
  ];

  const jobTypes = [
    { id: '', name: 'Any Type' },
    { id: 'FULL_TIME', name: 'Full Time' },
    { id: 'PART_TIME', name: 'Part Time' },
    { id: 'CONTRACT', name: 'Contract' },
    { id: 'TEMPORARY', name: 'Temporary' },
    { id: 'INTERNSHIP', name: 'Internship' }
  ];

  const experienceLevels = [
    { id: '', name: 'Any Level' },
    { id: 'ENTRY_LEVEL', name: 'Entry Level' },
    { id: 'MID_LEVEL', name: 'Mid Level' },
    { id: 'SENIOR_LEVEL', name: 'Senior Level' },
    { id: 'EXECUTIVE', name: 'Executive' }
  ];

  const datePostedOptions = [
    { id: '', name: 'Any Time' },
    { id: 'past_24_hours', name: 'Past 24 Hours' },
    { id: 'past_week', name: 'Past Week' },
    { id: 'past_month', name: 'Past Month' }
  ];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    // Build query parameters
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (location) params.append('location', location);
    if (jobType) params.append('type', jobType);
    if (remote) params.append('remote', 'true');
    if (experienceLevel) params.append('experienceLevel', experienceLevel);
    if (datePosted) params.append('datePosted', datePosted);
    
    // Add selected platforms
    selectedPlatforms.forEach(platform => {
      params.append('platforms', platform);
    });

    // Navigate to jobs page with search parameters
    router.push(`/dashboard/jobs?${params.toString()}`);
  };

  const togglePlatform = (platformId: string) => {
    setSelectedPlatforms(prev => {
      if (prev.includes(platformId)) {
        return prev.filter(id => id !== platformId);
      } else {
        return [...prev, platformId];
      }
    });
  };

  return (
    <form onSubmit={handleSearch} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-1">
            Job Title, Keywords, or Company
          </label>
          <input
            id="query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-black"
            placeholder="e.g. Software Engineer"
          />
        </div>
        
        <div>
          <label htmlFor="location" className="block text-sm font-medium text-gray-700 mb-1">
            Location
          </label>
          <input
            id="location"
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-black"
            placeholder="e.g. New York, NY"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label htmlFor="jobType" className="block text-sm font-medium text-gray-700 mb-1">
            Job Type
          </label>
          <select
            id="jobType"
            value={jobType}
            onChange={(e) => setJobType(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-black"
          >
            {jobTypes.map(type => (
              <option key={type.id} value={type.id}>{type.name}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label htmlFor="experienceLevel" className="block text-sm font-medium text-gray-700 mb-1">
            Experience Level
          </label>
          <select
            id="experienceLevel"
            value={experienceLevel}
            onChange={(e) => setExperienceLevel(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-black"
          >
            {experienceLevels.map(level => (
              <option key={level.id} value={level.id}>{level.name}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label htmlFor="datePosted" className="block text-sm font-medium text-gray-700 mb-1">
            Date Posted
          </label>
          <select
            id="datePosted"
            value={datePosted}
            onChange={(e) => setDatePosted(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-black"
          >
            {datePostedOptions.map(option => (
              <option key={option.id} value={option.id}>{option.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center">
        <input
          id="remote"
          type="checkbox"
          checked={remote}
          onChange={(e) => setRemote(e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-blue-600"
        />
        <label htmlFor="remote" className="ml-2 text-sm font-medium text-gray-700">
          Remote Jobs Only
        </label>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Job Platforms
        </label>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {jobPlatforms.map(platform => (
            <div key={platform.id} className="flex items-center">
              <input
                id={`platform-${platform.id}`}
                type="checkbox"
                checked={selectedPlatforms.includes(platform.id)}
                onChange={() => togglePlatform(platform.id)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600"
              />
              <label htmlFor={`platform-${platform.id}`} className="ml-2 text-sm text-gray-700">
                {platform.name}
              </label>
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-gray-100 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
        >
          {isLoading ? 'Searching...' : 'Search Jobs'}
        </button>
      </div>
    </form>
  );
} 