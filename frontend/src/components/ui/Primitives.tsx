import React, { useEffect } from 'react';
import { AlertCircle, Inbox, Loader2, X } from 'lucide-react';

/* --- Card --- */
interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  padding = 'md',
}) => {
  const padMap = {
    none: '',
    sm: 'p-3.5 sm:p-4',
    md: 'p-4 sm:p-5',
    lg: 'p-5 sm:p-6',
  };
  return (
    <div className={`surface-card ${padMap[padding]} ${className}`}>
      {children}
    </div>
  );
};

/* --- Button --- */
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  disabled,
  className = '',
  ...rest
}) => {
  const sizeClasses = {
    sm: 'min-h-[38px] px-3 py-1.5 text-xs',
    md: 'min-h-[44px] px-4 py-2 text-sm',
    lg: 'min-h-[48px] px-5 py-2.5 text-base',
  };

  const getVariantStyle = (): React.CSSProperties => {
    if (variant === 'primary') {
      return {
        backgroundColor: 'var(--brand-primary)',
        color: '#ffffff',
      };
    }
    if (variant === 'secondary') {
      return {
        backgroundColor: 'var(--bg-subtle)',
        color: 'var(--text-primary)',
        border: '1px solid var(--border-default)',
      };
    }
    if (variant === 'outline') {
      return {
        backgroundColor: 'transparent',
        color: 'var(--text-primary)',
        border: '1px solid var(--border-strong)',
      };
    }
    if (variant === 'danger') {
      return {
        backgroundColor: '#dc2626',
        color: '#ffffff',
      };
    }
    return {
      backgroundColor: 'transparent',
      color: 'var(--text-secondary)',
    };
  };

  return (
    <button
      style={getVariantStyle()}
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center gap-2 font-semibold rounded-xl transition-opacity focus:outline-none focus:ring-2 focus:ring-emerald-600/50 disabled:opacity-50 disabled:cursor-not-allowed ${sizeClasses[size]} ${className}`}
      {...rest}
    >
      {isLoading ? <Loader2 className="w-4 h-4 animate-spin shrink-0" /> : leftIcon}
      <span>{children}</span>
    </button>
  );
};

/* --- ModalOrSheet (Bottom Sheet on mobile <640px, Centered Dialog on >=640px) --- */
interface ModalOrSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export const ModalOrSheet: React.FC<ModalOrSheetProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
}) => {
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-sheet-title"
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-xs p-0 sm:p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border-default)',
          boxShadow: 'var(--shadow-modal)',
        }}
        className="w-full sm:max-w-lg max-h-[90vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl border p-5 sm:p-6"
      >
        <div className="flex items-start justify-between gap-3 pb-3 mb-4 border-b" style={{ borderColor: 'var(--border-default)' }}>
          <div>
            <h2 id="modal-sheet-title" className="text-lg font-bold font-display">
              {title}
            </h2>
            {subtitle && (
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                {subtitle}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="touch-target inline-flex items-center justify-center rounded-lg hover:opacity-80"
            style={{ color: 'var(--text-secondary)' }}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
};

/* --- EmptyState --- */
interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  action,
}) => (
  <div className="surface-card p-6 sm:p-10 text-center flex flex-col items-center justify-center">
    <div
      className="w-12 h-12 rounded-2xl flex items-center justify-center mb-3"
      style={{ backgroundColor: 'var(--brand-soft)', color: 'var(--brand-primary)' }}
    >
      {icon || <Inbox className="w-6 h-6" />}
    </div>
    <h3 className="text-base sm:text-lg font-bold font-display mb-1">{title}</h3>
    <p
      className="text-xs sm:text-sm max-w-md mb-4 leading-relaxed"
      style={{ color: 'var(--text-secondary)' }}
    >
      {description}
    </p>
    {action && <div>{action}</div>}
  </div>
);

/* --- ErrorAlert --- */
interface ErrorAlertProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({
  title = 'Unable to complete request',
  message,
  onRetry,
}) => (
  <div
    role="alert"
    className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-900 dark:text-red-200 flex items-start gap-3"
  >
    <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
    <div className="flex-1 min-w-0">
      <h4 className="text-sm font-bold">{title}</h4>
      <p className="text-xs mt-1 break-words opacity-90">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2.5 inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600 text-white hover:bg-red-700"
        >
          Retry Request
        </button>
      )}
    </div>
  </div>
);

/* --- Skeleton --- */
export const Skeleton: React.FC<{ className?: string }> = ({ className = 'h-24 w-full' }) => (
  <div
    aria-hidden="true"
    style={{ backgroundColor: 'var(--bg-subtle)' }}
    className={`animate-pulse rounded-xl ${className}`}
  />
);
