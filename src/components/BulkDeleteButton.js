import React from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

const BulkDeleteButton = ({
  onClick,
  label = 'Clear All',
  className = '',
  disabled = false,
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
    >
      <XMarkIcon className="h-4 w-4 mr-1" />
      {label}
    </button>
  );
};

export default BulkDeleteButton; 