import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle2,
  Compass,
  Droplets,
  FlaskConical,
  Sprout,
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
import { useFarmDetail, useRecommendAgronomyMutation } from '../hooks/useAgriQueries';
import { ProvenanceBadge } from '../components/ui/ProvenanceBadge';
import { Button, Card, ErrorAlert } from '../components/ui/Primitives';
import type { CropIrrigationAdvisoryResponse } from '../types/api';

const CANDIDATE_CROPS = ['Tomato', 'Potato', 'Pepper', 'Maize', 'Rice'];

export const RecommendationsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { selectedFarmId } = useAppContext();
  const { data: farmDetail } = useFarmDetail(selectedFarmId);

  const [cropType, setCropType] = useState(searchParams.get('crop') || 'Tomato');
  const [soilPh, setSoilPh] = useState('6.4');
  const [temperatureC, setTemperatureC] = useState('23.5');
  const [soilMoisturePct, setSoilMoisturePct] = useState('58.0');
  const [precipitationMm, setPrecipitationMm] = useState('2.0');
  const [plotId, setPlotId] = useState<number | null>(() => {
    const p = searchParams.get('plotId');
    return p ? Number(p) : null;
  });

  const [formError, setFormError] = useState<string | null>(null);
  const [result, setResult] = useState<CropIrrigationAdvisoryResponse | null>(null);

  const recommendMutation = useRecommendAgronomyMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    const ph = Number(soilPh);
    const temp = Number(temperatureC);
    const moist = Number(soilMoisturePct);
    const rain = Number(precipitationMm);

    if (ph < 3 || ph > 10) {
      setFormError('Soil pH must be between 3.0 and 10.0.');
      return;
    }
    if (temp < -10 || temp > 55) {
      setFormError('Temperature must be between -10°C and 55°C.');
      return;
    }
    if (moist < 0 || moist > 100) {
      setFormError('Soil moisture must be between 0% and 100%.');
      return;
    }

    try {
      const res = await recommendMutation.mutateAsync({
        crop_type: cropType,
        soil_ph: ph,
        temperature_c: temp,
        soil_moisture_pct: moist,
        precipitation_mm: rain,
        plot_id: plotId || null,
      });
      setResult(res);
    } catch {
      // handled by mutation error
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <Card padding="md">
        <div className="flex flex-wrap items-center gap-2 mb-1">
          <ProvenanceBadge type="recommended" />
          <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
            PRESCRIPTIVE AGRONOMY ENGINE • CROP, IRRIGATION & SOIL pH
          </span>
        </div>
        <h2 className="text-lg sm:text-xl font-extrabold font-display">
          Crop Suitability, Irrigation & Fertilizer Advisory
        </h2>
        <p className="text-xs sm:text-sm" style={{ color: 'var(--text-secondary)' }}>
          Evaluate multi-crop suitability scores and compute prescriptive water and soil amendment
          guidance via <code>POST /api/v1/recommend/crop-irrigation</code>.
        </p>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Input Form (Left 5 Cols) */}
        <Card padding="md" className="lg:col-span-5 self-start">
          <form onSubmit={handleSubmit} className="space-y-4">
            <h3 className="text-base font-bold font-display flex items-center gap-2">
              <Compass className="w-4 h-4 text-emerald-600" />
              <span>Field Conditions Input</span>
            </h3>

            {formError && <ErrorAlert message={formError} />}
            {recommendMutation.isError && (
              <ErrorAlert
                message={
                  recommendMutation.error instanceof Error
                    ? recommendMutation.error.message
                    : 'Advisory request failed'
                }
              />
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor="adv-crop" className="block text-xs font-bold mb-1">
                  Target Crop
                </label>
                <select
                  id="adv-crop"
                  value={cropType}
                  onChange={(e) => setCropType(e.target.value)}
                  className="input-field"
                >
                  {CANDIDATE_CROPS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="adv-plot" className="block text-xs font-bold mb-1">
                  Link to Plot (Optional)
                </label>
                <select
                  id="adv-plot"
                  value={plotId ?? ''}
                  onChange={(e) => setPlotId(e.target.value ? Number(e.target.value) : null)}
                  className="input-field"
                >
                  <option value="">Unlinked Advisory</option>
                  {farmDetail?.plots?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.crop_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="adv-ph" className="block text-xs font-bold mb-1">
                  Soil pH (3.0–10.0) <span className="text-red-500">*</span>
                </label>
                <input
                  id="adv-ph"
                  type="number"
                  step="0.1"
                  min="3"
                  max="10"
                  required
                  value={soilPh}
                  onChange={(e) => setSoilPh(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label htmlFor="adv-temp" className="block text-xs font-bold mb-1">
                  Temperature (°C) <span className="text-red-500">*</span>
                </label>
                <input
                  id="adv-temp"
                  type="number"
                  step="0.5"
                  min="-10"
                  max="55"
                  required
                  value={temperatureC}
                  onChange={(e) => setTemperatureC(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label htmlFor="adv-moisture" className="block text-xs font-bold mb-1">
                  Soil Moisture (%) <span className="text-red-500">*</span>
                </label>
                <input
                  id="adv-moisture"
                  type="number"
                  step="1"
                  min="0"
                  max="100"
                  required
                  value={soilMoisturePct}
                  onChange={(e) => setSoilMoisturePct(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label htmlFor="adv-rain" className="block text-xs font-bold mb-1">
                  Recent / Forecast Rain (mm)
                </label>
                <input
                  id="adv-rain"
                  type="number"
                  step="0.5"
                  min="0"
                  value={precipitationMm}
                  onChange={(e) => setPrecipitationMm(e.target.value)}
                  className="input-field"
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              isLoading={recommendMutation.isPending}
              leftIcon={<Compass className="w-5 h-5" />}
            >
              Generate Agronomic Advisory
            </Button>
          </form>
        </Card>

        {/* Advisory Output (Right 7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          {!result ? (
            <Card padding="lg" className="min-h-[340px] flex flex-col items-center justify-center text-center">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
                style={{ backgroundColor: 'var(--brand-soft)', color: 'var(--brand-primary)' }}
              >
                <Compass className="w-7 h-7" />
              </div>
              <h3 className="text-base sm:text-lg font-bold font-display mb-1">
                Configure Soil & Weather Parameters
              </h3>
              <p className="text-xs sm:text-sm max-w-md" style={{ color: 'var(--text-secondary)' }}>
                Submit field measurements on the left to rank candidate crops and receive irrigation
                and nutrient management recommendations.
              </p>
            </Card>
          ) : (
            <>
              {/* 1. Irrigation & Soil pH Action Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Card padding="md" className="space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase flex items-center gap-1.5 text-sky-700 dark:text-sky-300">
                      <Droplets className="w-4 h-4" />
                      Irrigation Schedule ({result.crop_type})
                    </span>
                    <ProvenanceBadge type="recommended" />
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
                      Urgency Level:
                    </span>
                    <span className="text-base font-extrabold font-display">
                      {result.irrigation_recommendation.urgency}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl surface-subtle text-xs">
                    <span className="block font-bold mb-0.5">
                      Water Dose: {result.irrigation_recommendation.estimated_water_liters_per_m2}{' '}
                      L/m²
                    </span>
                    <p style={{ color: 'var(--text-secondary)' }}>
                      {result.irrigation_recommendation.action}
                    </p>
                  </div>
                </Card>

                <Card padding="md" className="space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase flex items-center gap-1.5 text-amber-700 dark:text-amber-300">
                      <FlaskConical className="w-4 h-4" />
                      Nutrient & pH Guidance
                    </span>
                    <ProvenanceBadge type="recommended" />
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
                      Soil pH Status:
                    </span>
                    <span className="text-base font-extrabold font-display">
                      {result.fertilizer_recommendation.soil_ph_status}
                    </span>
                  </div>
                  <ul className="space-y-1 text-xs pl-4 list-disc" style={{ color: 'var(--text-secondary)' }}>
                    {result.fertilizer_recommendation.guidance_notes.map((n, idx) => (
                      <li key={idx}>{n}</li>
                    ))}
                  </ul>
                </Card>
              </div>

              {/* 2. Ranked Crop Suitability Chart & Breakdown */}
              <Card padding="md" className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="text-base font-bold font-display">
                      Multi-Crop Suitability Ranking
                    </h3>
                    <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                      Composite agronomic match across temperature (40%), moisture (35%), and pH
                      (25%)
                    </p>
                  </div>
                  <ProvenanceBadge type="recommended" />
                </div>

                <div className="h-52 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={result.crop_suitability_ranking}
                      margin={{ top: 8, right: 12, left: -16, bottom: 4 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                      <XAxis dataKey="crop_type" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                      <Tooltip
                        cursor={{ fill: 'rgba(148, 163, 184, 0.12)' }}
                        contentStyle={{
                          backgroundColor: 'var(--bg-elevated)',
                          borderColor: 'var(--border-strong)',
                          borderRadius: '0.75rem',
                          fontSize: '12px',
                          color: 'var(--text-primary)',
                          boxShadow: 'var(--shadow-modal)',
                        }}
                        labelStyle={{ color: 'var(--text-primary)', fontWeight: 700 }}
                        itemStyle={{ color: 'var(--text-secondary)' }}
                      />
                      <Bar dataKey="suitability_score" name="Suitability Score" radius={[6, 6, 0, 0]}>
                        {result.crop_suitability_ranking.map((entry, idx) => (
                          <Cell
                            key={`cell-${idx}`}
                            fill={
                              entry.suitability_score >= 0.75
                                ? '#059669'
                                : entry.suitability_score >= 0.5
                                ? '#d97706'
                                : '#dc2626'
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Suitability Cards */}
                <div className="space-y-2.5">
                  {result.crop_suitability_ranking.map((item, idx) => (
                    <div key={item.crop_type} className="p-3.5 rounded-xl surface-subtle space-y-1.5">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-extrabold px-2 py-0.5 rounded-md bg-emerald-600 text-white">
                            #{idx + 1}
                          </span>
                          <span className="font-bold text-sm flex items-center gap-1.5">
                            <Sprout className="w-4 h-4 text-emerald-600" />
                            {item.crop_type}
                          </span>
                          <span className="text-xs font-semibold px-2 py-0.5 rounded-full border" style={{ borderColor: 'var(--border-strong)' }}>
                            {item.suitability}
                          </span>
                        </div>
                        <span className="text-sm font-extrabold tabular-nums">
                          {(item.suitability_score * 100).toFixed(1)}% match
                        </span>
                      </div>
                      <ul className="text-xs pl-4 list-disc space-y-0.5" style={{ color: 'var(--text-secondary)' }}>
                        {item.reasons.map((r, rIdx) => (
                          <li key={rIdx}>{r}</li>
                        ))}
                      </ul>
                      <p className="text-[11px] italic" style={{ color: 'var(--text-muted)' }}>
                        {item.crop_notes}
                      </p>
                    </div>
                  ))}
                </div>
              </Card>

              {/* 3. Explicit Assumptions & Limitations */}
              <Card padding="md" className="space-y-2 text-xs">
                <div className="font-bold flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  <span>Agronomic Assumptions & Limitations</span>
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
                    Logged as Provenance Record #{result.record_id}
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
