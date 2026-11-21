import React, { useState } from 'react';
import {
  AlertTriangle,
  BrainCircuit,
  Droplets,
  Network,
  Send,
  ShieldAlert,
  Sparkles,
  Thermometer,
} from 'lucide-react';
import { useAppContext } from '../context/AppContext';
import { useAssessIntelligenceMutation, useFarmDetail } from '../hooks/useAgriQueries';
import { ProvenanceBadge } from '../components/ui/ProvenanceBadge';
import { Button, Card, ErrorAlert } from '../components/ui/Primitives';
import type { IntelligenceAssessmentResponse } from '../types/api';

const CROPS = ['Tomato', 'Potato', 'Pepper', 'Maize', 'Rice'];

const DETERMINISTIC_QUERY_PRESETS = [
  {
    label: 'Outbreak Risk Check',
    query: 'Is there any risk of late blight outbreak under current humidity and temperature?',
  },
  {
    label: '14-Day RL Irrigation Sim',
    query: 'Run an irrigation RL simulation for water savings over 14 days',
  },
  {
    label: 'Knowledge Graph Topology',
    query: 'Show me the agricultural graph network topology and disease bridges',
  },
  {
    label: 'Crop Suitability Check',
    query: 'Which crop is recommended for current soil pH and temperature?',
  },
];

