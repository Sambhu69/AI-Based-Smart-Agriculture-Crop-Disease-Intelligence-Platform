import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Play,
  RotateCcw,
  Sliders,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useAppContext } from '../context/AppContext';
import { useFarmDetail, useSimulateTwinMutation } from '../hooks/useAgriQueries';
import { ProvenanceBadge } from '../components/ui/ProvenanceBadge';
import { Button, Card, ErrorAlert } from '../components/ui/Primitives';
import type { TwinScenarioPreset, TwinSimulationResponse } from '../types/api';

const CROPS = ['Tomato', 'Potato', 'Pepper', 'Maize', 'Rice'];

const SCENARIO_PRESETS: Array<{
  id: TwinScenarioPreset;
  label: string;
  desc: string;
  defaults: {
    tempDelta: number;
    rainMult: number;
    irrigation: number;
    fertilizer: number;
    disease: number;
  };
}> = [
  {
    id: 'baseline',
    label: 'Baseline Reference',
    desc: 'Zero environmental perturbation; reference crop condition.',
    defaults: { tempDelta: 0.0, rainMult: 1.0, irrigation: 0, fertilizer: 0, disease: 0.0 },
  },
  {
    id: 'warming_2c',
    label: 'Warming +2°C',
    desc: 'Simulates a +2.0°C regional canopy temperature increase.',
    defaults: { tempDelta: 2.0, rainMult: 1.0, irrigation: 0, fertilizer: 0, disease: 0.0 },
  },
  {
    id: 'monsoon_drought',
    label: 'Monsoon Drought',
    desc: 'Severe precipitation deficit (×0.4 rainfall) and moisture stress.',
    defaults: { tempDelta: 0.0, rainMult: 0.4, irrigation: 0, fertilizer: 0, disease: 0.0 },
  },
  {
    id: 'wet_monsoon',
    label: 'Excess Wet Monsoon',
    desc: 'Heavy monsoon rainfall (×1.8) with potential waterlogging.',
    defaults: { tempDelta: 0.0, rainMult: 1.8, irrigation: 0, fertilizer: 0, disease: 0.0 },
  },
  {
    id: 'custom',
    label: 'Custom What-If',
    desc: 'User-configured multi-factor climate, irrigation, and disease shock.',
    defaults: { tempDelta: 1.5, rainMult: 0.75, irrigation: 35, fertilizer: 80, disease: 0.15 },
  },
];

