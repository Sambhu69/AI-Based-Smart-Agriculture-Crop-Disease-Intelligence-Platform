import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  Cpu,
  FolderKanban,
  History,
  Layers,
  Leaf,
  Plus,
  RefreshCw,
  Sliders,
  Sprout,
  Table,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useAppContext } from '../context/AppContext';
import {
  useFarmDetail,
  useFarmsList,
  useHistoryList,
  useSystemHealth,
} from '../hooks/useAgriQueries';
import { ProvenanceBadge } from '../components/ui/ProvenanceBadge';
import { Button, Card, EmptyState, ErrorAlert, Skeleton } from '../components/ui/Primitives';

const MODULE_LABELS: Record<string, string> = {
  crop_disease_classification: 'Disease CV',
  crop_yield_prediction: 'Yield Model',
  crop_and_irrigation_advisory: 'Agronomy Rule',
  disease_outbreak_risk_assessment: 'Outbreak Risk',
  twin_service_v1: 'Digital Twin',
};

const PROVENANCE_COLORS: Record<string, string> = {
  predicted: '#7c3aed',
  simulated: '#0d9488',
  recommended: '#d97706',
  observed: '#059669',
  external: '#0284c7',
};

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectedFarmId, setSelectedFarmId } = useAppContext();

  const {
    data: health,
    isLoading: healthLoading,
    isError: healthError,
    refetch: refetchHealth,
  } = useSystemHealth();
  const {
    data: farms,
    isLoading: farmsLoading,
    isError: farmsError,
    error: farmsErrObj,
    refetch: refetchFarms,
  } = useFarmsList();

  const effectiveFarmId = useMemo(() => {
    if (selectedFarmId) return selectedFarmId;
    if (farms && farms.length > 0) return farms[0].id;
    return null;
  }, [selectedFarmId, farms]);

  const { data: activeFarmDetail, isLoading: farmDetailLoading } =
    useFarmDetail(effectiveFarmId);

  const {
    data: historyData,
    isLoading: historyLoading,
    refetch: refetchHistory,
  } = useHistoryList({ limit: 50 });

  const [showChartTable, setShowChartTable] = useState(false);

  const stats = useMemo(() => {
    const items = historyData?.items || [];
    const predictionsCount = items.filter((i) => i.record_type === 'prediction').length;
    const twinCount = items.filter((i) => i.record_type === 'twin_scenario').length;
    return {
      totalFarms: farms?.length ?? 0,
      activeFarmPlots: activeFarmDetail?.plots?.length ?? 0,
      predictionsCount,
      twinCount,
    };
  }, [farms, activeFarmDetail, historyData]);

  const moduleBreakdown = useMemo(() => {
    const items = historyData?.items || [];
    const counts: Record<string, { module: string; count: number; epistemic: string }> = {};
    for (const item of items) {
      const key = item.module_name;
      if (!counts[key]) {
        counts[key] = {
          module: MODULE_LABELS[key] || key,
          count: 0,
          epistemic: item.epistemic_type,
        };
      }
      counts[key].count += 1;
    }
    return Object.values(counts);
  }, [historyData]);

  const todayFormatted = new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date());

  return (
    <div className="space-y-5 sm:space-y-6">
      {/* =====================================================================
          HERO & QUICK WORKFLOW LAUNCHER
      ===================================================================== */}
      <Card padding="lg" className="relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
              <span
                className="px-2.5 py-0.5 rounded-full"
                style={{
                  backgroundColor: 'var(--brand-soft)',
                  color: 'var(--brand-text)',
                }}
              >
                PRECISION AGRICULTURE SAAS
              </span>
              <span style={{ color: 'var(--text-muted)' }}>{todayFormatted}</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-extrabold font-display">
              Agricultural Digital Twin & Food Security Command
            </h2>
            <p className="text-xs sm:text-sm max-w-2xl" style={{ color: 'var(--text-secondary)' }}>
              Monitor field observations, run ResNet-50 leaf pathology inference, forecast tabular
              crop yields, and simulate climate stress scenarios with strict epistemic provenance.
            </p>
          </div>

          {/* Primary Quick Actions (Touch-Friendly >=44px) */}
          <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-2.5 shrink-0">
            <Button
              variant="primary"
              leftIcon={<Leaf className="w-4 h-4" />}
              onClick={() => navigate('/diagnosis')}
            >
              Diagnose Leaf
            </Button>
            <Button
              variant="secondary"
              leftIcon={<Sliders className="w-4 h-4" />}
              onClick={() => navigate('/digital-twin')}
            >
              Simulate Twin
            </Button>
            <Button
              variant="outline"
              leftIcon={<BrainCircuit className="w-4 h-4" />}
              onClick={() => navigate('/intelligence')}
            >
              Outbreak Risk
            </Button>
            <Button
              variant="outline"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={() => navigate('/farms')}
            >
              Manage Farms
            </Button>
          </div>
        </div>
      </Card>

      {/* =====================================================================
          SYSTEM TELEMETRY STRIP (VERIFIED BACKEND HEALTH)
      ===================================================================== */}
      <Card padding="sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="inline-flex items-center gap-1.5 font-bold">
              <Cpu className="w-4 h-4 text-emerald-600" />
              Backend Telemetry:
            </span>
            {healthLoading ? (
              <span style={{ color: 'var(--text-muted)' }}>Polling /api/v1/health…</span>
            ) : healthError || !health ? (
              <span className="text-red-600 dark:text-red-400 font-semibold">
                FastAPI unreachable — start server with <code>uvicorn app.main:app --port 8000</code>
              </span>
            ) : (
              <>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md surface-subtle font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Status: <strong className="uppercase">{health.status}</strong>
                </span>
                <span className="px-2 py-0.5 rounded-md surface-subtle font-medium">
                  Model: <strong>{health.model_architecture}</strong> (v{health.model_version})
                </span>
                <span className="px-2 py-0.5 rounded-md surface-subtle font-medium">
                  Device: <strong className="uppercase">{health.inference_device}</strong>
                </span>
                <span className="px-2 py-0.5 rounded-md surface-subtle font-medium">
                  Classes: <strong>{health.num_classes}</strong>
                </span>
              </>
            )}
          </div>

          <button
            type="button"
            onClick={() => {
              refetchHealth();
              refetchFarms();
              refetchHistory();
            }}
            className="touch-target px-2.5 py-1 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 surface-subtle hover:opacity-80"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Sync Data</span>
          </button>
        </div>
      </Card>

      {farmsError && (
        <ErrorAlert
          title="Backend Connection Unavailable"
          message={
            farmsErrObj instanceof Error
              ? farmsErrObj.message
              : 'Could not load farm records from FastAPI.'
          }
          onRetry={() => {
            refetchHealth();
            refetchFarms();
            refetchHistory();
          }}
        />
      )}

      {/* =====================================================================
          SUMMARY METRIC CARDS (GROUNDED IN ACTUAL DB RECORDS)
      ===================================================================== */}
      <section aria-label="Platform Metrics Summary" className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <Card padding="md" className="flex flex-col justify-between">
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
              Registered Farms
            </span>
            <ProvenanceBadge type="observed" />
          </div>
          {farmsLoading ? (
            <Skeleton className="h-8 w-20" />
          ) : (
            <div className="flex items-baseline justify-between">
              <span className="text-2xl sm:text-3xl font-extrabold font-display tabular-nums">
                {stats.totalFarms}
              </span>
              <button
                type="button"
                onClick={() => navigate('/farms')}
                className="text-xs font-semibold inline-flex items-center gap-1 hover:underline"
                style={{ color: 'var(--brand-primary)' }}
              >
                View <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </Card>

        <Card padding="md" className="flex flex-col justify-between">
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-xs font-semibold truncate" style={{ color: 'var(--text-secondary)' }}>
              {activeFarmDetail ? `Plots (${activeFarmDetail.name})` : 'Active Farm Plots'}
            </span>
            <ProvenanceBadge type="observed" />
          </div>
          {farmDetailLoading ? (
            <Skeleton className="h-8 w-20" />
          ) : (
            <div className="flex items-baseline justify-between">
              <span className="text-2xl sm:text-3xl font-extrabold font-display tabular-nums">
                {stats.activeFarmPlots}
              </span>
              <button
                type="button"
                onClick={() => navigate('/farms')}
                className="text-xs font-semibold inline-flex items-center gap-1 hover:underline"
                style={{ color: 'var(--brand-primary)' }}
              >
                Manage <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </Card>

        <Card padding="md" className="flex flex-col justify-between">
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
              AI Predictions Logged
            </span>
            <ProvenanceBadge type="predicted" />
          </div>
          {historyLoading ? (
            <Skeleton className="h-8 w-20" />
          ) : (
            <div className="flex items-baseline justify-between">
              <span className="text-2xl sm:text-3xl font-extrabold font-display tabular-nums">
                {stats.predictionsCount}
              </span>
              <button
                type="button"
                onClick={() => navigate('/history')}
                className="text-xs font-semibold inline-flex items-center gap-1 hover:underline"
                style={{ color: 'var(--brand-primary)' }}
              >
                Audit <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </Card>

        <Card padding="md" className="flex flex-col justify-between">
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
              Twin Scenarios Run
            </span>
            <ProvenanceBadge type="simulated" />
          </div>
          {historyLoading ? (
            <Skeleton className="h-8 w-20" />
          ) : (
            <div className="flex items-baseline justify-between">
              <span className="text-2xl sm:text-3xl font-extrabold font-display tabular-nums">
                {stats.twinCount}
              </span>
              <button
                type="button"
                onClick={() => navigate('/digital-twin')}
                className="text-xs font-semibold inline-flex items-center gap-1 hover:underline"
                style={{ color: 'var(--brand-primary)' }}
              >
                Studio <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </Card>
      </section>

      {/* =====================================================================
          MAIN GRID: PROVENANCE ACTIVITY CHART + ACTIVE FARM PLOTS
      ===================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left 7 cols: Intelligence Activity by Module & Provenance */}
        <Card padding="md" className="lg:col-span-7 flex flex-col justify-between">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
              <div>
                <h3 className="text-base font-bold font-display">
                  Logged Intelligence & Simulation Activity
                </h3>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  Distribution of persisted database records by execution module and provenance
                </p>
              </div>
              <div className="flex items-center gap-2">
                <ProvenanceBadge type="predicted" />
                <ProvenanceBadge type="simulated" />
                <button
                  type="button"
                  onClick={() => setShowChartTable((v) => !v)}
                  className="px-2.5 py-1 rounded-lg text-xs font-semibold surface-subtle inline-flex items-center gap-1"
                  aria-expanded={showChartTable}
                >
                  <Table className="w-3.5 h-3.5" />
                  <span>{showChartTable ? 'Show Chart' : 'Data Table'}</span>
                </button>
              </div>
            </div>

            {historyLoading ? (
              <Skeleton className="h-60 w-full" />
            ) : moduleBreakdown.length === 0 ? (
              <EmptyState
                title="No Model or Simulation Runs Logged Yet"
                description="Run a leaf disease diagnosis, yield forecast, or digital twin scenario to populate real provenance telemetry."
                icon={<Activity className="w-6 h-6" />}
                action={
                  <div className="flex flex-wrap justify-center gap-2">
                    <Button size="sm" onClick={() => navigate('/diagnosis')}>
                      Run Leaf Diagnosis
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => navigate('/digital-twin')}>
                      Run Twin Scenario
                    </Button>
                  </div>
                }
              />
            ) : showChartTable ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b" style={{ borderColor: 'var(--border-default)' }}>
                      <th className="py-2 px-3 font-bold">Module</th>
                      <th className="py-2 px-3 font-bold">Provenance</th>
                      <th className="py-2 px-3 font-bold text-right">Records Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {moduleBreakdown.map((row) => (
                      <tr
                        key={row.module}
                        className="border-b"
                        style={{ borderColor: 'var(--border-default)' }}
                      >
                        <td className="py-2 px-3 font-medium">{row.module}</td>
                        <td className="py-2 px-3">
                          <ProvenanceBadge type={row.epistemic} />
                        </td>
                        <td className="py-2 px-3 text-right font-bold tabular-nums">
                          {row.count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="h-60 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={moduleBreakdown}
                    margin={{ top: 8, right: 12, left: -16, bottom: 8 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                    <XAxis
                      dataKey="module"
                      tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--bg-surface)',
                        borderColor: 'var(--border-default)',
                        borderRadius: '0.75rem',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="count" name="Logged Runs" radius={[6, 6, 0, 0]}>
                      {moduleBreakdown.map((entry, idx) => (
                        <Cell
                          key={`cell-${idx}`}
                          fill={PROVENANCE_COLORS[entry.epistemic] || '#1b5e3a'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </Card>

        {/* Right 5 cols: Active Farm & Plot Quick-Access */}
        <Card padding="md" className="lg:col-span-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2 mb-3">
              <div>
                <h3 className="text-base font-bold font-display">
                  {activeFarmDetail ? activeFarmDetail.name : 'Farm & Plot Registry'}
                </h3>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  {activeFarmDetail?.location || 'Select or register a farm to inspect plots'}
                </p>
              </div>
              <ProvenanceBadge type="observed" />
            </div>

            {farmsLoading || farmDetailLoading ? (
              <div className="space-y-2.5">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : !farms || farms.length === 0 ? (
              <EmptyState
                title="No Farms Registered"
                description="Register your first farm and crop plots to log field observations and link AI predictions."
                icon={<FolderKanban className="w-6 h-6" />}
                action={
                  <Button size="sm" onClick={() => navigate('/farms')}>
                    Register First Farm
                  </Button>
                }
              />
            ) : (
              <div className="space-y-3">
                {/* Farm Switcher Pills */}
                <div className="flex flex-wrap gap-1.5">
                  {farms.map((f) => {
                    const isSelected = f.id === effectiveFarmId;
                    return (
                      <button
                        key={f.id}
                        type="button"
                        onClick={() => setSelectedFarmId(f.id)}
                        className="px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors"
                        style={
                          isSelected
                            ? {
                                backgroundColor: 'var(--brand-primary)',
                                color: '#ffffff',
                                borderColor: 'var(--brand-primary)',
                              }
                            : {
                                backgroundColor: 'var(--bg-subtle)',
                                color: 'var(--text-primary)',
                                borderColor: 'var(--border-default)',
                              }
                        }
                      >
                        {f.name}
                      </button>
                    );
                  })}
                </div>

                {/* Plot List for Selected Farm */}
                {activeFarmDetail && activeFarmDetail.plots.length > 0 ? (
                  <ul className="space-y-2">
                    {activeFarmDetail.plots.map((plot) => (
                      <li key={plot.id}>
                        <button
                          type="button"
                          onClick={() =>
                            navigate(`/farms/${activeFarmDetail.id}/plots/${plot.id}`)
                          }
                          className="w-full text-left p-3 rounded-xl surface-subtle hover:opacity-90 flex items-center justify-between gap-2 transition-opacity"
                        >
                          <div className="min-w-0">
                            <div className="font-bold text-xs sm:text-sm truncate flex items-center gap-2">
                              <Sprout className="w-4 h-4 text-emerald-600 shrink-0" />
                              <span>{plot.name}</span>
                            </div>
                            <div
                              className="text-xs mt-0.5"
                              style={{ color: 'var(--text-secondary)' }}
                            >
                              Crop: <strong>{plot.crop_type}</strong>
                              {plot.area_hectares ? ` • ${plot.area_hectares} ha` : ''}
                            </div>
                          </div>
                          <ArrowRight className="w-4 h-4 shrink-0" />
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="p-4 rounded-xl surface-subtle text-center text-xs">
                    <p className="mb-2" style={{ color: 'var(--text-secondary)' }}>
                      No plots created under this farm yet.
                    </p>
                    <Button size="sm" variant="secondary" onClick={() => navigate('/farms')}>
                      Add Plot in Farm Manager
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="pt-3 mt-4 border-t flex justify-end" style={{ borderColor: 'var(--border-default)' }}>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => navigate('/farms')}
              leftIcon={<Layers className="w-4 h-4" />}
            >
              Open Full Farm & Plot Directory
            </Button>
          </div>
        </Card>
      </div>

      {/* =====================================================================
          RECENT PROVENANCE ACTIVITY STREAM (/api/v1/history)
      ===================================================================== */}
      <Card padding="md">
        <div className="flex items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="text-base font-bold font-display">
              Recent Predictions & Simulated Scenarios
            </h3>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              Live audit feed from <code>GET /api/v1/history</code> with explicit epistemic provenance
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            leftIcon={<History className="w-4 h-4" />}
            onClick={() => navigate('/history')}
          >
            Full History
          </Button>
        </div>

        {historyLoading ? (
          <div className="space-y-2.5">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : !historyData || historyData.items.length === 0 ? (
          <p className="text-xs py-4 text-center" style={{ color: 'var(--text-muted)' }}>
            No prediction or scenario records stored yet.
          </p>
        ) : (
          <div className="divide-y" style={{ borderColor: 'var(--border-default)' }}>
            {historyData.items.slice(0, 6).map((item) => (
              <div
                key={`${item.record_type}-${item.id}`}
                className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <ProvenanceBadge type={item.epistemic_type} />
                    <span className="text-xs font-bold">
                      {MODULE_LABELS[item.module_name] || item.module_name}
                    </span>
                    {item.model_version && (
                      <span
                        className="text-[11px] px-1.5 py-0.5 rounded surface-subtle"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        v{item.model_version}
                      </span>
                    )}
                    {item.plot_id && (
                      <span
                        className="text-[11px] px-1.5 py-0.5 rounded surface-subtle"
                        style={{ color: 'var(--text-secondary)' }}
                      >
                        Plot #{item.plot_id}
                      </span>
                    )}
                  </div>
                  <p className="text-xs sm:text-sm font-medium truncate">{item.summary}</p>
                </div>
                <time
                  className="text-[11px] tabular-nums shrink-0"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {new Date(item.timestamp).toLocaleString()}
                </time>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
