import React, { useState } from 'react';
import {
  CheckCircle2,
  Database,
  Info,
  Moon,
  RefreshCw,
  Server,
  ShieldCheck,
  Sun,
} from 'lucide-react';
import { useAppContext } from '../context/AppContext';
import { useSystemHealth } from '../hooks/useAgriQueries';
import { ProvenanceBadge } from '../components/ui/ProvenanceBadge';
import { Button, Card } from '../components/ui/Primitives';

export const SettingsPage: React.FC = () => {
  const { theme, setTheme, apiBaseUrl, updateApiBaseUrl, selectedFarmId, setSelectedFarmId } =
    useAppContext();
  const { data: health, isLoading, isError, refetch } = useSystemHealth();

  const [urlInput, setUrlInput] = useState(apiBaseUrl);
  const [savedNotice, setSavedNotice] = useState(false);

  const handleSaveUrl = (e: React.FormEvent) => {
    e.preventDefault();
    updateApiBaseUrl(urlInput);
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 3000);
    refetch();
  };

  const handleResetUrl = () => {
    const def = 'http://127.0.0.1:8000';
    setUrlInput(def);
    updateApiBaseUrl(def);
    refetch();
  };

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Header */}
      <Card padding="md">
        <h2 className="text-lg sm:text-xl font-extrabold font-display">
          Platform Settings, Appearance & API Diagnostics
        </h2>
        <p className="text-xs sm:text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>
          Configure visual theme preferences, test FastAPI backend connectivity, and review the
          canonical epistemic provenance taxonomy.
        </p>
      </Card>

      {/* 1. Theme & Appearance */}
      <Card padding="md" className="space-y-4">
        <div>
          <h3 className="text-base font-bold font-display">1. Theme & Visual Appearance</h3>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Stored locally in your browser via <code>localStorage</code> (<code>agri_theme_mode</code>
            ).
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setTheme('light')}
            style={
              theme === 'light'
                ? {
                    backgroundColor: 'var(--brand-soft)',
                    borderColor: 'var(--brand-primary)',
                  }
                : {
                    backgroundColor: 'var(--bg-subtle)',
                    borderColor: 'var(--border-default)',
                  }
            }
            className="p-4 rounded-2xl border text-left flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <Sun className="w-5 h-5 text-amber-500" />
              <div>
                <div className="text-sm font-bold">Botanical Daylight (Light)</div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  High-contrast outdoor & field readability
                </div>
              </div>
            </div>
            {theme === 'light' && <CheckCircle2 className="w-5 h-5 text-emerald-600" />}
          </button>

          <button
            type="button"
            onClick={() => setTheme('dark')}
            style={
              theme === 'dark'
                ? {
                    backgroundColor: 'var(--brand-soft)',
                    borderColor: 'var(--brand-primary)',
                  }
                : {
                    backgroundColor: 'var(--bg-subtle)',
                    borderColor: 'var(--border-default)',
                  }
            }
            className="p-4 rounded-2xl border text-left flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <Moon className="w-5 h-5 text-emerald-400" />
              <div>
                <div className="text-sm font-bold">Forest Obsidian (Dark)</div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  Low-glare analytical workstation theme
                </div>
              </div>
            </div>
            {theme === 'dark' && <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
          </button>
        </div>
      </Card>

      {/* 2. FastAPI Connection & Telemetry */}
      <Card padding="md" className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold font-display flex items-center gap-2">
              <Server className="w-4 h-4 text-emerald-600" />
              <span>2. FastAPI Backend Endpoint Configuration</span>
            </h3>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              Default: <code>VITE_API_BASE_URL=http://127.0.0.1:8000</code>. No secret credentials
              are stored in the browser.
            </p>
          </div>
        </div>

        <form onSubmit={handleSaveUrl} className="flex flex-col sm:flex-row gap-2.5">
          <label htmlFor="api-base-url-input" className="sr-only">
            FastAPI Base URL
          </label>
          <input
            id="api-base-url-input"
            type="url"
            required
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            className="input-field flex-1 font-mono text-xs"
          />
          <div className="flex gap-2">
            <Button type="submit" variant="primary" size="md">
              Save & Test
            </Button>
            <Button type="button" variant="outline" size="md" onClick={handleResetUrl}>
              Reset Default
            </Button>
          </div>
        </form>

        {savedNotice && (
          <p className="text-xs font-semibold text-emerald-600">
            API Base URL updated in browser localStorage and health check re-triggered.
          </p>
        )}

        {/* Live Health Response Box */}
        <div className="p-4 rounded-xl surface-subtle text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-bold uppercase tracking-wider">
              Live <code>GET /api/v1/health</code> Status
            </span>
            <button
              type="button"
              onClick={() => refetch()}
              className="inline-flex items-center gap-1 font-semibold hover:underline"
              style={{ color: 'var(--brand-primary)' }}
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Ping Now
            </button>
          </div>

          {isLoading ? (
            <p>Checking connection…</p>
          ) : isError || !health ? (
            <p className="text-red-600 dark:text-red-400 font-semibold">
              Disconnected from {apiBaseUrl}. Start backend with:{' '}
              <code>.\venv\Scripts\python.exe -m uvicorn app.main:app --port 8000</code>
            </p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
              <div>
                Status: <strong className="uppercase text-emerald-600">{health.status}</strong>
              </div>
              <div>
                API Version: <strong>{health.api_version}</strong>
              </div>
              <div>
                Model Loaded: <strong>{health.model_loaded ? 'Yes' : 'No'}</strong>
              </div>
              <div>
                Architecture: <strong>{health.model_architecture}</strong>
              </div>
              <div>
                Model Version: <strong>v{health.model_version}</strong>
              </div>
              <div>
                Compute Device: <strong className="uppercase">{health.inference_device}</strong>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* 3. Canonical Epistemic Provenance Legend */}
      <Card padding="md" className="space-y-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-600" />
          <h3 className="text-base font-bold font-display">
            3. Canonical Data Provenance Taxonomy
          </h3>
        </div>
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Every metric, record, and recommendation in this platform is tagged with one of five
          epistemic provenance categories to prevent conflating ground truth with model estimates:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div className="p-3 rounded-xl surface-subtle space-y-1">
            <ProvenanceBadge type="observed" />
            <p style={{ color: 'var(--text-secondary)' }}>
              Direct physical field measurements, scout inspections, or in-situ sensor readouts.
            </p>
          </div>
          <div className="p-3 rounded-xl surface-subtle space-y-1">
            <ProvenanceBadge type="external" />
            <p style={{ color: 'var(--text-secondary)' }}>
              Records ingested from external agroclimatology providers (e.g., NASA POWER).
            </p>
          </div>
          <div className="p-3 rounded-xl surface-subtle space-y-1">
            <ProvenanceBadge type="predicted" />
            <p style={{ color: 'var(--text-secondary)' }}>
              Outputs generated by trained ML/DL models (ResNet-50 disease CV, Ridge yield model).
            </p>
          </div>
          <div className="p-3 rounded-xl surface-subtle space-y-1">
            <ProvenanceBadge type="simulated" />
            <p style={{ color: 'var(--text-secondary)' }}>
              Projections from mathematical scenario simulators (Digital Twin, RL water balance).
            </p>
          </div>
          <div className="p-3 rounded-xl surface-subtle space-y-1 sm:col-span-2">
            <ProvenanceBadge type="recommended" />
            <p style={{ color: 'var(--text-secondary)' }}>
              Prescriptive guidance from the agronomic suitability, irrigation, and treatment rule
              engine.
            </p>
          </div>
        </div>
      </Card>

      {/* 4. Persistence & Privacy Disclosure */}
      <Card padding="md" className="space-y-2 text-xs">
        <div className="font-bold flex items-center gap-1.5">
          <Database className="w-4 h-4 text-emerald-600" />
          <span>4. Storage & Session Transparency</span>
        </div>
        <p style={{ color: 'var(--text-secondary)' }}>
          • <strong>Database-Persisted Entities:</strong> Farms, plots, field observations,
          prediction records, and plot-linked digital twin scenarios are persisted in the FastAPI
          relational database (SQLite default / PostgreSQL via <code>DATABASE_URL</code>).
        </p>
        <p style={{ color: 'var(--text-secondary)' }}>
          • <strong>Browser Local Preferences:</strong> Visual theme (<code>{theme}</code>), active
          farm selection (<code>{selectedFarmId ?? 'All'}</code>), and API URL override are saved in
          browser <code>localStorage</code>.
        </p>
        {selectedFarmId && (
          <div className="pt-1">
            <Button size="sm" variant="outline" onClick={() => setSelectedFarmId(null)}>
              Clear Active Farm Filter
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
};