export const DigitalTwinPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { selectedFarmId } = useAppContext();
  const { data: farmDetail } = useFarmDetail(selectedFarmId);

  const [cropType, setCropType] = useState(searchParams.get('crop') || 'Tomato');
  const [baselineYield, setBaselineYield] = useState('20000');
  const [scenario, setScenario] = useState<TwinScenarioPreset>('warming_2c');
  const [tempDelta, setTempDelta] = useState(2.0);
  const [rainMult, setRainMult] = useState(1.0);
  const [irrigationMm, setIrrigationMm] = useState(0);
  const [fertilizerKg, setFertilizerKg] = useState(0);
  const [diseasePressure, setDiseasePressure] = useState(0.0);
  const [plotId, setPlotId] = useState<number | null>(() => {
    const p = searchParams.get('plotId');
    return p ? Number(p) : null;
  });

  const [formError, setFormError] = useState<string | null>(null);
  const [result, setResult] = useState<TwinSimulationResponse | null>(null);

  const twinMutation = useSimulateTwinMutation();

  const applyPreset = (presetId: TwinScenarioPreset) => {
    setScenario(presetId);
    const found = SCENARIO_PRESETS.find((p) => p.id === presetId);
    if (found) {
      setTempDelta(found.defaults.tempDelta);
      setRainMult(found.defaults.rainMult);
      setIrrigationMm(found.defaults.irrigation);
      setFertilizerKg(found.defaults.fertilizer);
      setDiseasePressure(found.defaults.disease);
    }
  };

  const handleRunSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    const baseVal = Number(baselineYield);
    if (Number.isNaN(baseVal) || baseVal <= 0) {
      setFormError('Baseline yield must be greater than 0 kg/ha.');
      return;
    }

    try {
      const res = await twinMutation.mutateAsync({
        crop_type: cropType,
        baseline_yield_kg_ha: baseVal,
        scenario,
        temperature_delta_c: tempDelta,
        rainfall_multiplier: rainMult,
        irrigation_mm: irrigationMm,
        fertilizer_kg_ha: fertilizerKg,
        disease_pressure: diseasePressure,
        plot_id: plotId || null,
      });
      setResult(res);
    } catch {
      // handled by mutation error
    }
  };

  const factorChartData = result?.factor_breakdown
    ? [
        { factor: 'Temperature', multiplier: result.factor_breakdown.temperature },
        { factor: 'Rainfall', multiplier: result.factor_breakdown.rainfall_moisture },
        { factor: 'Irrigation', multiplier: result.factor_breakdown.irrigation },
        { factor: 'Fertilizer', multiplier: result.factor_breakdown.fertilizer },
        { factor: 'Disease', multiplier: result.factor_breakdown.disease },
      ]
    : [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <Card padding="md">
        <div className="flex flex-wrap items-center gap-2 mb-1">
          <ProvenanceBadge type="simulated" />
          <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
            5-FACTOR MULTIPLICATIVE SCENARIO ENGINE • TWIN_SERVICE_V1
          </span>
        </div>
        <h2 className="text-lg sm:text-xl font-extrabold font-display">
          Agricultural Digital Twin Scenario Studio
        </h2>
        <p className="text-xs sm:text-sm" style={{ color: 'var(--text-secondary)' }}>
          Configure hypothetical climate anomalies, supplemental irrigation, nutrient inputs, and
          foliar disease pressure to simulate directional yield sensitivity via{' '}
          <code>POST /api/v1/twin/simulate</code>.
        </p>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left 5 Cols: Scenario Configuration Controls */}
        <Card padding="md" className="lg:col-span-5 self-start">
          <form onSubmit={handleRunSimulation} className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold font-display flex items-center gap-2">
                <Sliders className="w-4 h-4 text-emerald-600" />
                <span>Scenario Parameters</span>
              </h3>
              <button
                type="button"
                onClick={() => applyPreset('baseline')}
                className="text-xs font-semibold inline-flex items-center gap-1 hover:underline"
                style={{ color: 'var(--text-secondary)' }}
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reset
              </button>
            </div>

            {formError && <ErrorAlert message={formError} />}
            {twinMutation.isError && (
              <ErrorAlert
                message={
                  twinMutation.error instanceof Error
                    ? twinMutation.error.message
                    : 'Simulation failed'
                }
              />
            )}

            {/* Named Scenario Presets */}
            <div>
              <span className="block text-xs font-bold mb-1.5">Named Scenario Preset</span>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {SCENARIO_PRESETS.map((p) => {
                  const active = scenario === p.id;
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => applyPreset(p.id)}
                      style={
                        active
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
                      className="px-2.5 py-2 rounded-xl border text-xs font-semibold text-left truncate transition-colors"
                    >
                      {p.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label htmlFor="twin-crop" className="block text-xs font-bold mb-1">
                  Crop Species
                </label>
                <select
                  id="twin-crop"
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
                <label htmlFor="twin-baseline" className="block text-xs font-bold mb-1">
                  Baseline Yield (kg/ha)
                </label>
                <input
                  id="twin-baseline"
                  type="number"
                  step="500"
                  min="500"
                  required
                  value={baselineYield}
                  onChange={(e) => setBaselineYield(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label htmlFor="twin-plot" className="block text-xs font-bold mb-1">
                  Persist to Plot
                </label>
                <select
                  id="twin-plot"
                  value={plotId ?? ''}
                  onChange={(e) => setPlotId(e.target.value ? Number(e.target.value) : null)}
                  className="input-field"
                >
                  <option value="">Ephemeral Run</option>
                  {farmDetail?.plots?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.crop_type})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Interactive Touch Sliders */}
            <div className="space-y-3 pt-2 border-t" style={{ borderColor: 'var(--border-default)' }}>
              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <label htmlFor="slider-temp">Temperature Shift (Δ°C)</label>
                  <span className="font-bold tabular-nums">
                    {tempDelta > 0 ? `+${tempDelta}` : tempDelta}°C
                  </span>
                </div>
                <input
                  id="slider-temp"
                  type="range"
                  min="-5"
                  max="10"
                  step="0.5"
                  value={tempDelta}
                  onChange={(e) => {
                    setScenario('custom');
                    setTempDelta(Number(e.target.value));
                  }}
                  className="w-full accent-emerald-600"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <label htmlFor="slider-rain">Rainfall Multiplier</label>
                  <span className="font-bold tabular-nums">×{rainMult.toFixed(2)}</span>
                </div>
                <input
                  id="slider-rain"
                  type="range"
                  min="0.1"
                  max="2.5"
                  step="0.1"
                  value={rainMult}
                  onChange={(e) => {
                    setScenario('custom');
                    setRainMult(Number(e.target.value));
                  }}
                  className="w-full accent-emerald-600"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <label htmlFor="slider-irrig">Supplemental Irrigation (mm)</label>
                  <span className="font-bold tabular-nums">{irrigationMm} mm</span>
                </div>
                <input
                  id="slider-irrig"
                  type="range"
                  min="0"
                  max="150"
                  step="5"
                  value={irrigationMm}
                  onChange={(e) => {
                    setScenario('custom');
                    setIrrigationMm(Number(e.target.value));
                  }}
                  className="w-full accent-emerald-600"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <label htmlFor="slider-fert">Additional Fertilizer (kg/ha)</label>
                  <span className="font-bold tabular-nums">{fertilizerKg} kg/ha</span>
                </div>
                <input
                  id="slider-fert"
                  type="range"
                  min="0"
                  max="250"
                  step="10"
                  value={fertilizerKg}
                  onChange={(e) => {
                    setScenario('custom');
                    setFertilizerKg(Number(e.target.value));
                  }}
                  className="w-full accent-emerald-600"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <label htmlFor="slider-disease">Foliar Disease Pressure (0–100%)</label>
                  <span className="font-bold tabular-nums">
                    {(diseasePressure * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  id="slider-disease"
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={diseasePressure}
                  onChange={(e) => {
                    setScenario('custom');
                    setDiseasePressure(Number(e.target.value));
                  }}
                  className="w-full accent-emerald-600"
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              isLoading={twinMutation.isPending}
              leftIcon={<Play className="w-4 h-4" />}
            >
              Execute Digital Twin Simulation
            </Button>
          </form>
        </Card>

        {/* Right 7 Cols: Comparison Cards & Factor Chart */}
        <div className="lg:col-span-7 space-y-4">
          {!result ? (
            <Card padding="lg" className="min-h-[360px] flex flex-col items-center justify-center text-center">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
                style={{ backgroundColor: 'var(--brand-soft)', color: 'var(--brand-primary)' }}
              >
                <Sliders className="w-7 h-7" />
              </div>
              <h3 className="text-base sm:text-lg font-bold font-display mb-1">
                Ready to Simulate What-If Scenario
              </h3>
              <p className="text-xs sm:text-sm max-w-md" style={{ color: 'var(--text-secondary)' }}>
                Choose a climate preset or adjust the 5 environmental sliders on the left, then tap{' '}
                <strong>Execute Digital Twin Simulation</strong>.
              </p>
            </Card>
          ) : (
            <>
              {/* 1. Stacked / Grid Comparison Cards */}
              <Card padding="lg" className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <ProvenanceBadge type={result.epistemic_type} size="md" />
                    <span className="text-xs font-bold uppercase px-2.5 py-0.5 rounded-full surface-subtle">
                      Scenario: {result.scenario}
                    </span>
                  </div>
                  {result.combined_yield_factor !== undefined &&
                    result.combined_yield_factor !== null && (
                      <span className="text-xs font-semibold tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                        Combined Factor: <strong>×{result.combined_yield_factor}</strong>
                      </span>
                    )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
                  <div className="p-4 rounded-2xl surface-subtle">
                    <span className="text-xs font-bold uppercase block" style={{ color: 'var(--text-secondary)' }}>
                      Baseline Reference
                    </span>
                    <div className="text-xl sm:text-2xl font-extrabold font-display tabular-nums mt-1">
                      {result.baseline_yield_kg_ha.toLocaleString()} kg/ha
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl surface-subtle">
                    <span className="text-xs font-bold uppercase block" style={{ color: 'var(--text-secondary)' }}>
                      Simulated Yield
                    </span>
                    <div className="text-xl sm:text-2xl font-extrabold font-display tabular-nums mt-1 text-teal-600 dark:text-teal-300">
                      {result.simulated_yield_kg_ha.toLocaleString()} kg/ha
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl surface-subtle">
                    <span className="text-xs font-bold uppercase block" style={{ color: 'var(--text-secondary)' }}>
                      Net Yield Impact
                    </span>
                    <div
                      className={`text-xl sm:text-2xl font-extrabold font-display tabular-nums mt-1 inline-flex items-center gap-1 ${
                        result.yield_change_pct >= 0
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      {result.yield_change_pct >= 0 ? (
                        <ArrowUpRight className="w-5 h-5" />
                      ) : (
                        <ArrowDownRight className="w-5 h-5" />
                      )}
                      <span>
                        {result.yield_change_pct > 0
                          ? `+${result.yield_change_pct}%`
                          : `${result.yield_change_pct}%`}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Key Drivers */}
                <div className="p-3.5 rounded-xl surface-subtle space-y-1.5 text-xs">
                  <span className="font-bold uppercase tracking-wider block" style={{ color: 'var(--text-secondary)' }}>
                    Primary Simulation Drivers
                  </span>
                  <ul className="pl-4 list-disc space-y-1">
                    {result.key_drivers.map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                </div>
              </Card>

              {/* 2. Multiplicative Factor Breakdown Chart */}
              {factorChartData.length > 0 && (
                <Card padding="md" className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-base font-bold font-display">
                        5-Factor Multiplicative Response Breakdown
                      </h4>
                      <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                        Multiplier &gt; 1.0 indicates positive yield boost; &lt; 1.0 indicates
                        stress penalty
                      </p>
                    </div>
                    <ProvenanceBadge type="simulated" />
                  </div>

                  <div className="h-56 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={factorChartData}
                        margin={{ top: 10, right: 12, left: -16, bottom: 4 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                        <XAxis dataKey="factor" tick={{ fontSize: 11 }} />
                        <YAxis domain={[0, 1.3]} tick={{ fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'var(--bg-surface)',
                            borderColor: 'var(--border-default)',
                            borderRadius: '0.75rem',
                            fontSize: '12px',
                          }}
                        />
                        <ReferenceLine y={1.0} stroke="#64748b" strokeDasharray="3 3" />
                        <Bar dataKey="multiplier" name="Yield Multiplier" radius={[6, 6, 0, 0]}>
                          {factorChartData.map((entry, idx) => (
                            <Cell
                              key={`cell-${idx}`}
                              fill={
                                entry.multiplier > 1.0
                                  ? '#059669'
                                  : entry.multiplier === 1.0
                                  ? '#0d9488'
                                  : '#dc2626'
                              }
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              )}

              {/* 3. Explicit Assumptions & Limitations */}
              <Card padding="md" className="space-y-2 text-xs">
                <div className="font-bold flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-teal-600" />
                  <span>Simulation Assumptions & Model Boundaries</span>
                </div>
                <ul className="pl-4 list-disc space-y-1" style={{ color: 'var(--text-secondary)' }}>
                  {result.assumptions.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
                <p className="pt-1" style={{ color: 'var(--text-muted)' }}>
                  {result.limitations}
                </p>
                {result.record_id && (
                  <p className="text-[11px] pt-1 font-semibold flex items-center gap-1 text-emerald-600">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Persisted in Twin Scenarios Table as Record #{result.record_id}
                  </p>
                )}
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
