'use client';

import { useEffect, useState } from 'react';

interface DateFormatterProps {
  date: string | Date;
  className?: string;
}

export default function DateFormatter({ date, className }: DateFormatterProps) {
  const [formattedDate, setFormattedDate] = useState<string>('');

  useEffect(() => {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    setFormattedDate(dateObj.toLocaleDateString());
  }, [date]);

  return <span className={className}>{formattedDate}</span>;
} 