export const IntelligencePage: React.FC = () => {
  const { selectedFarmId } = useAppContext();
  const { data: farmDetail } = useFarmDetail(selectedFarmId);

  const [cropType, setCropType] = useState('Tomato');
  const [temperatureC, setTemperatureC] = useState('20.5');
  const [humidityPct, setHumidityPct] = useState('88.0');
  const [rainfallMm, setRainfallMm] = useState('8.0');
  const [visualAnomaly, setVisualAnomaly] = useState('0.25');
  const [queryText, setQueryText] = useState(DETERMINISTIC_QUERY_PRESETS[0].query);
  const [plotId, setPlotId] = useState<number | null>(null);

  const [result, setResult] = useState<IntelligenceAssessmentResponse | null>(null);
  const assessMutation = useAssessIntelligenceMutation();

  const runAssessment = async (overrideQuery?: string) => {
    const q = overrideQuery !== undefined ? overrideQuery : queryText;
    try {
      const res = await assessMutation.mutateAsync({
        crop_type: cropType,
        temperature_c: Number(temperatureC),
        relative_humidity_pct: Number(humidityPct),
        rainfall_mm: Number(rainfallMm),
        visual_anomaly_score: Number(visualAnomaly),
        query: q.trim() || null,
        plot_id: plotId || null,
      });
      setResult(res);
    } catch {
      // handled by mutation error
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runAssessment();
  };

  const risk = result?.risk_assessment;
  const assistant = result?.assistant_response;
  const toolData = (assistant?.tool_data || null) as Record<string, any> | null;

  return (
    <div className="space-y-5">
      {/* Header */}
      <Card padding="md">
        <div className="flex flex-wrap items-center gap-2 mb-1">
          <ProvenanceBadge type="predicted" />
          <ProvenanceBadge type="simulated" />
          <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
            MULTIMODAL OUTBREAK RISK • RL WATER BALANCE • NETWORKX GRAPH
          </span>
        </div>
        <h2 className="text-lg sm:text-xl font-extrabold font-display">
          Agricultural Intelligence & Decision Support Center
        </h2>
        <p className="text-xs sm:text-sm" style={{ color: 'var(--text-secondary)' }}>
          Evaluate microclimate pathogen conduciveness, run 14-day Q-learning irrigation
          simulations, and inspect regional farm-pathogen graph topology via{' '}
          <code>POST /api/v1/intelligence/assess</code>.
        </p>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left 5 Cols: Microclimate Inputs & Tool-Grounded Assistant Query */}
        <Card padding="md" className="lg:col-span-5 self-start">
          <form onSubmit={handleSubmit} className="space-y-4">
            <h3 className="text-base font-bold font-display flex items-center gap-2">
              <Thermometer className="w-4 h-4 text-emerald-600" />
              <span>Canopy Microclimate & Scouting Inputs</span>
            </h3>

            {assessMutation.isError && (
              <ErrorAlert
                message={
                  assessMutation.error instanceof Error
                    ? assessMutation.error.message
                    : 'Intelligence assessment failed'
                }
              />
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="intel-crop" className="block text-xs font-bold mb-1">
                  Crop Species
                </label>
                <select
                  id="intel-crop"
                  value={cropType}
                  onChange={(e) => setCropType(e.target.value)}
                  className="input-field"
                >
                  {CROPS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="intel-plot" className="block text-xs font-bold mb-1">
                  Link to Plot (Optional)
                </label>
                <select
                  id="intel-plot"
                  value={plotId ?? ''}
                  onChange={(e) => setPlotId(e.target.value ? Number(e.target.value) : null)}
                  className="input-field"
                >
                  <option value="">Unlinked Assessment</option>
                  {farmDetail?.plots?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.crop_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="intel-temp" className="block text-xs font-bold mb-1">
                  Temperature (°C)
                </label>
                <input
                  id="intel-temp"
                  type="number"
                  step="0.5"
                  min="-10"
                  max="55"
                  value={temperatureC}
                  onChange={(e) => setTemperatureC(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label htmlFor="intel-rh" className="block text-xs font-bold mb-1">
                  Relative Humidity (%)
                </label>
                <input
                  id="intel-rh"
                  type="number"
                  step="1"
                  min="0"
                  max="100"
                  value={humidityPct}
                  onChange={(e) => setHumidityPct(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label htmlFor="intel-rain" className="block text-xs font-bold mb-1">
                  24h Rainfall (mm)
                </label>
                <input
                  id="intel-rain"
                  type="number"
                  step="0.5"
                  min="0"
                  value={rainfallMm}
                  onChange={(e) => setRainfallMm(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label htmlFor="intel-anomaly" className="block text-xs font-bold mb-1">
                  Visual Lesion Score (0–1)
                </label>
                <input
                  id="intel-anomaly"
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={visualAnomaly}
                  onChange={(e) => setVisualAnomaly(e.target.value)}
                  className="input-field"
                />
              </div>
            </div>

            {/* Deterministic Assistant Dispatcher */}
            <div className="pt-3 border-t space-y-2.5" style={{ borderColor: 'var(--border-default)' }}>
              <label htmlFor="intel-query" className="block text-xs font-bold">
                Deterministic Tool-Grounded Assistant Query
              </label>
              <textarea
                id="intel-query"
                rows={2}
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                placeholder="Ask about late blight risk, RL irrigation simulation, crop suitability, or graph topology…"
                className="input-field text-xs"
              />

              <div className="flex flex-wrap gap-1.5">
                {DETERMINISTIC_QUERY_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => {
                      setQueryText(preset.query);
                      runAssessment(preset.query);
                    }}
                    className="px-2.5 py-1 rounded-lg text-[11px] font-semibold surface-subtle hover:opacity-80"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              isLoading={assessMutation.isPending}
              leftIcon={<Send className="w-4 h-4" />}
            >
              Run Multimodal Risk & Assistant
            </Button>
          </form>
        </Card>

        {/* Right 7 Cols: Outbreak Risk Card + Assistant Tool Output */}
        <div className="lg:col-span-7 space-y-4">
          {!result || !risk ? (
            <Card padding="lg" className="min-h-[340px] flex flex-col items-center justify-center text-center">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
                style={{ backgroundColor: 'var(--brand-soft)', color: 'var(--brand-primary)' }}
              >
                <BrainCircuit className="w-7 h-7" />
              </div>
              <h3 className="text-base sm:text-lg font-bold font-display mb-1">
                Ready for Multimodal Risk & Tool Evaluation
              </h3>
              <p className="text-xs sm:text-sm max-w-md" style={{ color: 'var(--text-secondary)' }}>
                Tap <strong>Run Multimodal Risk & Assistant</strong> or any quick-preset button on
                the left to evaluate pathogen outbreak risk and execute deterministic platform tools.
              </p>
            </Card>
          ) : (
            <>
              {/* 1. Outbreak Risk Assessment Card */}
              <Card padding="lg" className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <ProvenanceBadge type={risk.epistemic_type} size="md" />
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold uppercase ${
                        risk.risk_level === 'Low'
                          ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                          : risk.risk_level === 'Moderate'
                          ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300'
                          : 'bg-red-500/15 text-red-700 dark:text-red-300'
                      }`}
                    >
                      {risk.risk_level} Outbreak Risk
                    </span>
                  </div>
                  <span className="text-xs tabular-nums" style={{ color: 'var(--text-muted)' }}>
                    Est. Leaf Wetness: <strong>{risk.estimated_leaf_wetness_hours}h</strong>
                  </span>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
                  <div>
                    <h3 className="text-lg sm:text-xl font-extrabold font-display">
                      {risk.crop_type} Pathogen Conduciveness Assessment
                    </h3>
                    <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                      Environmental Subscore: {(risk.environmental_risk_subscore * 100).toFixed(1)}%
                      • Visual Anomaly Score: {(risk.visual_anomaly_score * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className="text-2xl sm:text-3xl font-extrabold font-display tabular-nums">
                    {(risk.risk_score * 100).toFixed(1)}%
                  </div>
                </div>

                {/* Primary Threats */}
                <div className="space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider block" style={{ color: 'var(--text-muted)' }}>
                    Primary Pathogen Threats Identified
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {risk.primary_threats.map((threat) => (
                      <span
                        key={threat}
                        className="px-3 py-1 rounded-xl text-xs font-semibold surface-subtle flex items-center gap-1.5"
                      >
                        <ShieldAlert className="w-3.5 h-3.5 text-red-500" />
                        {threat}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Contributing Factors & Preventative Actions */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  <div className="p-3.5 rounded-xl surface-subtle space-y-1.5">
                    <span className="text-xs font-bold block">Contributing Risk Drivers</span>
                    <ul className="text-xs pl-4 list-disc space-y-1" style={{ color: 'var(--text-secondary)' }}>
                      {risk.contributing_factors.length > 0 ? (
                        risk.contributing_factors.map((f, i) => <li key={i}>{f}</li>)
                      ) : (
                        <li>Microclimate currently within low-conduciveness bounds.</li>
                      )}
                    </ul>
                  </div>

                  <div className="p-3.5 rounded-xl surface-subtle space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold">Preventative Actions</span>
                      <ProvenanceBadge type="recommended" />
                    </div>
                    <ul className="text-xs pl-4 list-disc space-y-1" style={{ color: 'var(--text-secondary)' }}>
                      {risk.preventative_actions.map((act, i) => (
                        <li key={i}>{act}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <p className="text-[11px] italic" style={{ color: 'var(--text-muted)' }}>
                  {risk.caveats}
                </p>
              </Card>

              {/* 2. Tool-Grounded Assistant Response Card */}
              {assistant && (
                <Card padding="md" className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-emerald-600" />
                      <h4 className="text-sm sm:text-base font-bold font-display">
                        Tool-Grounded Assistant Output
                      </h4>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <ProvenanceBadge type={assistant.epistemic_type} />
                      <span className="text-[11px] px-2 py-0.5 rounded surface-subtle font-mono">
                        {assistant.intent_detected}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs sm:text-sm font-medium leading-relaxed p-3.5 rounded-xl surface-subtle">
                    {assistant.guidance}
                  </p>

                  {/* Specialized view if tool_data is RL Irrigation Simulation */}
                  {assistant.intent_detected === 'irrigation_rl_simulation' && toolData && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                      <div className="p-3 rounded-xl surface-subtle text-xs">
                        <span className="block font-bold text-sky-700 dark:text-sky-300">
                          Baseline Rule Water
                        </span>
                        <span className="text-lg font-extrabold tabular-nums">
                          {toolData.baseline_rule_results?.total_water_applied_mm} mm
                        </span>
                        <span className="block text-[11px]" style={{ color: 'var(--text-muted)' }}>
                          Stress days: {toolData.baseline_rule_results?.stress_days}
                        </span>
                      </div>
                      <div className="p-3 rounded-xl surface-subtle text-xs">
                        <span className="block font-bold text-emerald-700 dark:text-emerald-300">
                          Q-Learning Policy Water
                        </span>
                        <span className="text-lg font-extrabold tabular-nums">
                          {toolData.rl_policy_results?.total_water_applied_mm} mm
                        </span>
                        <span className="block text-[11px]" style={{ color: 'var(--text-muted)' }}>
                          Stress days: {toolData.rl_policy_results?.stress_days}
                        </span>
                      </div>
                      <div className="p-3 rounded-xl surface-subtle text-xs">
                        <span className="block font-bold">Simulated Water Savings</span>
                        <span className="text-lg font-extrabold tabular-nums text-emerald-600">
                          {toolData.rl_policy_results?.water_savings_pct}%
                        </span>
                        <span className="block text-[11px]" style={{ color: 'var(--text-muted)' }}>
                          Over {toolData.simulation_days} days
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Specialized view if tool_data is Agricultural Knowledge Graph */}
                  {assistant.intent_detected === 'agricultural_graph_topology' && toolData && (
                    <div className="space-y-2.5 pt-1 text-xs">
                      <div className="flex flex-wrap gap-2">
                        <span className="px-2.5 py-1 rounded-lg surface-subtle font-semibold">
                          Nodes: <strong>{toolData.node_count}</strong>
                        </span>
                        <span className="px-2.5 py-1 rounded-lg surface-subtle font-semibold">
                          Edges: <strong>{toolData.edge_count}</strong>
                        </span>
                        <span className="px-2.5 py-1 rounded-lg surface-subtle font-semibold">
                          Components: <strong>{toolData.connected_components}</strong>
                        </span>
                      </div>
                      {Array.isArray(toolData.top_central_nodes) && (
                        <div className="p-3 rounded-xl surface-subtle">
                          <span className="font-bold flex items-center gap-1.5 mb-1.5">
                            <Network className="w-3.5 h-3.5 text-emerald-600" />
                            Top Central Graph Entities (Degree Centrality)
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {toolData.top_central_nodes.map(
                              (n: { node: string; centrality: number; degree: number }) => (
                                <span
                                  key={n.node}
                                  className="px-2 py-0.5 rounded border text-[11px] font-mono"
                                  style={{ borderColor: 'var(--border-strong)' }}
                                >
                                  {n.node} (deg={n.degree}, c={n.centrality})
                                </span>
                              )
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                    Tools invoked: <code>{assistant.tools_invoked.join(', ') || 'none'}</code> •{' '}
                    {assistant.limitations}
                  </p>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
