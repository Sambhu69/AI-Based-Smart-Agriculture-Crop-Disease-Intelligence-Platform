import React from 'react';
import { Activity, AlertTriangle, Loader2 } from 'lucide-react';
import type { SystemHealthResponse } from '../../types/api';

interface ConnectionBadgeProps {
  health?: SystemHealthResponse;
  isLoading: boolean;
  isError: boolean;
  compact?: boolean;
}

export const ConnectionBadge: React.FC<ConnectionBadgeProps> = ({
  health,
  isLoading,
  isError,
  compact = false,
}) => {
  if (isLoading) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium surface-subtle"
        style={{ color: 'var(--text-secondary)' }}
      >
        <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-600" />
        <span>{compact ? 'Checking' : 'Checking API…'}</span>
      </div>
    );
  }

  if (isError || !health || health.status !== 'healthy') {
    return (
      <div
        role="status"
        aria-live="polite"
        title="FastAPI backend is offline or unreachable. Start with: uvicorn app.main:app --port 8000"
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/15 text-red-700 dark:text-red-300 border border-red-500/30"
      >
        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
        <span>{compact ? 'Offline' : 'API Offline'}</span>
      </div>
    );
  }

  return (
    <div
      role="status"
      aria-live="polite"
      title={`Connected to FastAPI v1 | Model: ${health.model_architecture} v${health.model_version} (${health.inference_device.toUpperCase()})`}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border border-emerald-500/30"
    >
      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
      <span>{compact ? 'Online' : 'API Connected'}</span>
      {!compact && (
        <span className="hidden sm:inline-flex items-center gap-1 pl-1 border-l border-emerald-500/30 text-[11px] opacity-85 uppercase">
          <Activity className="w-3 h-3" />
          {health.inference_device}
        </span>
      )}
    </div>
  );
};
