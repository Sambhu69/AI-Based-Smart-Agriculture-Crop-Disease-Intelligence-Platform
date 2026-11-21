import React, { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  BarChart3,
  ClipboardList,
  Compass,
  Leaf,
  Plus,
  Sliders,
  Sprout,
} from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  useCreateObservationMutation,
  useFarmDetail,
  usePlotObservations,
} from '../hooks/useAgriQueries';
import { ProvenanceBadge } from '../components/ui/ProvenanceBadge';
import {
  Button,
  Card,
  EmptyState,
  ErrorAlert,
  ModalOrSheet,
  Skeleton,
} from '../components/ui/Primitives';

export const PlotDetailPage: React.FC = () => {
  const { farmId, plotId } = useParams<{ farmId: string; plotId: string }>();
  const navigate = useNavigate();

  const numericFarmId = Number(farmId);
  const numericPlotId = Number(plotId);

  const { data: farmDetail, isLoading: farmLoading, isError: farmError } =
    useFarmDetail(numericFarmId);
  const {
    data: observations,
    isLoading: obsLoading,
    isError: obsError,
    error: obsErrObj,
    refetch: refetchObs,
  } = usePlotObservations(numericFarmId, numericPlotId);

  const createObsMutation = useCreateObservationMutation(numericFarmId, numericPlotId);

  const plot = useMemo(
    () => farmDetail?.plots?.find((p) => p.id === numericPlotId) || null,
    [farmDetail, numericPlotId]
  );

  // Filter state for observations
  const [provFilter, setProvFilter] = useState<'all' | 'observed' | 'external'>('all');

  // New Observation Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [epistemicType, setEpistemicType] = useState<'observed' | 'external'>('observed');
  const [source, setSource] = useState('field_scout');
  const [tempC, setTempC] = useState('23.5');
  const [moisturePct, setMoisturePct] = useState('64.0');
  const [soilPh, setSoilPh] = useState('6.4');
  const [rainfallMm, setRainfallMm] = useState('0.0');
  const [notes, setNotes] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const filteredObservations = useMemo(() => {
    if (!observations) return [];
    if (provFilter === 'all') return observations;
    return observations.filter((o) => o.epistemic_type === provFilter);
  }, [observations, provFilter]);

  const trendSeries = useMemo(() => {
    if (!observations) return [];
    return observations
      .filter(
        (o) =>
          typeof o.data?.temperature_c === 'number' ||
          typeof o.data?.soil_moisture_pct === 'number'
      )
      .map((o, idx) => ({
        idx: `#${idx + 1}`,
        time: new Date(o.observed_at).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
        epistemic_type: o.epistemic_type,
        temperature_c:
          typeof o.data?.temperature_c === 'number' ? Number(o.data.temperature_c) : null,
        soil_moisture_pct:
          typeof o.data?.soil_moisture_pct === 'number'
            ? Number(o.data.soil_moisture_pct)
            : null,
      }));
  }, [observations]);

  const handleCreateObservation = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!source.trim()) {
      setFormError('Observation source is required.');
      return;
    }

    const dataPayload: Record<string, unknown> = {};
    if (tempC.trim() !== '') dataPayload.temperature_c = Number(tempC);
    if (moisturePct.trim() !== '') dataPayload.soil_moisture_pct = Number(moisturePct);
    if (soilPh.trim() !== '') dataPayload.soil_ph = Number(soilPh);
    if (rainfallMm.trim() !== '') dataPayload.rainfall_mm = Number(rainfallMm);

    try {
      await createObsMutation.mutateAsync({
        source: source.trim(),
        epistemic_type: epistemicType,
        data: dataPayload,
        notes: notes.trim() || null,
      });
      setNotes('');
      setModalOpen(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to record observation');
    }
  };

  if (farmLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (farmError || !farmDetail || !plot) {
    return (
      <EmptyState
        title="Plot Not Found in This Farm"
        description={`Could not locate Plot #${plotId} under Farm #${farmId}. Verify the farm and plot exist.`}
        action={
          <Button onClick={() => navigate('/farms')} leftIcon={<ArrowLeft className="w-4 h-4" />}>
            Back to Farms Directory
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-5">
      {/* Breadcrumb & Header */}
      <Card padding="md">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs mb-1.5">
              <Link
                to="/farms"
                className="font-semibold hover:underline inline-flex items-center gap-1"
                style={{ color: 'var(--brand-primary)' }}
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                {farmDetail.name}
              </Link>
              <span style={{ color: 'var(--text-muted)' }}>/</span>
              <span style={{ color: 'var(--text-secondary)' }}>Plot #{plot.id}</span>
            </nav>

            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className="text-xl font-extrabold font-display flex items-center gap-2">
                <Sprout className="w-5 h-5 text-emerald-600" />
                {plot.name}
              </h2>
              <span
                className="px-2.5 py-0.5 rounded-full text-xs font-bold"
                style={{ backgroundColor: 'var(--brand-soft)', color: 'var(--brand-text)' }}
              >
                Crop: {plot.crop_type}
              </span>
              <ProvenanceBadge type="observed" />
            </div>

            <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
              Area:{' '}
              <strong>
                {plot.area_hectares !== null ? `${plot.area_hectares} hectares` : 'Unspecified'}
              </strong>{' '}
              • Farm Location: {farmDetail.location || 'Unspecified'} • Created{' '}
              {new Date(plot.created_at).toLocaleDateString()}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={() => setModalOpen(true)}
            >
              Record Observation
            </Button>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Leaf className="w-4 h-4" />}
              onClick={() => navigate(`/diagnosis?plotId=${plot.id}&crop=${plot.crop_type}`)}
            >
              Diagnose
            </Button>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<BarChart3 className="w-4 h-4" />}
              onClick={() =>
                navigate(
                  `/yield-prediction?plotId=${plot.id}&crop=${plot.crop_type}&area=${
                    plot.area_hectares || 1.5
                  }`
                )
              }
            >
              Forecast Yield
            </Button>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Compass className="w-4 h-4" />}
              onClick={() =>
                navigate(`/recommendations?plotId=${plot.id}&crop=${plot.crop_type}`)
              }
            >
              Advisory
            </Button>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Sliders className="w-4 h-4" />}
              onClick={() => navigate(`/digital-twin?plotId=${plot.id}&crop=${plot.crop_type}`)}
            >
              Simulate Twin
            </Button>
          </div>
        </div>
      </Card>

      {obsError && (
        <ErrorAlert
          message={obsErrObj instanceof Error ? obsErrObj.message : 'Error loading observations'}
          onRetry={() => refetchObs()}
        />
      )}

      {/* Observation Trend Chart (Only when numerical measurements exist) */}
      {trendSeries.length >= 2 && (
        <Card padding="md">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <div>
              <h3 className="text-sm sm:text-base font-bold font-display">
                Plot Microclimate & Soil Moisture Measurements
              </h3>
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Recorded across {trendSeries.length} field and external observation snapshots
              </p>
            </div>
            <div className="flex items-center gap-1.5">
              <ProvenanceBadge type="observed" />
              <ProvenanceBadge type="external" />
            </div>
          </div>
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendSeries} margin={{ top: 8, right: 12, left: -12, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                <XAxis dataKey="idx" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-surface)',
                    borderColor: 'var(--border-default)',
                    borderRadius: '0.75rem',
                    fontSize: '12px',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="temperature_c"
                  name="Temperature (°C)"
                  stroke="#d97706"
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="soil_moisture_pct"
                  name="Soil Moisture (%)"
                  stroke="#0284c7"
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Field Observations Log with Provenance Separation */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h3 className="text-base font-bold font-display">
              Field & External Observation Ledger ({filteredObservations.length})
            </h3>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              Strictly enforces physical ground truth (<code>observed</code>) vs. external provider
              data (<code>external</code>).
            </p>
          </div>

          {/* Provenance Filter Tabs */}
          <div className="inline-flex rounded-xl p-1 surface-subtle self-start">
            {(['all', 'observed', 'external'] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setProvFilter(tab)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-colors"
                style={
                  provFilter === tab
                    ? {
                        backgroundColor: 'var(--brand-primary)',
                        color: '#ffffff',
                      }
                    : {
                        color: 'var(--text-secondary)',
                      }
                }
              >
                {tab === 'all' ? 'All Sources' : tab}
              </button>
            ))}
          </div>
        </div>

        {obsLoading ? (
          <div className="space-y-2.5">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : filteredObservations.length === 0 ? (
          <EmptyState
            title="No Observations Recorded for This Filter"
            description="Log a direct field measurement (soil pH, moisture, temperature) or external weather station reading."
            icon={<ClipboardList className="w-6 h-6" />}
            action={
              <Button
                size="sm"
                leftIcon={<Plus className="w-4 h-4" />}
                onClick={() => setModalOpen(true)}
              >
                Log First Observation
              </Button>
            }
          />
        ) : (
          <div className="space-y-3">
            {filteredObservations.map((obs) => (
              <div
                key={obs.id}
                className="p-4 rounded-xl surface-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <ProvenanceBadge type={obs.epistemic_type} />
                    <span className="text-xs font-bold uppercase tracking-wide">
                      Source: {obs.source}
                    </span>
                    <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                      Record #{obs.id}
                    </span>
                  </div>

                  {/* Key-Value Measurement Chips */}
                  <div className="flex flex-wrap gap-2 pt-1">
                    {Object.entries(obs.data || {}).map(([k, v]) => (
                      <span
                        key={k}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold border tabular-nums"
                        style={{
                          backgroundColor: 'var(--bg-surface)',
                          borderColor: 'var(--border-default)',
                        }}
                      >
                        {k}: <strong>{String(v)}</strong>
                      </span>
                    ))}
                  </div>

                  {obs.notes && (
                    <p className="text-xs italic pt-0.5" style={{ color: 'var(--text-secondary)' }}>
                      “{obs.notes}”
                    </p>
                  )}
                </div>

                <time
                  className="text-xs tabular-nums shrink-0"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {new Date(obs.observed_at).toLocaleString()}
                </time>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Modal: Record Observation */}
      <ModalOrSheet
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={`Record Observation — ${plot.name}`}
        subtitle="Persists to POST /api/v1/farms/{farm_id}/plots/{plot_id}/observations"
      >
        <form onSubmit={handleCreateObservation} className="space-y-4">
          {formError && <ErrorAlert message={formError} />}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label htmlFor="obs-epistemic-select" className="block text-xs font-bold mb-1">
                Epistemic Provenance <span className="text-red-500">*</span>
              </label>
              <select
                id="obs-epistemic-select"
                value={epistemicType}
                onChange={(e) => setEpistemicType(e.target.value as 'observed' | 'external')}
                className="input-field"
              >
                <option value="observed">Observed (Direct Field / Sensor)</option>
                <option value="external">External (Weather Provider / NASA POWER)</option>
              </select>
            </div>

            <div>
              <label htmlFor="obs-source-select" className="block text-xs font-bold mb-1">
                Data Source Identifier <span className="text-red-500">*</span>
              </label>
              <select
                id="obs-source-select"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="input-field"
              >
                <option value="field_scout">Field Scout Inspection</option>
                <option value="iot_soil_probe">IoT Soil Probe</option>
                <option value="weather_station">Local Weather Station</option>
                <option value="nasa_power_agro">NASA POWER Agroclimatology</option>
                <option value="drone_multispectral">Drone Multispectral Pass</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="obs-temp" className="block text-xs font-bold mb-1">
                Temperature (°C)
              </label>
              <input
                id="obs-temp"
                type="number"
                step="0.1"
                value={tempC}
                onChange={(e) => setTempC(e.target.value)}
                className="input-field"
              />
            </div>
            <div>
              <label htmlFor="obs-moisture" className="block text-xs font-bold mb-1">
                Soil Moisture (%)
              </label>
              <input
                id="obs-moisture"
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={moisturePct}
                onChange={(e) => setMoisturePct(e.target.value)}
                className="input-field"
              />
            </div>
            <div>
              <label htmlFor="obs-ph" className="block text-xs font-bold mb-1">
                Soil pH (3.0–10.0)
              </label>
              <input
                id="obs-ph"
                type="number"
                step="0.1"
                min="3"
                max="10"
                value={soilPh}
                onChange={(e) => setSoilPh(e.target.value)}
                className="input-field"
              />
            </div>
            <div>
              <label htmlFor="obs-rain" className="block text-xs font-bold mb-1">
                Precipitation (mm)
              </label>
              <input
                id="obs-rain"
                type="number"
                step="0.1"
                min="0"
                value={rainfallMm}
                onChange={(e) => setRainfallMm(e.target.value)}
                className="input-field"
              />
            </div>
          </div>

          <div>
            <label htmlFor="obs-notes" className="block text-xs font-bold mb-1">
              Agronomist / Scout Notes (Optional)
            </label>
            <textarea
              id="obs-notes"
              rows={2}
              placeholder="e.g., Lower canopy dew observed after morning fog."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input-field"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={createObsMutation.isPending}>
              Save Observation
            </Button>
          </div>
        </form>
      </ModalOrSheet>
    </div>
  );
};
