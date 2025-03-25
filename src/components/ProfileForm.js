'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Transition } from '@headlessui/react';
import { PencilIcon, CheckIcon, XMarkIcon, EyeIcon, EyeSlashIcon, PlusIcon, ExclamationCircleIcon, ArrowTopRightOnSquareIcon, CloudArrowDownIcon } from '@heroicons/react/24/outline';
import { v4 as uuidv4 } from 'uuid';
import { format, isValid, isBefore } from 'date-fns';
import { z } from 'zod';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import ConfirmationDialog from './ConfirmationDialog';
import BulkDeleteButton from './BulkDeleteButton';

// Zod schemas for validation
const urlSchema = z.string().url().optional().or(z.literal(''));

const experienceSchema = z.object({
  id: z.string(),
  profileId: z.string(),
  title: z.string().min(1, 'Title is required'),
  company: z.string().min(1, 'Company is required'),
  location: z.string().nullable(),
  startDate: z.date(),
  endDate: z.date().nullable(),
  description: z.string().nullable(),
  skills: z.array(z.string()),
  isEditing: z.boolean(),
  isDirty: z.boolean()
});

const educationSchema = z.object({
  id: z.string(),
  profileId: z.string(),
  school: z.string().min(1, 'School is required'),
  degree: z.string().min(1, 'Degree is required'),
  field: z.string().min(1, 'Field of study is required'),
  startDate: z.date(),
  endDate: z.date().nullable(),
  gpa: z.number().nullable(),
  isEditing: z.boolean(),
  isDirty: z.boolean()
});

const publicationSchema = z.object({
  id: z.string(),
  profileId: z.string(),
  title: z.string().min(1, 'Title is required'),
  publisher: z.string().min(1, 'Publisher is required'),
  date: z.date().nullable(),
  description: z.string().nullable(),
  isEditing: z.boolean(),
  isDirty: z.boolean()
});

const certificationSchema = z.object({
  id: z.string(),
  profileId: z.string(),
  name: z.string().min(1, 'Name is required'),
  issuer: z.string().min(1, 'Issuer is required'),
  date: z.date().nullable(),
  url: z.string().url().optional().or(z.literal('')),
  isEditing: z.boolean(),
  isDirty: z.boolean()
});

const dynamicSectionItemSchema = z.object({
  id: z.string(),
  title: z.string().optional(),
  subtitle: z.string().optional(),
  date: z.date().nullable(),
  endDate: z.date().nullable(),
  description: z.string().optional(),
  url: z.string().url().optional().or(z.literal('')),
  isEditing: z.boolean(),
  isDirty: z.boolean()
});

const dynamicSectionSchema = z.object({
  id: z.string(),
  type: z.string(),
  title: z.string(),
  items: z.array(dynamicSectionItemSchema),
  isEditing: z.boolean(),
  isDirty: z.boolean()
});

const projectSchema = z.object({
  id: z.string(),
  profileId: z.string(),
  title: z.string().min(1, 'Title is required'),
  description: z.string().nullable(),
  url: z.string().url().optional().or(z.literal('')),
  date: z.date().nullable(),
  isEditing: z.boolean(),
  isDirty: z.boolean()
});

const formSchema = z.object({
  linkedInUrl: urlSchema,
  githubUrl: urlSchema,
  portfolioUrl: urlSchema,
  bio: z.string().min(1, 'Bio is required'),
  skills: z.array(z.string()),
  experience: z.array(experienceSchema),
  education: z.array(educationSchema),
  publications: z.array(publicationSchema),
  certifications: z.array(certificationSchema),
  projects: z.array(projectSchema),
  additionalSections: z.array(dynamicSectionSchema)
});

const SortableItem = ({ id, children }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      {children}
    </div>
  );
};

// Define consistent color classes
const buttonPrimaryClass = "inline-flex items-center px-3 py-1 border border-slate-600 text-sm font-medium rounded-md text-slate-100 bg-slate-700 hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500";
const buttonSecondaryClass = "inline-flex items-center px-3 py-1 border border-slate-600 text-sm font-medium rounded-md text-slate-300 bg-slate-800 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500";
const sectionClass = "bg-slate-800 rounded-lg p-6 shadow-sm border border-slate-700";
const sectionHeaderClass = "text-lg font-semibold text-slate-100 mb-4";
const cardClass = "bg-slate-800 shadow rounded-lg p-4 border border-slate-700";
const titleClass = "text-lg font-medium text-slate-100";
const labelClass = "block text-sm font-medium text-slate-200";
const inputClass = "mt-1 block w-full rounded-md border-slate-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm text-slate-100 bg-slate-700 placeholder-slate-400";
const subtitleClass = "text-sm text-slate-300";
const deleteButtonClass = "inline-flex items-center px-3 py-1 border border-red-900 text-sm font-medium rounded-md text-red-200 bg-red-900/50 hover:bg-red-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500";
const linkClass = "inline-flex items-center text-sm text-slate-300 hover:text-slate-100";
const skillTagClass = "inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium bg-slate-700 text-slate-200 group";
const skillTagButtonClass = "ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full text-slate-300 hover:text-slate-100 focus:outline-none";

