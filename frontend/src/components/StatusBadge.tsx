/**
 * Reusable StatusBadge component for Snack stock levels.
 * Styling explicitly adheres to architecture rules:
 * - Stocked: Green
 * - Running Low: Amber
 * - Gone: Red
 */

import React from 'react';
import { SnackStatus } from '../api/types';

interface StatusBadgeProps {
  status: SnackStatus;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  showDot = true,
  className = '',
}) => {
  const getBadgeConfig = () => {
    switch (status) {
      case 'stocked':
        return {
          label: 'Stocked',
          bg: 'bg-emerald-50 text-emerald-800 border-emerald-200',
          dot: 'bg-emerald-500',
        };
      case 'running_low':
        return {
          label: 'Running Low',
          bg: 'bg-amber-50 text-amber-800 border-amber-200',
          dot: 'bg-amber-500',
        };
      case 'gone':
        return {
          label: 'Gone',
          bg: 'bg-rose-50 text-rose-800 border-rose-200',
          dot: 'bg-rose-500',
        };
      default:
        return {
          label: status,
          bg: 'bg-slate-50 text-slate-700 border-slate-200',
          dot: 'bg-slate-400',
        };
    }
  };

  const config = getBadgeConfig();

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1.5',
    md: 'text-xs sm:text-sm px-2.5 py-1 gap-2',
    lg: 'text-sm sm:text-base px-3 py-1.5 gap-2.5',
  }[size];

  const dotSize = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5',
  }[size];

  return (
    <span
      className={`inline-flex items-center font-semibold rounded-full border tracking-wide uppercase ${sizeClasses} ${config.bg} ${className}`}
    >
      {showDot && (
        <span
          className={`rounded-full shrink-0 ${dotSize} ${config.dot}`}
          aria-hidden="true"
        />
      )}
      <span>{config.label}</span>
    </span>
  );
};
