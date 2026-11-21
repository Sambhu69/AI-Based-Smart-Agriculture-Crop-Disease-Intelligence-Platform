import React, { useMemo, useState } from 'react';
import {
  ArrowDownUp,
  ChevronDown,
  ChevronUp,
  Filter,
  History,
  RefreshCw,
  Search,
} from 'lucide-react';
import { useHistoryList } from '../hooks/useAgriQueries';
import { ProvenanceBadge } from '../components/ui/ProvenanceBadge';
import { Button, Card, EmptyState, ErrorAlert, Skeleton } from '../components/ui/Primitives';

const MODULE_OPTIONS = [
  { value: '', label: 'All Backend Modules' },
  { value: 'crop_disease_classification', label: 'Disease Classification (ResNet-50)' },
  { value: 'crop_yield_prediction', label: 'Crop Yield Prediction (Stage 6)' },
  { value: 'crop_and_irrigation_advisory', label: 'Crop & Irrigation Advisory' },
  { value: 'disease_outbreak_risk_assessment', label: 'Multimodal Outbreak Risk' },
  { value: 'twin_service_v1', label: 'Digital Twin Scenario Engine' },
];

export const HistoryPage: React.FC = () => {
  const [moduleFilter, setModuleFilter] = useState<string>('');
  const [limit, setLimit] = useState<number>(50);
  const [provFilter, setProvFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortAsc, setSortAsc] = useState<boolean>(false);
  const [expandedCardId, setExpandedCardId] = useState<string | null>(null);

  const {
    data: historyData,
    isLoading,
    isError,
    error,
    refetch,
  } = useHistoryList({
    limit,
    moduleName: moduleFilter || null,
  });

  const filteredItems = useMemo(() => {
    const raw = historyData?.items || [];
    const filtered = raw.filter((item) => {
      if (provFilter !== 'all' && item.epistemic_type !== provFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchSummary = item.summary.toLowerCase().includes(q);
        const matchModule = item.module_name.toLowerCase().includes(q);
        const matchId = String(item.id).includes(q);
        return matchSummary || matchModule || matchId;
      }
      return true;
    });

    return [...filtered].sort((a, b) => {
      const tA = new Date(a.timestamp).getTime();
      const tB = new Date(b.timestamp).getTime();
      return sortAsc ? tA - tB : tB - tA;
    });
  }, [historyData, provFilter, searchQuery, sortAsc]);

  return (
    <div className="space-y-5">
      {/* Header */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <ProvenanceBadge type="predicted" />
              <ProvenanceBadge type="simulated" />
              <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                UNIFIED PROVENANCE AUDIT LEDGER
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-extrabold font-display">
              Prediction & Digital Twin Scenario History
            </h2>
            <p className="text-xs sm:text-sm" style={{ color: 'var(--text-secondary)' }}>
              Inspect persisted <code>prediction_records</code> and <code>twin_scenarios</code> from{' '}
              <code>GET /api/v1/history</code> with model versions, timestamps, and epistemic tags.
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw className="w-4 h-4" />}
            onClick={() => refetch()}
          >
            Refresh Ledger
          </Button>
        </div>
      </Card>

      {/* Filter & Search Bar */}
      <Card padding="md" className="space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
          {/* Search Input */}
          <div className="sm:col-span-5 relative">
            <label htmlFor="history-search" className="sr-only">
              Search history records
            </label>
            <Search
              className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2"
              style={{ color: 'var(--text-muted)' }}
            />
            <input
              id="history-search"
              type="search"
              placeholder="Search summary, module, or record ID…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field pl-9 text-xs"
            />
          </div>

          {/* Module Backend Filter */}
          <div className="sm:col-span-4">
            <label htmlFor="history-module-select" className="sr-only">
              Filter by Module
            </label>
            <select
              id="history-module-select"
              value={moduleFilter}
              onChange={(e) => setModuleFilter(e.target.value)}
              className="input-field text-xs"
            >
              {MODULE_OPTIONS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>

          {/* Limit & Sort Controls */}
          <div className="sm:col-span-3 flex gap-2">
            <select
              aria-label="Record Limit"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="input-field text-xs flex-1"
            >
              <option value={20}>20 rows</option>
              <option value={50}>50 rows</option>
              <option value={100}>100 rows</option>
            </select>

            <button
              type="button"
              onClick={() => setSortAsc((s) => !s)}
              className="touch-target px-3 rounded-xl border text-xs font-semibold inline-flex items-center gap-1 surface-subtle"
              title="Toggle timestamp sort direction"
            >
              <ArrowDownUp className="w-3.5 h-3.5" />
              <span>{sortAsc ? 'Oldest' : 'Newest'}</span>
            </button>
          </div>
        </div>

        {/* Provenance Filter Pills */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t" style={{ borderColor: 'var(--border-default)' }}>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-bold mr-1 inline-flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
              <Filter className="w-3.5 h-3.5" />
              Provenance:
            </span>
            {(['all', 'predicted', 'simulated'] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setProvFilter(p)}
                className="px-3 py-1 rounded-full text-xs font-semibold capitalize transition-colors"
                style={
                  provFilter === p
                    ? { backgroundColor: 'var(--brand-primary)', color: '#ffffff' }
                    : { backgroundColor: 'var(--bg-subtle)', color: 'var(--text-secondary)' }
                }
              >
                {p === 'all' ? 'All Records' : p}
              </button>
            ))}
          </div>

          <span className="text-xs font-semibold tabular-nums" style={{ color: 'var(--text-muted)' }}>
            Showing {filteredItems.length} of {historyData?.count ?? 0} loaded records
          </span>
        </div>
      </Card>

      {isError && (
        <ErrorAlert
          message={error instanceof Error ? error.message : 'Failed to load history'}
          onRetry={() => refetch()}
        />
      )}

      {/* Results View */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : filteredItems.length === 0 ? (
        <EmptyState
          title="No Matching History Records Found"
          description="Try clearing your search or module filter, or execute a new prediction or digital twin scenario."
          icon={<History className="w-6 h-6" />}
        />
      ) : (
        <>
          {/* DESKTOP VIEW (>= 768px): Structured Data Table */}
          <Card padding="none" className="hidden md:block overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr
                    className="border-b surface-subtle"
                    style={{ borderColor: 'var(--border-default)' }}
                  >
                    <th className="py-3 px-4 font-bold">Provenance</th>
                    <th className="py-3 px-4 font-bold">Record ID</th>
                    <th className="py-3 px-4 font-bold">Module / Engine</th>
                    <th className="py-3 px-4 font-bold">Model Version</th>
                    <th className="py-3 px-4 font-bold">Result Summary</th>
                    <th className="py-3 px-4 font-bold">Plot</th>
                    <th className="py-3 px-4 font-bold text-right">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: 'var(--border-default)' }}>
                  {filteredItems.map((item) => {
                    const key = `${item.record_type}-${item.id}`;
                    return (
                      <tr key={key} className="hover:opacity-95">
                        <td className="py-3 px-4">
                          <ProvenanceBadge type={item.epistemic_type} />
                        </td>
                        <td className="py-3 px-4 font-mono font-semibold">
                          #{item.id}{' '}
                          <span className="text-[10px] opacity-75">({item.record_type})</span>
                        </td>
                        <td className="py-3 px-4 font-semibold">{item.module_name}</td>
                        <td className="py-3 px-4 tabular-nums">
                          {item.model_version ? `v${item.model_version}` : '—'}
                        </td>
                        <td className="py-3 px-4 max-w-md truncate font-medium">
                          {item.summary}
                        </td>
                        <td className="py-3 px-4">
                          {item.plot_id ? `Plot #${item.plot_id}` : 'Unlinked'}
                        </td>
                        <td
                          className="py-3 px-4 text-right tabular-nums whitespace-nowrap"
                          style={{ color: 'var(--text-muted)' }}
                        >
                          {new Date(item.timestamp).toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          {/* MOBILE VIEW (< 768px): Expandable Activity Cards */}
          <div className="md:hidden space-y-2.5">
            {filteredItems.map((item) => {
              const key = `${item.record_type}-${item.id}`;
              const isExpanded = expandedCardId === key;
              return (
                <Card key={key} padding="sm" className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <ProvenanceBadge type={item.epistemic_type} />
                      <span className="text-xs font-bold font-mono">#{item.id}</span>
                    </div>
                    <time className="text-[11px] tabular-nums" style={{ color: 'var(--text-muted)' }}>
                      {new Date(item.timestamp).toLocaleString()}
                    </time>
                  </div>

                  <p className="text-xs font-bold">{item.summary}</p>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] font-medium" style={{ color: 'var(--text-secondary)' }}>
                      Module: <code>{item.module_name}</code>
                    </span>
                    <button
                      type="button"
                      onClick={() => setExpandedCardId(isExpanded ? null : key)}
                      className="text-xs font-semibold inline-flex items-center gap-1"
                      style={{ color: 'var(--brand-primary)' }}
                    >
                      <span>{isExpanded ? 'Hide Details' : 'Details'}</span>
                      {isExpanded ? (
                        <ChevronUp className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="p-2.5 rounded-xl surface-subtle text-[11px] space-y-1">
                      <div>
                        Record Type: <strong>{item.record_type}</strong>
                      </div>
                      <div>
                        Model Version: <strong>{item.model_version || 'Not applicable'}</strong>
                      </div>
                      <div>
                        Plot Association:{' '}
                        <strong>{item.plot_id ? `Plot #${item.plot_id}` : 'Unlinked'}</strong>
                      </div>
                      <div>
                        ISO Timestamp: <code>{item.timestamp}</code>
                      </div>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};