// Helper functions
const areProjectsDuplicate = (proj1, proj2) => {
  return (
    proj1.title.toLowerCase() === proj2.title.toLowerCase() &&
    (proj1.url === proj2.url || (!proj1.url && !proj2.url))
  );
};

const areCertificationsDuplicate = (cert1, cert2) => {
  return (
    cert1.name.toLowerCase() === cert2.name.toLowerCase() &&
    cert1.issuer.toLowerCase() === cert2.issuer.toLowerCase()
  );
};

const isValidRecord = (record, type) => {
  if (!record) return false;
  
  switch (type) {
    case 'experience':
      return Boolean(record.title && record.company && record.startDate);
    case 'education':
      return Boolean(record.school && record.degree && record.field);
    case 'project':
      return Boolean(record.title);
    case 'publication':
      return Boolean(record.title && record.publisher);
    case 'certification':
      return Boolean(record.name && record.issuer);
    default:
      return true;
  }
};

const removeDuplicates = (items, compareFn) => {
  return items.reduce((unique, item) => {
    const isDuplicate = unique.some(existingItem => compareFn(existingItem, item));
    if (!isDuplicate) {
      unique.push(item);
    }
    return unique;
  }, []);
};

export default function ProfileForm({ initialData }) {
  const router = useRouter();
  const [formData, setFormData] = useState({
    linkedInUrl: initialData.linkedInUrl || '',
    githubUrl: initialData.githubUrl || '',
    portfolioUrl: initialData.portfolioUrl || '',
    bio: initialData.bio || '',
    skills: initialData.skills || [],
    experience: initialData.experience || [],
    education: initialData.education || [],
    publications: initialData.publications || [],
    certifications: initialData.certifications || [],
    projects: initialData.projects || [],
    additionalSections: initialData.additionalSections || []
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [itemToDelete, setItemToDelete] = useState(null);
  const [deleteType, setDeleteType] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [importPassword, setImportPassword] = useState('');
  const [isImporting, setIsImporting] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const validateField = (value, fieldName) => {
    try {
      formSchema.shape[fieldName].parse(value);
      return null;
    } catch (error) {
      return error.errors[0]?.message || 'Invalid value';
    }
  };

  const addNewEntry = (type) => {
    const newEntry = {
      id: uuidv4(),
      profileId: uuidv4(),
      isEditing: true,
      isDirty: true
    };

    switch (type) {
      case 'experience':
        newEntry.title = '';
        newEntry.company = '';
        newEntry.location = null;
        newEntry.startDate = new Date();
        newEntry.endDate = null;
        newEntry.description = null;
        newEntry.skills = [];
        break;
      case 'education':
        newEntry.school = '';
        newEntry.degree = '';
        newEntry.field = '';
        newEntry.startDate = new Date();
        newEntry.endDate = null;
        newEntry.gpa = null;
        break;
      case 'publication':
        newEntry.title = '';
        newEntry.publisher = '';
        newEntry.date = null;
        newEntry.description = null;
        break;
      case 'certification':
        newEntry.name = '';
        newEntry.issuer = '';
        newEntry.date = null;
        newEntry.url = '';
        break;
      case 'project':
        newEntry.title = '';
        newEntry.description = null;
        newEntry.url = '';
        newEntry.date = null;
        break;
      case 'dynamicSection':
        newEntry.type = 'custom';
        newEntry.title = '';
        newEntry.items = [];
        break;
    }

    setFormData(prev => ({
      ...prev,
      [type]: [...prev[type], newEntry]
    }));
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSkillsChange = (e) => {
    const { value } = e.target;
    if (value.endsWith(',')) {
      const newSkill = value.slice(0, -1).trim();
      if (newSkill && !formData.skills.includes(newSkill)) {
        setFormData(prev => ({
          ...prev,
          skills: [...prev.skills, newSkill]
        }));
      }
      e.target.value = '';
    }
  };

  const removeSkill = (skillToRemove) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.filter(skill => skill !== skillToRemove)
    }));
  };

  const handleClearAllSkills = () => {
    setFormData(prev => ({
      ...prev,
      skills: []
    }));
  };

  const formatDate = (date) => {
    if (!date) return '';
    return format(new Date(date), 'MMM yyyy');
  };

  const handleItemChange = (type, id, field, value) => {
    setFormData(prev => ({
      ...prev,
      [type]: prev[type].map(item => {
        if (item.id === id) {
          return {
            ...item,
            [field]: value,
            isDirty: true
          };
        }
        return item;
      })
    }));
  };

  const toggleEdit = (type, id) => {
    setFormData(prev => ({
      ...prev,
      [type]: prev[type].map(item => {
        if (item.id === id) {
          return {
            ...item,
            isEditing: !item.isEditing
          };
        }
        return item;
      })
    }));
  };

  const handleDeleteItem = (type, id) => {
    setItemToDelete(id);
    setDeleteType(type);
    setShowConfirmation(true);
  };

  const handleDeleteDynamicItem = (sectionId, itemId) => {
    setFormData(prev => ({
      ...prev,
      additionalSections: prev.additionalSections.map(section => {
        if (section.id === sectionId) {
          return {
            ...section,
            items: section.items.filter(item => item.id !== itemId)
          };
        }
        return section;
      })
    }));
  };

  const getFieldError = (type, id, field) => {
    if (!id) return errors[field];
    return errors[`${type}.${id}.${field}`];
  };

  const handleDragEnd = (event, sectionId) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setFormData(prev => ({
      ...prev,
      additionalSections: prev.additionalSections.map(section => {
        if (section.id === sectionId) {
          const oldIndex = section.items.findIndex(item => item.id === active.id);
          const newIndex = section.items.findIndex(item => item.id === over.id);
          return {
            ...section,
            items: arrayMove(section.items, oldIndex, newIndex)
          };
        }
        return section;
      })
    }));
  };

  const addDynamicSectionItem = (sectionId) => {
    const newItem = {
      id: uuidv4(),
      title: '',
      subtitle: '',
      date: null,
      endDate: null,
      description: '',
      url: '',
      isEditing: true,
      isDirty: true
    };

    setFormData(prev => ({
      ...prev,
      additionalSections: prev.additionalSections.map(section => {
        if (section.id === sectionId) {
          return {
            ...section,
            items: [...section.items, newItem]
          };
        }
        return section;
      })
    }));
  };

  const handleDynamicItemChange = (sectionId, itemId, field, value) => {
    setFormData(prev => ({
      ...prev,
      additionalSections: prev.additionalSections.map(section => {
        if (section.id === sectionId) {
          return {
            ...section,
            items: section.items.map(item => {
              if (item.id === itemId) {
                return {
                  ...item,
                  [field]: value,
                  isDirty: true
                };
              }
              return item;
            })
          };
        }
        return section;
      })
    }));
  };

  const toggleDynamicItemEdit = (sectionId, itemId) => {
    setFormData(prev => ({
      ...prev,
      additionalSections: prev.additionalSections.map(section => {
        if (section.id === sectionId) {
          return {
            ...section,
            items: section.items.map(item => {
              if (item.id === itemId) {
                return {
                  ...item,
                  isEditing: !item.isEditing
                };
              }
              return item;
            })
          };
        }
        return section;
      })
    }));
  };

  const handleImportFromSocialMedia = async () => {
    if (!importPassword) {
      toast.error('Please enter your password');
      return;
    }

    setIsImporting(true);
    try {
      const response = await fetch('/api/profile/import', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          password: importPassword,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to import profile data');
      }

      const data = await response.json();
      setFormData(prev => ({
        ...prev,
        ...data,
        skills: removeDuplicates([...prev.skills, ...data.skills], (a, b) => a === b),
        experience: removeDuplicates([...prev.experience, ...data.experience], (a, b) => 
          a.title === b.title && a.company === b.company
        ),
        education: removeDuplicates([...prev.education, ...data.education], (a, b) =>
          a.school === b.school && a.degree === b.degree
        ),
        projects: removeDuplicates([...prev.projects, ...data.projects], areProjectsDuplicate),
        certifications: removeDuplicates([...prev.certifications, ...data.certifications], areCertificationsDuplicate),
      }));

      toast.success('Profile data imported successfully');
      setShowPassword(false);
      setImportPassword('');
    } catch (error) {
      console.error('Error importing profile data:', error);
      toast.error('Failed to import profile data');
    } finally {
      setIsImporting(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Validate form data
      const validationResult = formSchema.safeParse(formData);
      if (!validationResult.success) {
        const newErrors = {};
        validationResult.error.errors.forEach(error => {
          const path = error.path.join('.');
          newErrors[path] = error.message;
        });
        setErrors(newErrors);
        throw new Error('Validation failed');
      }

      // Send data to API
      const response = await fetch('/api/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error('Failed to update profile');
      }

      toast.success('Profile updated successfully');
      router.refresh();
    } catch (error) {
      console.error('Error updating profile:', error);
      toast.error('Failed to update profile');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Information */}
      <div className={sectionClass}>
        <h2 className={sectionHeaderClass}>Basic Information</h2>
        <div className="space-y-4">
          <div>
            <label htmlFor="linkedInUrl" className={labelClass}>
              LinkedIn URL
            </label>
            <input
              type="url"
              id="linkedInUrl"
              name="linkedInUrl"
              value={formData.linkedInUrl}
              onChange={handleChange}
              className={inputClass}
              placeholder="https://linkedin.com/in/your-profile"
            />
            {errors.linkedInUrl && (
              <p className="mt-1 text-sm text-red-500">{errors.linkedInUrl}</p>
            )}
          </div>

          <div>
            <label htmlFor="githubUrl" className={labelClass}>
              GitHub URL
            </label>
            <input
              type="url"
              id="githubUrl"
              name="githubUrl"
              value={formData.githubUrl}
              onChange={handleChange}
              className={inputClass}
              placeholder="https://github.com/your-username"
            />
            {errors.githubUrl && (
              <p className="mt-1 text-sm text-red-500">{errors.githubUrl}</p>
            )}
          </div>

          <div>
            <label htmlFor="portfolioUrl" className={labelClass}>
              Portfolio URL
            </label>
            <input
              type="url"
              id="portfolioUrl"
              name="portfolioUrl"
              value={formData.portfolioUrl}
              onChange={handleChange}
              className={inputClass}
              placeholder="https://your-portfolio.com"
            />
            {errors.portfolioUrl && (
              <p className="mt-1 text-sm text-red-500">{errors.portfolioUrl}</p>
            )}
          </div>

          <div>
            <label htmlFor="bio" className={labelClass}>
              Bio
            </label>
            <textarea
              id="bio"
              name="bio"
              value={formData.bio}
              onChange={handleChange}
              className={inputClass}
              rows={4}
              required
            />
            {errors.bio && (
              <p className="mt-1 text-sm text-red-500">{errors.bio}</p>
            )}
          </div>
        </div>
      </div>

      {/* Skills */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h2 className={sectionHeaderClass}>Skills</h2>
          <button
            type="button"
            onClick={handleClearAllSkills}
            className={buttonSecondaryClass}
          >
            Clear All
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label htmlFor="skills" className={labelClass}>
              Add Skills (comma-separated)
            </label>
            <input
              type="text"
              id="skills"
              value=""
              onChange={handleSkillsChange}
              className={inputClass}
              placeholder="e.g. JavaScript, React, Node.js"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {formData.skills.map((skill, index) => (
              <span key={index} className={skillTagClass}>
                {skill}
                <button
                  type="button"
                  onClick={() => removeSkill(skill)}
                  className={skillTagButtonClass}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Experience */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h2 className={sectionHeaderClass}>Experience</h2>
          <button
            type="button"
            onClick={() => addNewEntry('experience')}
            className={buttonPrimaryClass}
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Experience
          </button>
        </div>
        <div className="space-y-4">
          {formData.experience.map((exp) => (
            <div key={exp.id} className={cardClass}>
              {exp.isEditing ? (
                <div className="space-y-4">
                  <div>
                    <label className={labelClass}>Title</label>
                    <input
                      type="text"
                      value={exp.title}
                      onChange={(e) => handleItemChange('experience', exp.id, 'title', e.target.value)}
                      className={inputClass}
                      required
                    />
                    {getFieldError('experience', exp.id, 'title') && (
                      <p className="mt-1 text-sm text-red-500">{getFieldError('experience', exp.id, 'title')}</p>
                    )}
                  </div>
                  <div>
                    <label className={labelClass}>Company</label>
                    <input
                      type="text"
                      value={exp.company}
                      onChange={(e) => handleItemChange('experience', exp.id, 'company', e.target.value)}
                      className={inputClass}
                      required
                    />
                    {getFieldError('experience', exp.id, 'company') && (
                      <p className="mt-1 text-sm text-red-500">{getFieldError('experience', exp.id, 'company')}</p>
                    )}
                  </div>
                  <div>
                    <label className={labelClass}>Location</label>
                    <input
                      type="text"
                      value={exp.location || ''}
                      onChange={(e) => handleItemChange('experience', exp.id, 'location', e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className={labelClass}>Start Date</label>
                      <input
                        type="date"
                        value={format(exp.startDate, 'yyyy-MM-dd')}
                        onChange={(e) => handleItemChange('experience', exp.id, 'startDate', new Date(e.target.value))}
                        className={inputClass}
                        required
                      />
                      {getFieldError('experience', exp.id, 'startDate') && (
                        <p className="mt-1 text-sm text-red-500">{getFieldError('experience', exp.id, 'startDate')}</p>
                      )}
                    </div>
                    <div>
                      <label className={labelClass}>End Date</label>
                      <input
                        type="date"
                        value={exp.endDate ? format(exp.endDate, 'yyyy-MM-dd') : ''}
                        onChange={(e) => handleItemChange('experience', exp.id, 'endDate', e.target.value ? new Date(e.target.value) : null)}
                        className={inputClass}
                      />
                    </div>
                  </div>
                  <div>
                    <label className={labelClass}>Description</label>
                    <textarea
                      value={exp.description || ''}
                      onChange={(e) => handleItemChange('experience', exp.id, 'description', e.target.value)}
                      className={inputClass}
                      rows={3}
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => toggleEdit('experience', exp.id)}
                      className={buttonSecondaryClass}
                    >
                      <XMarkIcon className="h-4 w-4 mr-1" />
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleEdit('experience', exp.id)}
                      className={buttonPrimaryClass}
                    >
                      <CheckIcon className="h-4 w-4 mr-1" />
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className={titleClass}>{exp.title}</h3>
                      <p className={subtitleClass}>{exp.company}</p>
                      {exp.location && <p className={subtitleClass}>{exp.location}</p>}
                      <p className={subtitleClass}>
                        {formatDate(exp.startDate)} - {exp.endDate ? formatDate(exp.endDate) : 'Present'}
                      </p>
                      {exp.description && (
                        <p className="mt-2 text-slate-300">{exp.description}</p>
                      )}
                    </div>
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={() => toggleEdit('experience', exp.id)}
                        className={buttonSecondaryClass}
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteItem('experience', exp.id)}
                        className={deleteButtonClass}
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Education */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h2 className={sectionHeaderClass}>Education</h2>
          <button
            type="button"
            onClick={() => addNewEntry('education')}
            className={buttonPrimaryClass}
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Education
          </button>
        </div>
        <div className="space-y-4">
          {formData.education.map((edu) => (
            <div key={edu.id} className={cardClass}>
              {edu.isEditing ? (
                <div className="space-y-4">
                  <div>
                    <label className={labelClass}>School</label>
                    <input
                      type="text"
                      value={edu.school}
                      onChange={(e) => handleItemChange('education', edu.id, 'school', e.target.value)}
                      className={inputClass}
                      required
                    />
                    {getFieldError('education', edu.id, 'school') && (
                      <p className="mt-1 text-sm text-red-500">{getFieldError('education', edu.id, 'school')}</p>
                    )}
                  </div>
                  <div>
                    <label className={labelClass}>Degree</label>
                    <input
                      type="text"
                      value={edu.degree}
                      onChange={(e) => handleItemChange('education', edu.id, 'degree', e.target.value)}
                      className={inputClass}
                      required
                    />
                    {getFieldError('education', edu.id, 'degree') && (
                      <p className="mt-1 text-sm text-red-500">{getFieldError('education', edu.id, 'degree')}</p>
                    )}
                  </div>
                  <div>
                    <label className={labelClass}>Field of Study</label>
                    <input
                      type="text"
                      value={edu.field}
                      onChange={(e) => handleItemChange('education', edu.id, 'field', e.target.value)}
                      className={inputClass}
                      required
                    />
                    {getFieldError('education', edu.id, 'field') && (
                      <p className="mt-1 text-sm text-red-500">{getFieldError('education', edu.id, 'field')}</p>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className={labelClass}>Start Date</label>
                      <input
                        type="date"
                        value={format(edu.startDate, 'yyyy-MM-dd')}
                        onChange={(e) => handleItemChange('education', edu.id, 'startDate', new Date(e.target.value))}
                        className={inputClass}
                        required
                      />
                      {getFieldError('education', edu.id, 'startDate') && (
                        <p className="mt-1 text-sm text-red-500">{getFieldError('education', edu.id, 'startDate')}</p>
                      )}
                    </div>
                    <div>
                      <label className={labelClass}>End Date</label>
                      <input
                        type="date"
                        value={edu.endDate ? format(edu.endDate, 'yyyy-MM-dd') : ''}
                        onChange={(e) => handleItemChange('education', edu.id, 'endDate', e.target.value ? new Date(e.target.value) : null)}
                        className={inputClass}
                      />
                    </div>
                  </div>
                  <div>
                    <label className={labelClass}>GPA</label>
                    <input
                      type="number"
                      step="0.01"
                      value={edu.gpa || ''}
                      onChange={(e) => handleItemChange('education', edu.id, 'gpa', e.target.value ? parseFloat(e.target.value) : null)}
                      className={inputClass}
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => toggleEdit('education', edu.id)}
                      className={buttonSecondaryClass}
                    >
                      <XMarkIcon className="h-4 w-4 mr-1" />
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleEdit('education', edu.id)}
                      className={buttonPrimaryClass}
                    >
                      <CheckIcon className="h-4 w-4 mr-1" />
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className={titleClass}>{edu.school}</h3>
                      <p className={subtitleClass}>{edu.degree} in {edu.field}</p>
                      <p className={subtitleClass}>
                        {formatDate(edu.startDate)} - {edu.endDate ? formatDate(edu.endDate) : 'Present'}
                      </p>
                      {edu.gpa && <p className={subtitleClass}>GPA: {edu.gpa}</p>}
                    </div>
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={() => toggleEdit('education', edu.id)}
                        className={buttonSecondaryClass}
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteItem('education', edu.id)}
                        className={deleteButtonClass}
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Projects */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h2 className={sectionHeaderClass}>Projects</h2>
          <button
            type="button"
            onClick={() => addNewEntry('project')}
            className={buttonPrimaryClass}
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Project
          </button>
        </div>
        <div className="space-y-4">
          {formData.projects.map((project) => (
            <div key={project.id} className={cardClass}>
              {project.isEditing ? (
                <div className="space-y-4">
                  <div>
                    <label className={labelClass}>Title</label>
                    <input
                      type="text"
                      value={project.title}
                      onChange={(e) => handleItemChange('projects', project.id, 'title', e.target.value)}
                      className={inputClass}
                      required
                    />
                    {getFieldError('projects', project.id, 'title') && (
                      <p className="mt-1 text-sm text-red-500">{getFieldError('projects', project.id, 'title')}</p>
                    )}
                  </div>
                  <div>
                    <label className={labelClass}>Description</label>
                    <textarea
                      value={project.description || ''}
                      onChange={(e) => handleItemChange('projects', project.id, 'description', e.target.value)}
                      className={inputClass}
                      rows={3}
                    />
                  </div>
                  <div>
                    <label className={labelClass}>URL</label>
                    <input
                      type="url"
                      value={project.url || ''}
                      onChange={(e) => handleItemChange('projects', project.id, 'url', e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className={labelClass}>Date</label>
                    <input
                      type="date"
                      value={project.date ? format(project.date, 'yyyy-MM-dd') : ''}
                      onChange={(e) => handleItemChange('projects', project.id, 'date', e.target.value ? new Date(e.target.value) : null)}
                      className={inputClass}
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => toggleEdit('projects', project.id)}
                      className={buttonSecondaryClass}
                    >
                      <XMarkIcon className="h-4 w-4 mr-1" />
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleEdit('projects', project.id)}
                      className={buttonPrimaryClass}
                    >
                      <CheckIcon className="h-4 w-4 mr-1" />
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className={titleClass}>{project.title}</h3>
                      {project.description && (
                        <p className="mt-2 text-slate-300">{project.description}</p>
                      )}
                      {project.url && (
                        <a
                          href={project.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={linkClass}
                        >
                          <ArrowTopRightOnSquareIcon className="h-4 w-4 mr-1" />
                          View Project
                        </a>
                      )}
                      {project.date && (
                        <p className={subtitleClass}>{formatDate(project.date)}</p>
                      )}
                    </div>
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={() => toggleEdit('projects', project.id)}
                        className={buttonSecondaryClass}
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteItem('projects', project.id)}
                        className={deleteButtonClass}
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Certifications */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h2 className={sectionHeaderClass}>Certifications</h2>
          <button
            type="button"
            onClick={() => addNewEntry('certification')}
            className={buttonPrimaryClass}
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Certification
          </button>
        </div>
        <div className="space-y-4">
          {formData.certifications.map((cert) => (
            <div key={cert.id} className={cardClass}>
              {cert.isEditing ? (
                <div className="space-y-4">
                  <div>
                    <label className={labelClass}>Name</label>
                    <input
                      type="text"
                      value={cert.name}
                      onChange={(e) => handleItemChange('certifications', cert.id, 'name', e.target.value)}
                      className={inputClass}
                      required
                    />
                    {getFieldError('certifications', cert.id, 'name') && (
                      <p className="mt-1 text-sm text-red-500">{getFieldError('certifications', cert.id, 'name')}</p>
                    )}
                  </div>
                  <div>
                    <label className={labelClass}>Issuer</label>
                    <input
                      type="text"
                      value={cert.issuer}
                      onChange={(e) => handleItemChange('certifications', cert.id, 'issuer', e.target.value)}
                      className={inputClass}
                      required
                    />
                    {getFieldError('certifications', cert.id, 'issuer') && (
                      <p className="mt-1 text-sm text-red-500">{getFieldError('certifications', cert.id, 'issuer')}</p>
                    )}
                  </div>
                  <div>
                    <label className={labelClass}>Date</label>
                    <input
                      type="date"
                      value={cert.date ? format(cert.date, 'yyyy-MM-dd') : ''}
                      onChange={(e) => handleItemChange('certifications', cert.id, 'date', e.target.value ? new Date(e.target.value) : null)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className={labelClass}>URL</label>
                    <input
                      type="url"
                      value={cert.url || ''}
                      onChange={(e) => handleItemChange('certifications', cert.id, 'url', e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => toggleEdit('certifications', cert.id)}
                      className={buttonSecondaryClass}
                    >
                      <XMarkIcon className="h-4 w-4 mr-1" />
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleEdit('certifications', cert.id)}
                      className={buttonPrimaryClass}
                    >
                      <CheckIcon className="h-4 w-4 mr-1" />
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className={titleClass}>{cert.name}</h3>
                      <p className={subtitleClass}>{cert.issuer}</p>
                      {cert.date && (
                        <p className={subtitleClass}>{formatDate(cert.date)}</p>
                      )}
                      {cert.url && (
                        <a
                          href={cert.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={linkClass}
                        >
                          <ArrowTopRightOnSquareIcon className="h-4 w-4 mr-1" />
                          View Certificate
                        </a>
                      )}
                    </div>
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={() => toggleEdit('certifications', cert.id)}
                        className={buttonSecondaryClass}
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteItem('certifications', cert.id)}
                        className={deleteButtonClass}
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Publications */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h2 className={sectionHeaderClass}>Publications</h2>
          <button
            type="button"
            onClick={() => addNewEntry('publication')}
            className={buttonPrimaryClass}
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Publication
          </button>
        </div>
        <div className="space-y-4">
          {formData.publications.map((pub) => (
            <div key={pub.id} className={cardClass}>
              {pub.isEditing ? (
                <div className="space-y-4">
                  <div>
                    <label className={labelClass}>Title</label>
                    <input
                      type="text"
                      value={pub.title}
                      onChange={(e) => handleItemChange('publications', pub.id, 'title', e.target.value)}
                      className={inputClass}
                      required
                    />
                    {getFieldError('publications', pub.id, 'title') && (
                      <p className="mt-1 text-sm text-red-500">{getFieldError('publications', pub.id, 'title')}</p>
                    )}
                  </div>
                  <div>
                    <label className={labelClass}>Publisher</label>
                    <input
                      type="text"
                      value={pub.publisher}
                      onChange={(e) => handleItemChange('publications', pub.id, 'publisher', e.target.value)}
                      className={inputClass}
                      required
                    />
                    {getFieldError('publications', pub.id, 'publisher') && (
                      <p className="mt-1 text-sm text-red-500">{getFieldError('publications', pub.id, 'publisher')}</p>
                    )}
                  </div>
                  <div>
                    <label className={labelClass}>Date</label>
                    <input
                      type="date"
                      value={pub.date ? format(pub.date, 'yyyy-MM-dd') : ''}
                      onChange={(e) => handleItemChange('publications', pub.id, 'date', e.target.value ? new Date(e.target.value) : null)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className={labelClass}>Description</label>
                    <textarea
                      value={pub.description || ''}
                      onChange={(e) => handleItemChange('publications', pub.id, 'description', e.target.value)}
                      className={inputClass}
                      rows={3}
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => toggleEdit('publications', pub.id)}
                      className={buttonSecondaryClass}
                    >
                      <XMarkIcon className="h-4 w-4 mr-1" />
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleEdit('publications', pub.id)}
                      className={buttonPrimaryClass}
                    >
                      <CheckIcon className="h-4 w-4 mr-1" />
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className={titleClass}>{pub.title}</h3>
                      <p className={subtitleClass}>{pub.publisher}</p>
                      {pub.date && (
                        <p className={subtitleClass}>{formatDate(pub.date)}</p>
                      )}
                      {pub.description && (
                        <p className="mt-2 text-slate-300">{pub.description}</p>
                      )}
                    </div>
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={() => toggleEdit('publications', pub.id)}
                        className={buttonSecondaryClass}
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteItem('publications', pub.id)}
                        className={deleteButtonClass}
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Additional Sections */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h2 className={sectionHeaderClass}>Additional Sections</h2>
          <button
            type="button"
            onClick={() => addNewEntry('dynamicSection')}
            className={buttonPrimaryClass}
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Section
          </button>
        </div>
        <div className="space-y-6">
          {formData.additionalSections.map((section) => (
            <div key={section.id} className={cardClass}>
              <div className="flex justify-between items-center mb-4">
                <h3 className={titleClass}>{section.title || 'Untitled Section'}</h3>
                <div className="flex space-x-2">
                  <button
                    type="button"
                    onClick={() => toggleEdit('additionalSections', section.id)}
                    className={buttonSecondaryClass}
                  >
                    <PencilIcon className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteItem('additionalSections', section.id)}
                    className={deleteButtonClass}
                  >
                    <XMarkIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {section.isEditing ? (
                <div className="space-y-4">
                  <div>
                    <label className={labelClass}>Section Title</label>
                    <input
                      type="text"
                      value={section.title}
                      onChange={(e) => handleItemChange('additionalSections', section.id, 'title', e.target.value)}
                      className={inputClass}
                      required
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => toggleEdit('additionalSections', section.id)}
                      className={buttonSecondaryClass}
                    >
                      <XMarkIcon className="h-4 w-4 mr-1" />
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleEdit('additionalSections', section.id)}
                      className={buttonPrimaryClass}
                    >
                      <CheckIcon className="h-4 w-4 mr-1" />
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={(event) => handleDragEnd(event, section.id)}
                  >
                    <SortableContext
                      items={section.items.map(item => item.id)}
                      strategy={verticalListSortingStrategy}
                    >
                      <div className="space-y-4">
                        {section.items.map((item) => (
                          <SortableItem key={item.id} id={item.id}>
                            <div className={cardClass}>
                              {item.isEditing ? (
                                <div className="space-y-4">
                                  <div>
                                    <label className={labelClass}>Title</label>
                                    <input
                                      type="text"
                                      value={item.title || ''}
                                      onChange={(e) => handleDynamicItemChange(section.id, item.id, 'title', e.target.value)}
                                      className={inputClass}
                                    />
                                  </div>
                                  <div>
                                    <label className={labelClass}>Subtitle</label>
                                    <input
                                      type="text"
                                      value={item.subtitle || ''}
                                      onChange={(e) => handleDynamicItemChange(section.id, item.id, 'subtitle', e.target.value)}
                                      className={inputClass}
                                    />
                                  </div>
                                  <div className="grid grid-cols-2 gap-4">
                                    <div>
                                      <label className={labelClass}>Date</label>
                                      <input
                                        type="date"
                                        value={item.date ? format(item.date, 'yyyy-MM-dd') : ''}
                                        onChange={(e) => handleDynamicItemChange(section.id, item.id, 'date', e.target.value ? new Date(e.target.value) : null)}
                                        className={inputClass}
                                      />
                                    </div>
                                    <div>
                                      <label className={labelClass}>End Date</label>
                                      <input
                                        type="date"
                                        value={item.endDate ? format(item.endDate, 'yyyy-MM-dd') : ''}
                                        onChange={(e) => handleDynamicItemChange(section.id, item.id, 'endDate', e.target.value ? new Date(e.target.value) : null)}
                                        className={inputClass}
                                      />
                                    </div>
                                  </div>
                                  <div>
                                    <label className={labelClass}>Description</label>
                                    <textarea
                                      value={item.description || ''}
                                      onChange={(e) => handleDynamicItemChange(section.id, item.id, 'description', e.target.value)}
                                      className={inputClass}
                                      rows={3}
                                    />
                                  </div>
                                  <div>
                                    <label className={labelClass}>URL</label>
                                    <input
                                      type="url"
                                      value={item.url || ''}
                                      onChange={(e) => handleDynamicItemChange(section.id, item.id, 'url', e.target.value)}
                                      className={inputClass}
                                    />
                                  </div>
                                  <div className="flex justify-end space-x-2">
                                    <button
                                      type="button"
                                      onClick={() => toggleDynamicItemEdit(section.id, item.id)}
                                      className={buttonSecondaryClass}
                                    >
                                      <XMarkIcon className="h-4 w-4 mr-1" />
                                      Cancel
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => toggleDynamicItemEdit(section.id, item.id)}
                                      className={buttonPrimaryClass}
                                    >
                                      <CheckIcon className="h-4 w-4 mr-1" />
                                      Save
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <div>
                                  <div className="flex justify-between items-start">
                                    <div>
                                      {item.title && <h4 className={titleClass}>{item.title}</h4>}
                                      {item.subtitle && <p className={subtitleClass}>{item.subtitle}</p>}
                                      {(item.date || item.endDate) && (
                                        <p className={subtitleClass}>
                                          {item.date ? formatDate(item.date) : ''}
                                          {item.date && item.endDate ? ' - ' : ''}
                                          {item.endDate ? formatDate(item.endDate) : ''}
                                        </p>
                                      )}
                                      {item.description && (
                                        <p className="mt-2 text-slate-300">{item.description}</p>
                                      )}
                                      {item.url && (
                                        <a
                                          href={item.url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className={linkClass}
                                        >
                                          <ArrowTopRightOnSquareIcon className="h-4 w-4 mr-1" />
                                          View Link
                                        </a>
                                      )}
                                    </div>
                                    <div className="flex space-x-2">
                                      <button
                                        type="button"
                                        onClick={() => toggleDynamicItemEdit(section.id, item.id)}
                                        className={buttonSecondaryClass}
                                      >
                                        <PencilIcon className="h-4 w-4" />
                                      </button>
                                      <button
                                        type="button"
                                        onClick={() => handleDeleteDynamicItem(section.id, item.id)}
                                        className={deleteButtonClass}
                                      >
                                        <XMarkIcon className="h-4 w-4" />
                                      </button>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </SortableItem>
                        ))}
                      </div>
                    </SortableContext>
                  </DndContext>
                  <div className="mt-4">
                    <button
                      type="button"
                      onClick={() => addDynamicSectionItem(section.id)}
                      className={buttonSecondaryClass}
                    >
                      <PlusIcon className="h-4 w-4 mr-1" />
                      Add Item
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Import from Social Media */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h2 className={sectionHeaderClass}>Import from Social Media</h2>
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className={buttonPrimaryClass}
          >
            {showPassword ? (
              <>
                <EyeSlashIcon className="h-4 w-4 mr-1" />
                Hide Password
              </>
            ) : (
              <>
                <EyeIcon className="h-4 w-4 mr-1" />
                Show Password
              </>
            )}
          </button>
        </div>
        <div className="space-y-4">
          {showPassword && (
            <div>
              <label className={labelClass}>Password</label>
              <input
                type="password"
                value={importPassword}
                onChange={(e) => setImportPassword(e.target.value)}
                className={inputClass}
                placeholder="Enter your password"
              />
            </div>
          )}
          <button
            type="button"
            onClick={handleImportFromSocialMedia}
            disabled={isImporting}
            className={buttonPrimaryClass}
          >
            {isImporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Importing...
              </>
            ) : (
              <>
                <CloudArrowDownIcon className="h-4 w-4 mr-1" />
                Import Profile Data
              </>
            )}
          </button>
        </div>
      </div>

      {/* Submit Button */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isSubmitting}
          className={`${buttonPrimaryClass} ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            'Save Profile'
          )}
        </button>
      </div>

      {/* Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={showConfirmation}
        title="Delete Item"
        message="Are you sure you want to delete this item? This action cannot be undone."
        confirmButtonText="Delete"
        cancelButtonText="Cancel"
        onConfirm={() => {
          if (deleteType && itemToDelete) {
            setFormData(prev => ({
              ...prev,
              [deleteType]: prev[deleteType].filter(item => item.id !== itemToDelete)
            }));
          }
          setShowConfirmation(false);
          setItemToDelete(null);
          setDeleteType(null);
        }}
        onCancel={() => {
          setShowConfirmation(false);
          setItemToDelete(null);
          setDeleteType(null);
        }}
      />
    </form>
  );
} 