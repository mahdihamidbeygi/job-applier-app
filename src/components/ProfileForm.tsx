'use client';

import { useState, useEffect, useCallback, type FC } from 'react';
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
  DragEndEvent,
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

// Add new schemas for publications and certifications
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

// Add a new schema for projects
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

// Update the form schema to include projects
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

type Experience = z.infer<typeof experienceSchema>;
type Education = z.infer<typeof educationSchema>;
type Publication = z.infer<typeof publicationSchema>;
type Certification = z.infer<typeof certificationSchema>;
type Project = z.infer<typeof projectSchema>;
type DynamicSectionItem = z.infer<typeof dynamicSectionItemSchema>;
type DynamicSection = z.infer<typeof dynamicSectionSchema>;
type FormData = z.infer<typeof formSchema>;

interface ValidationErrors {
  [key: string]: string;
}

interface SortableItemProps {
  id: string;
  children: React.ReactNode;
}

const SortableItem: FC<SortableItemProps> = ({ id, children }) => {
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

interface ProfileFormProps {
  initialData: {
    linkedInUrl: string;
    githubUrl: string;
    portfolioUrl: string;
    bio: string;
    skills: string[];
    experience?: Experience[];
    education?: Education[];
    publications?: Publication[];
    certifications?: Certification[];
    projects?: Project[];
    additionalSections?: DynamicSection[];
  };
}

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

// Update delete button styles
const deleteButtonClass = "inline-flex items-center px-3 py-1 border border-red-900 text-sm font-medium rounded-md text-red-200 bg-red-900/50 hover:bg-red-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500";
const linkClass = "inline-flex items-center text-sm text-slate-300 hover:text-slate-100";
const skillTagClass = "inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium bg-slate-700 text-slate-200 group";
const skillTagButtonClass = "ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full text-slate-300 hover:text-slate-100 focus:outline-none";

// Helper function to check if two projects are duplicates
const areProjectsDuplicate = (proj1: Project, proj2: Project): boolean => {
  return (
    proj1.title.toLowerCase() === proj2.title.toLowerCase() &&
    (proj1.url === proj2.url || (!proj1.url && !proj2.url))
  );
};

// Helper function to check if two certifications are duplicates
const areCertificationsDuplicate = (cert1: Certification, cert2: Certification): boolean => {
  return (
    cert1.name.toLowerCase() === cert2.name.toLowerCase() &&
    cert1.issuer.toLowerCase() === cert2.issuer.toLowerCase()
  );
};

// Helper function to validate a record
const isValidRecord = (record: Record<string, unknown>, type: string): boolean => {
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

// Helper function to filter out duplicates from an array
const removeDuplicates = <T,>(items: T[], compareFn: (a: T, b: T) => boolean): T[] => {
  return items.reduce((unique: T[], item: T) => {
    const isDuplicate = unique.some(existingItem => compareFn(existingItem, item));
    if (!isDuplicate) {
      unique.push(item);
    }
    return unique;
  }, []);
};

const ProfileForm: FC<ProfileFormProps> = ({ initialData }) => {
  const [formData, setFormData] = useState<FormData>({
    ...initialData,
    experience: initialData.experience?.map(exp => ({ ...exp, isEditing: false, isDirty: false })) || [],
    education: initialData.education?.map(edu => ({ ...edu, isEditing: false, isDirty: false })) || [],
    publications: initialData.publications?.map(pub => ({ ...pub, isEditing: false, isDirty: false })) || [],
    certifications: initialData.certifications?.map(cert => ({ ...cert, isEditing: false, isDirty: false })) || [],
    projects: initialData.projects?.map(proj => ({ ...proj, isEditing: false, isDirty: false })) || [],
    additionalSections: initialData.additionalSections || []
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [lastSavedData, setLastSavedData] = useState<FormData>(formData);
  const router = useRouter();
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [confirmationDialog, setConfirmationDialog] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
  });

  const validateField = (value: unknown, fieldName: string): string | null => {
    try {
      if (fieldName.includes('Url')) {
        urlSchema.parse(value);
      } else if (fieldName.includes('Date')) {
        const date = value as Date;
        if (!isValid(date)) {
          return 'Please enter a valid date';
        }
        if (fieldName.includes('endDate') && value) {
          const startDate = fieldName.includes('experience') 
            ? formData.experience.find(e => e.id === fieldName.split('-')[1])?.startDate
            : formData.education.find(e => e.id === fieldName.split('-')[1])?.startDate;
          
          if (startDate && isBefore(date, startDate)) {
            return 'End date must be after start date';
          }
        }
      }
      return null;
    } catch (err) {
      return err instanceof z.ZodError ? err.errors[0].message : 'Invalid value';
    }
  };

  const addNewEntry = (type: 'experience' | 'education' | 'publication' | 'certification' | 'project' | 'dynamicSection') => {
    const newId = uuidv4();
    const today = new Date();
    
    switch (type) {
      case 'experience':
        const newExperience: Experience = {
          id: newId,
          profileId: formData.experience[0]?.profileId || '',
          title: '',
          company: '',
          location: '',
          startDate: today,
          endDate: null,
          description: '',
          skills: [],
          isEditing: true,
          isDirty: true
        };
        setFormData(prev => ({
          ...prev,
          experience: [newExperience, ...prev.experience]
        }));
        break;
      
      case 'education':
        const newEducation: Education = {
          id: newId,
          profileId: formData.education[0]?.profileId || '',
          school: '',
          degree: '',
          field: '',
          startDate: today,
          endDate: null,
          gpa: null,
          isEditing: true,
          isDirty: true
        };
        setFormData(prev => ({
          ...prev,
          education: [newEducation, ...prev.education]
        }));
        break;
      
      case 'publication':
        const newPublication: Publication = {
          id: newId,
          profileId: formData.publications[0]?.profileId || '',
          title: '',
          publisher: '',
          date: today,
          description: '',
          isEditing: true,
          isDirty: true
        };
        setFormData(prev => ({
          ...prev,
          publications: [newPublication, ...prev.publications]
        }));
        break;
      
      case 'certification':
        const newCertification: Certification = {
          id: newId,
          profileId: formData.certifications[0]?.profileId || '',
          name: '',
          issuer: '',
          date: today,
          url: '',
          isEditing: true,
          isDirty: true
        };
        setFormData(prev => ({
          ...prev,
          certifications: [newCertification, ...prev.certifications]
        }));
        break;
      
      case 'project':
        const newProject: Project = {
          id: newId,
          profileId: formData.projects[0]?.profileId || '',
          title: '',
          description: '',
          url: '',
          date: today,
          isEditing: true,
          isDirty: true
        };
        setFormData(prev => ({
          ...prev,
          projects: [newProject, ...prev.projects]
        }));
        break;
      
      case 'dynamicSection':
        const newDynamicSection = {
          id: newId,
          type: '',
          title: '',
          items: [],
          isEditing: true,
          isDirty: true
        };
        setFormData(prev => ({
          ...prev,
          additionalSections: [newDynamicSection, ...prev.additionalSections]
        }));
        break;
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    if (name in formData) {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
    
    const error = validateField(value, name);
    if (error) {
      setValidationErrors(prev => ({
        ...prev,
        [name]: error
      }));
    } else {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { [name]: _, ...rest } = validationErrors;
      setValidationErrors(rest);
    }
  };

  const handleSkillsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const skills = e.target.value.split(',').map(skill => skill.trim()).filter(Boolean);
    setFormData(prev => ({ ...prev, skills }));
  };

  const removeSkill = (skillToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.filter(skill => skill !== skillToRemove)
    }));
  };

  const handleClearAllSkills = () => {
    setConfirmationDialog({
      isOpen: true,
      title: 'Clear All Skills',
      message: 'Are you sure you want to remove all skills? This action cannot be undone.',
      onConfirm: async () => {
        // Update the state
        const updatedFormData = {
          ...formData,
          skills: []
        };
        
        setFormData(updatedFormData);
        
        // Close the dialog
        setConfirmationDialog(prev => ({ ...prev, isOpen: false }));
        
        // Save changes to database directly
        try {
          console.log('Clearing all skills');
          
          // Remove isEditing and isDirty flags before submission
          const cleanFormData = {
            ...updatedFormData,
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            experience: updatedFormData.experience.map(({ isEditing, isDirty, ...exp }) => exp),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            education: updatedFormData.education.map(({ isEditing, isDirty, ...edu }) => edu),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            publications: updatedFormData.publications.map(({ isEditing, isDirty, ...pub }) => pub),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            certifications: updatedFormData.certifications.map(({ isEditing, isDirty, ...cert }) => cert),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            projects: updatedFormData.projects.map(({ isEditing, isDirty, ...proj }) => proj),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            additionalSections: updatedFormData.additionalSections.map(({ isEditing, isDirty, ...section }) => section)
          };
          
          const response = await fetch('/api/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cleanFormData),
          });
          
          if (!response.ok) {
            throw new Error('Failed to save profile after clearing skills');
          }
          
          console.log('Successfully cleared all skills and saved to database');
          setLastSavedData(updatedFormData);
          
          // Refresh the page to show the updated data
          router.refresh();
        } catch (error) {
          console.error('Error saving data after clearing skills:', error);
          setError(error instanceof Error ? error.message : 'An error occurred while saving data');
        }
      },
    });
  };

  const formatDate = (date: Date | null | undefined) => {
    if (!date) return '';
    return format(date, 'yyyy-MM-dd');
  };

  // Update type definitions for form data and handlers
  type SectionType = 'experience' | 'education' | 'publications' | 'certifications' | 'projects' | 'additionalSections';

  const handleItemChange = (
    type: SectionType,
    id: string,
    field: string,
    value: string | Date | null | number
  ) => {
    setFormData((prevData: FormData) => {
      if (type === 'additionalSections') {
        return {
          ...prevData,
          additionalSections: prevData.additionalSections.map(section =>
            section.id === id ? { ...section, [field]: value, isDirty: true } : section
          )
        };
      }
      return {
        ...prevData,
        [type]: prevData[type].map(item =>
          item.id === id ? { ...item, [field]: value, isDirty: true } : item
        )
      };
    });

    const validationError = validateField(value, `${type}-${id}-${field}`);
    if (validationError) {
      setValidationErrors(prev => ({
        ...prev,
        [`${type}-${id}-${field}`]: validationError
      }));
    } else {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { [`${type}-${id}-${field}`]: _, ...rest } = validationErrors;
      setValidationErrors(rest);
    }
  };

  const toggleEdit = (type: SectionType, id: string) => {
    setFormData(prev => {
      if (type === 'additionalSections') {
        return {
          ...prev,
          additionalSections: prev.additionalSections.map(section =>
            section.id === id ? { ...section, isEditing: !section.isEditing } : section
          )
        };
      }
      return {
        ...prev,
        [type]: prev[type].map(item =>
          item.id === id ? { ...item, isEditing: !item.isEditing } : item
        )
      };
    });
  };

  const handleDeleteItem = (type: SectionType, id: string) => {
    const itemType = type === 'additionalSections' ? 'section' : type.slice(0, -1);
    
    setConfirmationDialog({
      isOpen: true,
      title: `Delete ${itemType}`,
      message: `Are you sure you want to delete this ${itemType}? This action cannot be undone.`,
      onConfirm: async () => {
        // First update the state
        const updatedFormData = type === 'additionalSections'
          ? {
              ...formData,
              additionalSections: formData.additionalSections.filter(section => section.id !== id)
            }
          : {
              ...formData,
              [type]: formData[type].filter(item => item.id !== id)
            };
        
        // Update the state
        setFormData(updatedFormData);
        
        // Close the dialog
        setConfirmationDialog(prev => ({ ...prev, isOpen: false }));
        
        // Save changes to database directly
        try {
          console.log(`Deleting ${itemType} with ID: ${id}`);
          
          // Remove isEditing and isDirty flags before submission
          const cleanFormData = {
            ...updatedFormData,
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            experience: updatedFormData.experience.map(({ isEditing, isDirty, ...exp }) => exp),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            education: updatedFormData.education.map(({ isEditing, isDirty, ...edu }) => edu),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            publications: updatedFormData.publications.map(({ isEditing, isDirty, ...pub }) => pub),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            certifications: updatedFormData.certifications.map(({ isEditing, isDirty, ...cert }) => cert),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            projects: updatedFormData.projects.map(({ isEditing, isDirty, ...proj }) => proj),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            additionalSections: updatedFormData.additionalSections.map(({ isEditing, isDirty, ...section }) => section)
          };
          
          const response = await fetch('/api/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cleanFormData),
          });
          
          if (!response.ok) {
            throw new Error('Failed to save profile after deletion');
          }
          
          console.log(`Successfully deleted ${itemType} and saved to database`);
          setLastSavedData(updatedFormData);
          
          // Refresh the page to show the updated data
          router.refresh();
        } catch (error) {
          console.error('Error saving data after deletion:', error);
          setError(error instanceof Error ? error.message : 'An error occurred while saving data');
        }
      },
    });
  };

  const handleDeleteDynamicItem = (sectionId: string, itemId: string) => {
    setConfirmationDialog({
      isOpen: true,
      title: 'Delete item',
      message: 'Are you sure you want to delete this item? This action cannot be undone.',
      onConfirm: async () => {
        // First update the state
        const updatedFormData = {
          ...formData,
          additionalSections: formData.additionalSections.map(section =>
            section.id === sectionId
              ? { ...section, items: section.items.filter(item => item.id !== itemId) }
              : section
          )
        };
        
        // Update the state
        setFormData(updatedFormData);
        
        // Close the dialog
        setConfirmationDialog(prev => ({ ...prev, isOpen: false }));
        
        // Save changes to database directly
        try {
          console.log(`Deleting dynamic item with ID: ${itemId} from section: ${sectionId}`);
          
          // Remove isEditing and isDirty flags before submission
          const cleanFormData = {
            ...updatedFormData,
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            experience: updatedFormData.experience.map(({ isEditing, isDirty, ...exp }) => exp),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            education: updatedFormData.education.map(({ isEditing, isDirty, ...edu }) => edu),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            publications: updatedFormData.publications.map(({ isEditing, isDirty, ...pub }) => pub),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            certifications: updatedFormData.certifications.map(({ isEditing, isDirty, ...cert }) => cert),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            projects: updatedFormData.projects.map(({ isEditing, isDirty, ...proj }) => proj),
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            additionalSections: updatedFormData.additionalSections.map(({ isEditing, isDirty, ...section }) => section)
          };
          
          const response = await fetch('/api/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cleanFormData),
          });
          
          if (!response.ok) {
            throw new Error('Failed to save profile after deletion');
          }
          
          console.log('Successfully deleted dynamic item and saved to database');
          setLastSavedData(updatedFormData);
          
          // Refresh the page to show the updated data
          router.refresh();
        } catch (error) {
          console.error('Error saving data after deletion:', error);
          setError(error instanceof Error ? error.message : 'An error occurred while saving data');
        }
      },
    });
  };

  const handleSubmit = useCallback(async (e?: React.FormEvent, isAutoSave = false) => {
    if (e) {
      e.preventDefault();
    }
    
    setIsSubmitting(true);
    setError(null);

    try {
      // Validate form data using Zod
      formSchema.parse(formData);

      // Remove isEditing and isDirty flags before submission
      const cleanFormData = {
        ...formData,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        experience: formData.experience.map(({ isEditing, isDirty, ...exp }) => exp),
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        education: formData.education.map(({ isEditing, isDirty, ...edu }) => edu),
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        publications: formData.publications.map(({ isEditing, isDirty, ...pub }) => pub),
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        certifications: formData.certifications.map(({ isEditing, isDirty, ...cert }) => cert),
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        projects: formData.projects.map(({ isEditing, isDirty, ...proj }) => proj),
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        additionalSections: formData.additionalSections.map(({ isEditing, isDirty, ...section }) => section)
      };

      console.log('Sending data to API:', {
        publications: cleanFormData.publications,
        certifications: cleanFormData.certifications
      });

      const response = await fetch('/api/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cleanFormData),
      });

      if (!response.ok) {
        throw new Error('Failed to save profile');
      }

      setLastSavedData(formData);
      if (!isAutoSave) {
        router.refresh();
      }
    } catch (err) {
      if (err instanceof z.ZodError) {
        const errors: ValidationErrors = {};
        err.errors.forEach(error => {
          const path = error.path.join('.');
          errors[path] = error.message;
        });
        setValidationErrors(errors);
      } else {
        setError(err instanceof Error ? err.message : 'An error occurred');
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, router]);

  const getFieldError = (type: string, id: string | null, field: string) => {
    return id ? validationErrors[`${type}-${id}-${field}`] : validationErrors[field];
  };

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent, sectionId: string) => {
    const { active, over } = event;

    if (active && over && active.id !== over.id) {
      setFormData((prev) => {
        const section = prev.additionalSections.find(s => s.id === sectionId);
        if (!section) return prev;

        const oldIndex = section.items.findIndex(item => item.id === active.id);
        const newIndex = section.items.findIndex(item => item.id === over.id);

        if (oldIndex === -1 || newIndex === -1) return prev;

        const newItems = arrayMove(section.items, oldIndex, newIndex);

        return {
          ...prev,
          additionalSections: prev.additionalSections.map(s =>
            s.id === sectionId ? { ...s, items: newItems } : s
          ),
        };
      });
    }
  };

  const addDynamicSectionItem = (sectionId: string) => {
    const newItem: DynamicSectionItem = {
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
      additionalSections: prev.additionalSections.map(section =>
        section.id === sectionId
          ? { ...section, items: [newItem, ...section.items] }
          : section
      )
    }));
  };

  const handleDynamicItemChange = (
    sectionId: string,
    itemId: string,
    field: string,
    value: string | Date | null
  ) => {
    setFormData(prev => ({
      ...prev,
      additionalSections: prev.additionalSections.map(section =>
        section.id === sectionId
          ? {
              ...section,
              items: section.items.map(item =>
                item.id === itemId
                  ? { ...item, [field]: value, isDirty: true }
                  : item
              )
            }
          : section
      )
    }));
  };

  const toggleDynamicItemEdit = (sectionId: string, itemId: string) => {
    setFormData(prev => ({
      ...prev,
      additionalSections: prev.additionalSections.map(section =>
        section.id === sectionId
          ? {
              ...section,
              items: section.items.map(item =>
                item.id === itemId
                  ? { ...item, isEditing: !item.isEditing }
                  : item
              )
            }
          : section
      )
    }));
  };

  // Update the handleImportFromSocialMedia function
  const handleImportFromSocialMedia = async () => {
    try {
      setIsImporting(true);
      setImportError(null);
      
      const { githubUrl } = formData;
      
      if (!githubUrl) {
        setImportError('Please provide your GitHub URL');
        return;
      }
      
      console.log("Starting import from GitHub...");
      
      // Call the API endpoint instead of the function directly
      const response = await fetch('/api/profile/enrich', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          githubUrl
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to import data');
      }
      
      const { data: enrichedData } = await response.json();
      console.log("Received enriched data:", enrichedData);
      
      if (!enrichedData.github) {
        setImportError('Could not retrieve data from the provided GitHub URL. Please check the URL and try again.');
        return;
      }
      
      // Create a new form data object with the enriched data
      const updatedFormData = { ...formData };
      
      // Add GitHub data
      console.log("Processing GitHub data...");
      
      // Add projects (formerly repositories)
      if (enrichedData.github.projects && enrichedData.github.projects.length > 0) {
        console.log("GitHub projects found:", enrichedData.github.projects.length);
        
        // Filter valid projects
        const validProjects = enrichedData.github.projects
          .filter((proj: Record<string, unknown>) => isValidRecord(proj, 'project'))
          .map((proj: Project) => ({
            ...proj,
            profileId: formData.projects[0]?.profileId || '',
            isEditing: false,
            isDirty: true
          }));
        
        // Combine with existing projects and remove duplicates
        const allProjects = [...validProjects, ...formData.projects];
        updatedFormData.projects = removeDuplicates(allProjects, areProjectsDuplicate);
        
        console.log("Valid projects after deduplication:", updatedFormData.projects.length);
      }
      
      // Add certifications
      if (enrichedData.github.certifications && enrichedData.github.certifications.length > 0) {
        // Filter valid certifications
        const validCertifications = enrichedData.github.certifications
          .filter((cert: Record<string, unknown>) => isValidRecord(cert, 'certification'))
          .map((cert: Certification) => ({
            ...cert,
            profileId: formData.certifications[0]?.profileId || '',
            isEditing: false,
            isDirty: true
          }));
        
        // Combine with existing certifications and remove duplicates
        const allCertifications = [...validCertifications, ...formData.certifications];
        updatedFormData.certifications = removeDuplicates(allCertifications, areCertificationsDuplicate);
      }
      
      // Add skills
      if (enrichedData.github.skills && enrichedData.github.skills.length > 0) {
        // Filter out empty skills and normalize
        const validSkills = enrichedData.github.skills
          .filter((skill: string) => Boolean(skill && skill.trim()))
          .map((skill: string) => skill.trim());
        
        // Use Set to automatically remove duplicates
        const existingSkills = new Set(formData.skills);
        validSkills.forEach((skill: string) => existingSkills.add(skill));
        updatedFormData.skills = Array.from(existingSkills);
      }
      
      // Update bio if empty
      if (!formData.bio && enrichedData.github.bio) {
        updatedFormData.bio = enrichedData.github.bio;
      }
      
      console.log("Updated form data:", updatedFormData);
      console.log("Projects count after validation and deduplication:", updatedFormData.projects.length);
      
      // Update the form data
      setFormData(updatedFormData);
      
      // Manually save the data to the database
      try {
        console.log("Saving data to database...");
        
        // Remove isEditing and isDirty flags before submission
        const cleanFormData = {
          ...updatedFormData,
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          experience: updatedFormData.experience.map(({ isEditing, isDirty, ...exp }) => exp),
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          education: updatedFormData.education.map(({ isEditing, isDirty, ...edu }) => edu),
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          publications: updatedFormData.publications.map(({ isEditing, isDirty, ...pub }) => pub),
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          certifications: updatedFormData.certifications.map(({ isEditing, isDirty, ...cert }) => cert),
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          projects: updatedFormData.projects.map(({ isEditing, isDirty, ...proj }) => proj),
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          additionalSections: updatedFormData.additionalSections.map(({ isEditing, isDirty, ...section }) => section)
        };
        
        const saveResponse = await fetch('/api/profile', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(cleanFormData),
        });
        
        if (!saveResponse.ok) {
          throw new Error('Failed to save profile');
        }
        
        console.log("Data saved successfully!");
        setLastSavedData(updatedFormData);
        
        // Refresh the page to show the updated data
        router.refresh();
      } catch (saveError) {
        console.error("Error saving data:", saveError);
        setError(saveError instanceof Error ? saveError.message : 'An error occurred while saving data');
      }
      
    } catch (error) {
      console.error('Error importing data from GitHub:', error);
      setImportError(error instanceof Error ? error.message : 'An error occurred while importing data. Please try again later.');
    } finally {
      setIsImporting(false);
    }
  };

  // Auto-save functionality - moved after handleSubmit definition
  useEffect(() => {
    const hasChanges = JSON.stringify(formData) !== JSON.stringify(lastSavedData);
    if (hasChanges) {
      const timeoutId = setTimeout(() => {
        handleSubmit(undefined, true);
      }, 3000);
      return () => clearTimeout(timeoutId);
    }
  }, [formData, lastSavedData, handleSubmit]);

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={confirmationDialog.isOpen}
        title={confirmationDialog.title}
        message={confirmationDialog.message}
        confirmButtonText="Delete"
        cancelButtonText="Cancel"
        onConfirm={confirmationDialog.onConfirm}
        onCancel={() => setConfirmationDialog(prev => ({ ...prev, isOpen: false }))}
      />

      {/* Preview Mode Toggle */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setIsPreviewMode(!isPreviewMode)}
          className={buttonSecondaryClass}
        >
          {isPreviewMode ? (
            <>
              <EyeSlashIcon className="h-4 w-4 mr-2" />
              Edit Mode
            </>
          ) : (
            <>
              <EyeIcon className="h-4 w-4 mr-2" />
              Preview Mode
            </>
          )}
        </button>
      </div>

      {/* Professional Summary */}
      <div className={sectionClass}>
        <h3 className={sectionHeaderClass}>Professional Summary</h3>
        <div className="relative">
          <textarea
            id="bio"
            name="bio"
            value={formData.bio}
            onChange={handleChange}
            rows={4}
            placeholder="Write a brief professional bio..."
            className={`${inputClass} ${
              validationErrors.bio ? 'border-red-300' : 'border-gray-300'
            }`}
            readOnly={isPreviewMode}
          />
          {validationErrors.bio && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
            </div>
          )}
        </div>
        {validationErrors.bio && (
          <p className="mt-2 text-sm text-red-300">{validationErrors.bio}</p>
        )}
      </div>

      {/* Skills Section */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h3 className={sectionHeaderClass.replace(" mb-4", "")}>Skills</h3>
          {!isPreviewMode && formData.skills.length > 0 && (
            <BulkDeleteButton 
              onClick={handleClearAllSkills} 
              label="Clear All" 
            />
          )}
        </div>
        {!isPreviewMode && (
          <input
            type="text"
            id="skills"
            name="skills"
            value={formData.skills.join(', ')}
            onChange={handleSkillsChange}
            placeholder="React, TypeScript, Node.js"
            className={`${inputClass} ${
              validationErrors.skills ? 'border-red-300' : 'border-slate-600'
            }`}
          />
        )}
        <div className="mt-2 flex flex-wrap gap-2">
          {formData.skills.map((skill, index) => (
            <div
              key={index}
              className={skillTagClass}
            >
              {skill}
              {!isPreviewMode && (
                <button
                  type="button"
                  onClick={() => removeSkill(skill)}
                  className={skillTagButtonClass}
                >
                  <XMarkIcon className="w-3 h-3" />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Experience Section */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h3 className={sectionHeaderClass.replace(" mb-4", "")}>Experience</h3>
          {!isPreviewMode && (
            <button
              type="button"
              onClick={() => addNewEntry('experience')}
              className={buttonPrimaryClass}
            >
              <PlusIcon className="h-4 w-4 mr-2" />
              Add Experience
            </button>
          )}
        </div>
        <div className="space-y-6">
          {formData.experience.map((exp) => (
            <Transition
              key={exp.id}
              show={true}
              enter="transition ease-out duration-200"
              enterFrom="opacity-0 translate-y-1"
              enterTo="opacity-100 translate-y-0"
              leave="transition ease-in duration-150"
              leaveFrom="opacity-100 translate-y-0"
              leaveTo="opacity-0 translate-y-1"
            >
              <div className="border-b border-slate-700 pb-4 last:border-0">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className={labelClass}>Title</label>
                        <div className="relative">
                          <input
                            type="text"
                            value={exp.title}
                            onChange={e => handleItemChange('experience', exp.id, 'title', e.target.value)}
                            className={`${inputClass} ${
                              getFieldError('experience', exp.id, 'title') ? 'border-red-300' : 'border-slate-600'
                            }`}
                            readOnly={!exp.isEditing || isPreviewMode}
                          />
                          {getFieldError('experience', exp.id, 'title') && (
                            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                              <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
                            </div>
                          )}
                        </div>
                        {getFieldError('experience', exp.id, 'title') && (
                          <p className="mt-2 text-sm text-red-300">
                            {getFieldError('experience', exp.id, 'title')}
                          </p>
                        )}
                      </div>
                      <div>
                        <label className={labelClass}>Company</label>
                        <div className="relative">
                          <input
                            type="text"
                            value={exp.company}
                            onChange={e => handleItemChange('experience', exp.id, 'company', e.target.value)}
                            className={`${inputClass} ${
                              getFieldError('experience', exp.id, 'company') ? 'border-red-300' : 'border-gray-300'
                            }`}
                            readOnly={!exp.isEditing || isPreviewMode}
                          />
                          {getFieldError('experience', exp.id, 'company') && (
                            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                              <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
                            </div>
                          )}
                        </div>
                        {getFieldError('experience', exp.id, 'company') && (
                          <p className="mt-2 text-sm text-red-300">
                            {getFieldError('experience', exp.id, 'company')}
                          </p>
                        )}
                      </div>
                      <div>
                        <label className={labelClass}>Location</label>
                        <div className="relative">
                          <input
                            type="text"
                            value={exp.location || ''}
                            onChange={e => handleItemChange('experience', exp.id, 'location', e.target.value)}
                            placeholder="City, State, Country"
                            className={`${inputClass} ${
                              getFieldError('experience', exp.id, 'location') ? 'border-red-300' : 'border-gray-300'
                            }`}
                            readOnly={!exp.isEditing || isPreviewMode}
                          />
                          {getFieldError('experience', exp.id, 'location') && (
                            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                              <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
                            </div>
                          )}
                        </div>
                        {getFieldError('experience', exp.id, 'location') && (
                          <p className="mt-2 text-sm text-red-300">
                            {getFieldError('experience', exp.id, 'location')}
                          </p>
                        )}
                      </div>
                      <div>
                        <label className={labelClass}>Start Date</label>
                        <div className="relative">
                          <input
                            type="date"
                            value={formatDate(exp.startDate)}
                            onChange={e => handleItemChange('experience', exp.id, 'startDate', new Date(e.target.value))}
                            className={`${inputClass} ${
                              getFieldError('experience', exp.id, 'startDate') ? 'border-red-300' : 'border-gray-300'
                            }`}
                            readOnly={!exp.isEditing || isPreviewMode}
                          />
                          {getFieldError('experience', exp.id, 'startDate') && (
                            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                              <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
                            </div>
                          )}
                        </div>
                        {getFieldError('experience', exp.id, 'startDate') && (
                          <p className="mt-2 text-sm text-red-300">
                            {getFieldError('experience', exp.id, 'startDate')}
                          </p>
                        )}
                      </div>
                      <div>
                        <label className={labelClass}>End Date</label>
                        <div className="relative">
                          <input
                            type="date"
                            value={formatDate(exp.endDate)}
                            onChange={e => handleItemChange('experience', exp.id, 'endDate', e.target.value ? new Date(e.target.value) : null)}
                            className={`${inputClass} ${
                              getFieldError('experience', exp.id, 'endDate') ? 'border-red-300' : 'border-gray-300'
                            }`}
                            readOnly={!exp.isEditing || isPreviewMode}
                          />
                          {getFieldError('experience', exp.id, 'endDate') && (
                            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                              <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
                            </div>
                          )}
                        </div>
                        {getFieldError('experience', exp.id, 'endDate') && (
                          <p className="mt-2 text-sm text-red-300">
                            {getFieldError('experience', exp.id, 'endDate')}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="mt-4">
                      <label className={labelClass}>Description</label>
                      <div className="relative">
                        <textarea
                          value={exp.description || ''}
                          onChange={e => handleItemChange('experience', exp.id, 'description', e.target.value)}
                          rows={3}
                          className={`${inputClass} ${
                            getFieldError('experience', exp.id, 'description') ? 'border-red-300' : 'border-gray-300'
                          }`}
                          readOnly={!exp.isEditing || isPreviewMode}
                        />
                        {getFieldError('experience', exp.id, 'description') && (
                          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                            <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
                          </div>
                        )}
                      </div>
                      {getFieldError('experience', exp.id, 'description') && (
                        <p className="mt-2 text-sm text-red-300">
                          {getFieldError('experience', exp.id, 'description')}
                        </p>
                      )}
                    </div>
                  </div>
                  {!isPreviewMode && (
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={() => toggleEdit('experience', exp.id)}
                        className={buttonSecondaryClass}
                      >
                        {exp.isEditing ? (
                          <CheckIcon className="h-4 w-4" />
                        ) : (
                          <PencilIcon className="h-4 w-4" />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteItem('experience', exp.id)}
                        className={deleteButtonClass}
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </Transition>
          ))}
        </div>
      </div>

      {/* Education Section */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h3 className={sectionHeaderClass.replace(" mb-4", "")}>Education</h3>
          {!isPreviewMode && (
            <button
              type="button"
              onClick={() => addNewEntry('education')}
              className={buttonPrimaryClass}
            >
              <PlusIcon className="h-4 w-4 mr-2" />
              Add Education
            </button>
          )}
        </div>
        <div className="space-y-6">
          {formData.education.map((edu) => (
            <Transition
              key={edu.id}
              show={true}
              enter="transition ease-out duration-200"
              enterFrom="opacity-0 translate-y-1"
              enterTo="opacity-100 translate-y-0"
              leave="transition ease-in duration-150"
              leaveFrom="opacity-100 translate-y-0"
              leaveTo="opacity-0 translate-y-1"
            >
              <div className="border-b border-slate-700 pb-4 last:border-0">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className={labelClass}>School</label>
                        <input
                          type="text"
                          value={edu.school}
                          onChange={e => handleItemChange('education', edu.id, 'school', e.target.value)}
                          className={inputClass}
                          readOnly={!edu.isEditing || isPreviewMode}
                        />
                      </div>
                      <div>
                        <label className={labelClass}>Degree</label>
                        <input
                          type="text"
                          value={edu.degree}
                          onChange={e => handleItemChange('education', edu.id, 'degree', e.target.value)}
                          className={inputClass}
                          readOnly={!edu.isEditing || isPreviewMode}
                        />
                      </div>
                      <div>
                        <label className={labelClass}>Field</label>
                        <input
                          type="text"
                          value={edu.field}
                          onChange={e => handleItemChange('education', edu.id, 'field', e.target.value)}
                          className={inputClass}
                          readOnly={!edu.isEditing || isPreviewMode}
                        />
                      </div>
                      <div>
                        <label className={labelClass}>Dates</label>
                        <div className="flex items-center space-x-2">
                          <input
                            type="date"
                            value={formatDate(edu.startDate)}
                            onChange={e => handleItemChange('education', edu.id, 'startDate', new Date(e.target.value))}
                            className={inputClass}
                            readOnly={!edu.isEditing || isPreviewMode}
                          />
                          <span className={subtitleClass}>to</span>
                          <input
                            type="date"
                            value={formatDate(edu.endDate)}
                            onChange={e => handleItemChange('education', edu.id, 'endDate', e.target.value ? new Date(e.target.value) : null)}
                            className={inputClass}
                            readOnly={!edu.isEditing || isPreviewMode}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  {!isPreviewMode && (
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={() => toggleEdit('education', edu.id)}
                        className={buttonSecondaryClass}
                      >
                        {edu.isEditing ? (
                          <CheckIcon className="h-4 w-4" />
                        ) : (
                          <PencilIcon className="h-4 w-4" />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteItem('education', edu.id)}
                        className={deleteButtonClass}
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </Transition>
          ))}
        </div>
      </div>

      {/* Social Links */}
      <div className={sectionClass}>
        <h3 className={sectionHeaderClass}>Professional Links</h3>
        <div className="space-y-4">
          <div>
            <label htmlFor="linkedInUrl" className={labelClass}>
              LinkedIn Profile URL (Optional)
            </label>
            <input
              type="url"
              id="linkedInUrl"
              name="linkedInUrl"
              value={`${formData.linkedInUrl}`}
              onChange={handleChange}
              placeholder="https://www.linkedin.com/in/johndoe-12345678"
              className={`${inputClass} ${
                getFieldError('linkedInUrl', null, 'url') ? 'border-red-300' : 'border-slate-600'
              }`}
              readOnly={isPreviewMode}
            />
          </div>

          <div>
            <label htmlFor="githubUrl" className={labelClass}>
              GitHub Profile URL
            </label>
            <input
              type="url"
              id="githubUrl"
              name="githubUrl"
              value={`${formData.githubUrl}`}
              onChange={handleChange}
              placeholder="https://github.com/johndoe"
              className={`${inputClass} ${
                getFieldError('githubUrl', null, 'url') ? 'border-red-300' : 'border-slate-600'
              }`}
              readOnly={isPreviewMode}
            />
          </div>

          <div>
            <label htmlFor="portfolioUrl" className={labelClass}>
              Portfolio Website URL (Optional)
            </label>
            <input
              type="url"
              id="portfolioUrl"
              name="portfolioUrl"
              value={formData.portfolioUrl}
              onChange={handleChange}
              placeholder="https://yourportfolio.com"
              className={`${inputClass} ${
                getFieldError('portfolioUrl', null, 'url') ? 'border-red-300' : 'border-slate-600'
              }`}
              readOnly={isPreviewMode}
            />
          </div>
        </div>
      </div>

      {/* Import from Social Media Button */}
      <div className="mt-4">
        <button
          type="button"
          onClick={handleImportFromSocialMedia}
          disabled={isImporting || !formData.githubUrl}
          className={`${buttonPrimaryClass} px-4 py-2 ${
            isImporting || !formData.githubUrl 
              ? 'opacity-50 cursor-not-allowed' 
              : ''
          }`}
        >
          {isImporting ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Importing...
            </>
          ) : (
            <>
              <CloudArrowDownIcon className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
              Import from GitHub
            </>
          )}
        </button>
        
        {importError && (
          <p className="mt-2 text-sm text-red-300">
            <ExclamationCircleIcon className="h-5 w-5 text-red-400 inline mr-1" />
            {importError}
          </p>
        )}
        
        <div className="mt-2 text-xs text-slate-300 space-y-1">
          <p>
            Add your GitHub URL above and click this button to automatically import your repositories, 
            skills, and other information.
          </p>
          <p className="text-slate-400 italic">
            Note: LinkedIn integration is currently disabled. Please manually add your professional experience, 
            education, and other information using the forms below.
          </p>
        </div>
      </div>

      {/* Projects Section */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h3 className={sectionHeaderClass.replace(" mb-4", "")}>Projects</h3>
          <button
            type="button"
            onClick={() => addNewEntry('project')}
            className={buttonPrimaryClass}
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Project
          </button>
        </div>
        
        {formData.projects.map((project) => (
          <div key={project.id} className={`${cardClass} mb-4`}>
            {project.isEditing ? (
              <div className="space-y-4">
                <div>
                  <label htmlFor={`project-${project.id}-title`} className={labelClass}>
                    Title
                  </label>
                  <input
                    type="text"
                    id={`project-${project.id}-title`}
                    value={project.title}
                    onChange={(e) => handleItemChange('projects', project.id, 'title', e.target.value)}
                    className={`${inputClass} ${
                      getFieldError('projects', project.id, 'title') ? 'border-red-300' : 'border-gray-300'
                    }`}
                  />
                  {getFieldError('projects', project.id, 'title') && (
                    <p className="mt-1 text-sm text-red-300">{getFieldError('projects', project.id, 'title')}</p>
                  )}
                </div>
                
                <div>
                  <label htmlFor={`project-${project.id}-description`} className={labelClass}>
                    Description
                  </label>
                  <textarea
                    id={`project-${project.id}-description`}
                    value={project.description || ''}
                    onChange={(e) => handleItemChange('projects', project.id, 'description', e.target.value)}
                    rows={3}
                    className={`${inputClass} ${
                      getFieldError('projects', project.id, 'description') ? 'border-red-300' : 'border-gray-300'
                    }`}
                  />
                </div>
                
                <div>
                  <label htmlFor={`project-${project.id}-url`} className={labelClass}>
                    URL
                  </label>
                  <input
                    type="url"
                    id={`project-${project.id}-url`}
                    value={project.url || ''}
                    onChange={(e) => handleItemChange('projects', project.id, 'url', e.target.value)}
                    className={`${inputClass} ${
                      getFieldError('projects', project.id, 'url') ? 'border-red-300' : 'border-gray-300'
                    }`}
                  />
                </div>
                
                <div className="flex justify-end space-x-2">
                  <button
                    type="button"
                    onClick={() => toggleEdit('projects', project.id)}
                    className={buttonSecondaryClass}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleEdit('projects', project.id)}
                    className={buttonPrimaryClass}
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteItem('projects', project.id)}
                    className={deleteButtonClass}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <div className="flex justify-between">
                  <div>
                    <h4 className={titleClass}>{project.title}</h4>
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
                {project.description && (
                  <p className="mt-2 text-sm text-slate-300">{project.description}</p>
                )}
                {project.url && (
                  <a
                    href={project.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={linkClass}
                  >
                    View Project
                    <ArrowTopRightOnSquareIcon className="ml-1 h-4 w-4" />
                  </a>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Publications Section */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h3 className={sectionHeaderClass.replace(" mb-4", "")}>Publications</h3>
          <button
            type="button"
            onClick={() => addNewEntry('publication')}
            className={buttonPrimaryClass}
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Publication
          </button>
        </div>
        
        {formData.publications.map((publication) => (
          <div key={publication.id} className={`${cardClass} mb-4`}>
            {publication.isEditing ? (
              <div className="space-y-4">
                <div>
                  <label htmlFor={`publication-${publication.id}-title`} className={labelClass}>
                    Title
                  </label>
                  <input
                    type="text"
                    id={`publication-${publication.id}-title`}
                    value={publication.title}
                    onChange={(e) => handleItemChange('publications', publication.id, 'title', e.target.value)}
                    className={inputClass}
                  />
                </div>
                
                <div>
                  <label htmlFor={`publication-${publication.id}-publisher`} className={labelClass}>
                    Publisher
                  </label>
                  <input
                    type="text"
                    id={`publication-${publication.id}-publisher`}
                    value={publication.publisher}
                    onChange={(e) => handleItemChange('publications', publication.id, 'publisher', e.target.value)}
                    className={inputClass}
                  />
                </div>
                
                <div>
                  <label htmlFor={`publication-${publication.id}-date`} className={labelClass}>
                    Publication Date
                  </label>
                  <input
                    type="date"
                    id={`publication-${publication.id}-date`}
                    value={formatDate(publication.date)}
                    onChange={(e) => handleItemChange('publications', publication.id, 'date', new Date(e.target.value))}
                    className={inputClass}
                  />
                </div>

                <div>
                  <label htmlFor={`publication-${publication.id}-description`} className={labelClass}>
                    Description
                  </label>
                  <textarea
                    id={`publication-${publication.id}-description`}
                    value={publication.description || ''}
                    onChange={(e) => handleItemChange('publications', publication.id, 'description', e.target.value)}
                    rows={3}
                    className={inputClass}
                  />
                </div>
                
                <div className="flex justify-end space-x-2">
                  <button
                    type="button"
                    onClick={() => toggleEdit('publications', publication.id)}
                    className={buttonSecondaryClass}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleEdit('publications', publication.id)}
                    className={buttonPrimaryClass}
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteItem('publications', publication.id)}
                    className={deleteButtonClass}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <div className="flex justify-between">
                  <div>
                    <h4 className={titleClass}>{publication.title}</h4>
                    <p className={subtitleClass}>{publication.publisher}</p>
                    {publication.date && (
                      <p className="text-sm text-slate-400">{format(publication.date, 'MMMM yyyy')}</p>
                    )}
                  </div>
                  <div className="flex space-x-2">
                    <button
                      type="button"
                      onClick={() => toggleEdit('publications', publication.id)}
                      className={buttonSecondaryClass}
                    >
                      <PencilIcon className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteItem('publications', publication.id)}
                      className={deleteButtonClass}
                    >
                      <XMarkIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                {publication.description && (
                  <p className="mt-2 text-sm text-slate-300">{publication.description}</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Certifications Section */}
      <div className={sectionClass}>
        <div className="flex justify-between items-center mb-4">
          <h3 className={sectionHeaderClass.replace(" mb-4", "")}>Certifications</h3>
          <button
            type="button"
            onClick={() => addNewEntry('certification')}
            className={buttonPrimaryClass}
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            Add Certification
          </button>
        </div>
        
        {formData.certifications.map((certification) => (
          <div key={certification.id} className={`${cardClass} mb-4`}>
            {certification.isEditing ? (
              <div className="space-y-4">
                <div>
                  <label htmlFor={`certification-${certification.id}-name`} className={labelClass}>
                    Name
                  </label>
                  <input
                    type="text"
                    id={`certification-${certification.id}-name`}
                    value={certification.name}
                    onChange={(e) => handleItemChange('certifications', certification.id, 'name', e.target.value)}
                    className={inputClass}
                  />
                </div>
                
                <div>
                  <label htmlFor={`certification-${certification.id}-issuer`} className={labelClass}>
                    Issuer
                  </label>
                  <input
                    type="text"
                    id={`certification-${certification.id}-issuer`}
                    value={certification.issuer}
                    onChange={(e) => handleItemChange('certifications', certification.id, 'issuer', e.target.value)}
                    className={inputClass}
                  />
                </div>
                
                <div>
                  <label htmlFor={`certification-${certification.id}-date`} className={labelClass}>
                    Date Earned
                  </label>
                  <input
                    type="date"
                    id={`certification-${certification.id}-date`}
                    value={formatDate(certification.date)}
                    onChange={(e) => handleItemChange('certifications', certification.id, 'date', new Date(e.target.value))}
                    className={inputClass}
                  />
                </div>

                <div>
                  <label htmlFor={`certification-${certification.id}-url`} className={labelClass}>
                    URL
                  </label>
                  <input
                    type="url"
                    id={`certification-${certification.id}-url`}
                    value={certification.url || ''}
                    onChange={(e) => handleItemChange('certifications', certification.id, 'url', e.target.value)}
                    className={inputClass}
                  />
                </div>
                
                <div className="flex justify-end space-x-2">
                  <button
                    type="button"
                    onClick={() => toggleEdit('certifications', certification.id)}
                    className={buttonSecondaryClass}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleEdit('certifications', certification.id)}
                    className={buttonPrimaryClass}
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteItem('certifications', certification.id)}
                    className={deleteButtonClass}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <div className="flex justify-between">
                  <div>
                    <h4 className={titleClass}>{certification.name}</h4>
                    <p className={subtitleClass}>{certification.issuer}</p>
                    {certification.date && (
                      <p className="text-sm text-slate-400">{format(certification.date, 'MMMM yyyy')}</p>
                    )}
                  </div>
                  <div className="flex space-x-2">
                    <button
                      type="button"
                      onClick={() => toggleEdit('certifications', certification.id)}
                      className={buttonSecondaryClass}
                    >
                      <PencilIcon className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteItem('certifications', certification.id)}
                      className={deleteButtonClass}
                    >
                      <XMarkIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                {certification.url && (
                  <a
                    href={certification.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={linkClass}
                  >
                    View Certificate
                    <ArrowTopRightOnSquareIcon className="ml-1 h-4 w-4" />
                  </a>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Additional Dynamic Sections */}
      {formData.additionalSections.map((section) => (
        <div key={section.id} className={sectionClass}>
          <div className="flex justify-between items-center mb-4">
            <h3 className={sectionHeaderClass.replace(" mb-4", "")}>{section.title}</h3>
            <div className="flex space-x-2">
              <button
                type="button"
                onClick={() => addDynamicSectionItem(section.id)}
                className={buttonPrimaryClass}
              >
                <PlusIcon className="h-4 w-4 mr-1" />
                Add Item
              </button>
              <button
                type="button"
                onClick={() => handleDeleteItem('additionalSections', section.id)}
                className={deleteButtonClass}
              >
                <XMarkIcon className="h-4 w-4 mr-1" />
                Delete Section
              </button>
            </div>
          </div>
          
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
                    <div className="bg-slate-800 shadow rounded-lg p-4 border border-slate-700">
                      {item.isEditing ? (
                        <div className="space-y-4">
                          <div>
                            <label className={labelClass}>
                              Title
                            </label>
                            <input
                              type="text"
                              value={item.title || ''}
                              onChange={(e) => handleDynamicItemChange(section.id, item.id, 'title', e.target.value)}
                              className={`${inputClass} ${
                                getFieldError('additionalSections', `${section.id}-${item.id}-title`, 'title') ? 'border-red-300' : 'border-slate-600'
                              }`}
                            />
                          </div>
                          
                          <div>
                            <label className={labelClass}>
                              Description
                            </label>
                            <textarea
                              value={item.description || ''}
                              onChange={(e) => handleDynamicItemChange(section.id, item.id, 'description', e.target.value)}
                              rows={3}
                              className={`${inputClass} ${
                                getFieldError('additionalSections', `${section.id}-${item.id}-description`, 'description') ? 'border-red-300' : 'border-slate-600'
                              }`}
                            />
                          </div>
                          
                          <div>
                            <label className={labelClass}>
                              URL
                            </label>
                            <input
                              type="url"
                              value={item.url || ''}
                              onChange={(e) => handleDynamicItemChange(section.id, item.id, 'url', e.target.value)}
                              className={`${inputClass} ${
                                getFieldError('additionalSections', `${section.id}-${item.id}-url`, 'url') ? 'border-red-300' : 'border-slate-600'
                              }`}
                            />
                          </div>
                          
                          <div className="flex justify-end space-x-2">
                            <button
                              type="button"
                              onClick={() => toggleDynamicItemEdit(section.id, item.id)}
                              className={buttonSecondaryClass}
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              onClick={() => toggleDynamicItemEdit(section.id, item.id)}
                              className={buttonPrimaryClass}
                            >
                              Save
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteDynamicItem(section.id, item.id)}
                              className={deleteButtonClass}
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <div className="flex justify-between">
                            <div>
                              <h4 className={titleClass}>{item.title}</h4>
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
                          {item.description && (
                            <p className="mt-2 text-sm text-slate-300">{item.description}</p>
                          )}
                          {item.url && (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={linkClass}
                            >
                              View Link
                              <ArrowTopRightOnSquareIcon className="ml-1 h-4 w-4" />
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                  </SortableItem>
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </div>
      ))}

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

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isSubmitting}
          className={`${buttonPrimaryClass} px-4 py-2 ${
            isSubmitting ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {isSubmitting ? 'Saving...' : 'Save'}
        </button>
      </div>
    </form>
  );
};

export default ProfileForm;