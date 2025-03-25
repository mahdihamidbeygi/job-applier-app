'use client';

import { useEffect, useState } from 'react';

export default function DateFormatter({ date, className }) {
  const [formattedDate, setFormattedDate] = useState('');

  useEffect(() => {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    setFormattedDate(dateObj.toLocaleDateString());
  }, [date]);

  return <span className={className}>{formattedDate}</span>;
} 