import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BarChart3, Calculator, Info, Scale, Sprout } from 'lucide-react';
import { useAppContext } from '../context/AppContext';
import { useFarmDetail, usePredictYieldMutation } from '../hooks/useAgriQueries';
import { ProvenanceBadge } from '../components/ui/ProvenanceBadge';
import { Button, Card, ErrorAlert } from '../components/ui/Primitives';
import type { YieldPredictionResponse } from '../types/api';

const SUPPORTED_CROPS = ['Tomato', 'Potato', 'Pepper', 'Maize', 'Rice'];

export const YieldPredictionPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { selectedFarmId } = useAppContext();
  const { data: farmDetail } = useFarmDetail(selectedFarmId);

  const [cropType, setCropType] = useState(searchParams.get('crop') || 'Tomato');
  const [harvestYear, setHarvestYear] = useState('2025');
  const [areaHectares, setAreaHectares] = useState(searchParams.get('area') || '2.0');
  const [soilPh, setSoilPh] = useState('6.4');
  const [moisturePct, setMoisturePct] = useState('28.0');
  const [nitrogenMgKg, setNitrogenMgKg] = useState('42.0');
  const [organicMatterPct, setOrganicMatterPct] = useState('2.6');
  const [plotId, setPlotId] = useState<number | null>(() => {
    const p = searchParams.get('plotId');
    return p ? Number(p) : null;
  });

  const [formError, setFormError] = useState<string | null>(null);
  const [result, setResult] = useState<YieldPredictionResponse | null>(null);

  const yieldMutation = usePredictYieldMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const area = Number(areaHectares);
    const year = Number(harvestYear);
    const ph = Number(soilPh);
    const moist = Number(moisturePct);
    const nit = Number(nitrogenMgKg);
    const om = Number(organicMatterPct);

    if (Number.isNaN(area) || area <= 0) {
      setFormError('Cultivated area must be greater than 0 hectares.');
      return;
    }
    if (Number.isNaN(ph) || ph < 3 || ph > 10) {
      setFormError('Soil pH must be between 3.0 and 10.0.');
      return;
    }

    try {
      const res = await yieldMutation.mutateAsync({
        crop_type: cropType,
        harvest_year: year,
        area_hectares: area,
        ph,
        moisture_pct: moist,
        nitrogen_mg_kg: nit,
        organic_matter_pct: om,
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
          <ProvenanceBadge type="predicted" />
          <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
            TABULAR ML FORECASTER • RIDGE REGRESSION BASELINE
          </span>
        </div>
        <h2 className="text-lg sm:text-xl font-extrabold font-display">
          Crop Yield Prediction Studio
        </h2>
        <p className="text-xs sm:text-sm" style={{ color: 'var(--text-secondary)' }}>
          Forecast expected harvest yield (kg/ha and total projected output) from cultivated area
          and measured soil chemistry parameters via <code>POST /api/v1/predict/yield</code>.
        </p>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Form (Left 6 Cols) */}
        <Card padding="md" className="lg:col-span-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <h3 className="text-base font-bold font-display flex items-center gap-2">
              <Calculator className="w-4 h-4 text-emerald-600" />
              <span>Crop & Soil Input Parameters</span>
            </h3>

            {formError && <ErrorAlert message={formError} />}
            {yieldMutation.isError && (
              <ErrorAlert
                message={
                  yieldMutation.error instanceof Error
                    ? yieldMutation.error.message
                    : 'Prediction failed'
                }
              />
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label htmlFor="yield-crop" className="block text-xs font-bold mb-1">
                  Crop Species <span className="text-red-500">*</span>
                </label>
                <select
                  id="yield-crop"
                  value={cropType}
                  onChange={(e) => setCropType(e.target.value)}
                  className="input-field"
                >
                  {SUPPORTED_CROPS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="yield-area" className="block text-xs font-bold mb-1">
                  Cultivated Area (Hectares) <span className="text-red-500">*</span>
                </label>
                <input
                  id="yield-area"
                  type="number"
                  step="0.1"
                  min="0.1"
                  required
                  value={areaHectares}
                  onChange={(e) => setAreaHectares(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label htmlFor="yield-year" className="block text-xs font-bold mb-1">
                  Target Harvest Year
                </label>
                <input
                  id="yield-year"
                  type="number"
                  min="2000"
                  max="2100"
                  value={harvestYear}
                  onChange={(e) => setHarvestYear(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label htmlFor="yield-plot" className="block text-xs font-bold mb-1">
                  Link to Plot (Optional)
                </label>
                <select
                  id="yield-plot"
                  value={plotId ?? ''}
                  onChange={(e) => setPlotId(e.target.value ? Number(e.target.value) : null)}
                  className="input-field"
                >
                  <option value="">Unlinked Forecast</option>
                  {farmDetail?.plots?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.crop_type})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="pt-2 border-t" style={{ borderColor: 'var(--border-default)' }}>
              <span className="text-xs font-bold uppercase tracking-wider block mb-2.5" style={{ color: 'var(--text-muted)' }}>
                Soil Chemistry Profile
              </span>
              <div className="grid grid-cols-2 gap-3.5">
                <div>
                  <label htmlFor="yield-ph" className="block text-xs font-bold mb-1">
                    Soil pH (3.0–10.0)
                  </label>
                  <input
                    id="yield-ph"
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
                  <label htmlFor="yield-moisture" className="block text-xs font-bold mb-1">
                    Soil Moisture (%)
                  </label>
                  <input
                    id="yield-moisture"
                    type="number"
                    step="0.5"
                    min="0"
                    max="100"
                    value={moisturePct}
                    onChange={(e) => setMoisturePct(e.target.value)}
                    className="input-field"
                  />
                </div>

                <div>
                  <label htmlFor="yield-nitrogen" className="block text-xs font-bold mb-1">
                    Available Nitrogen (mg/kg)
                  </label>
                  <input
                    id="yield-nitrogen"
                    type="number"
                    step="1"
                    min="0"
                    value={nitrogenMgKg}
                    onChange={(e) => setNitrogenMgKg(e.target.value)}
                    className="input-field"
                  />
                </div>

                <div>
                  <label htmlFor="yield-om" className="block text-xs font-bold mb-1">
                    Organic Matter (%)
                  </label>
                  <input
                    id="yield-om"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={organicMatterPct}
                    onChange={(e) => setOrganicMatterPct(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              isLoading={yieldMutation.isPending}
              leftIcon={<BarChart3 className="w-5 h-5" />}
            >
              Compute Yield Forecast
            </Button>
          </form>
        </Card>

        {/* Output Results (Right 6 Cols) */}
        <div className="lg:col-span-6 space-y-4">
          {!result ? (
            <Card padding="lg" className="min-h-[320px] flex flex-col items-center justify-center text-center">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
                style={{ backgroundColor: 'var(--brand-soft)', color: 'var(--brand-primary)' }}
              >
                <Scale className="w-7 h-7" />
              </div>
              <h3 className="text-base sm:text-lg font-bold font-display mb-1">
                No Yield Forecast Generated Yet
              </h3>
              <p className="text-xs sm:text-sm max-w-md" style={{ color: 'var(--text-secondary)' }}>
                Enter your cultivated area and soil profile on the left and tap{' '}
                <strong>Compute Yield Forecast</strong> to query the trained Stage 6 yield baseline.
              </p>
            </Card>
          ) : (
            <Card padding="lg" className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <ProvenanceBadge type={result.epistemic_type} size="md" />
                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-full surface-subtle">
                    Model: {result.model_name}
                  </span>
                </div>
                <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                  Harvest Year {result.harvest_year}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div className="p-4 rounded-2xl surface-subtle">
                  <span className="text-xs font-bold uppercase block" style={{ color: 'var(--text-secondary)' }}>
                    Predicted Yield Intensity
                  </span>
                  <div className="text-2xl sm:text-3xl font-extrabold font-display tabular-nums mt-1 text-emerald-700 dark:text-emerald-400">
                    {result.predicted_yield_kg_per_ha.toLocaleString()} kg/ha
                  </div>
                  <span className="text-xs block mt-1" style={{ color: 'var(--text-muted)' }}>
                    ≈ {(result.predicted_yield_kg_per_ha / 1000).toFixed(2)} tonnes / hectare
                  </span>
                </div>

                <div className="p-4 rounded-2xl surface-subtle">
                  <span className="text-xs font-bold uppercase block" style={{ color: 'var(--text-secondary)' }}>
                    Total Projected Harvest ({result.area_hectares} ha)
                  </span>
                  <div className="text-2xl sm:text-3xl font-extrabold font-display tabular-nums mt-1">
                    {result.total_projected_yield_kg.toLocaleString()} kg
                  </div>
                  <span className="text-xs block mt-1" style={{ color: 'var(--text-muted)' }}>
                    ≈ {(result.total_projected_yield_kg / 1000).toFixed(2)} metric tonnes total
                  </span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl surface-subtle text-xs space-y-1.5">
                <div className="font-bold flex items-center gap-1.5">
                  <Sprout className="w-4 h-4 text-emerald-600" />
                  <span>Input Snapshot Summary</span>
                </div>
                <p style={{ color: 'var(--text-secondary)' }}>
                  Crop: <strong>{result.crop_type}</strong> • Area:{' '}
                  <strong>{result.area_hectares} ha</strong> • Soil pH: <strong>{soilPh}</strong> •
                  Moisture: <strong>{moisturePct}%</strong> • Nitrogen:{' '}
                  <strong>{nitrogenMgKg} mg/kg</strong> • Organic Matter:{' '}
                  <strong>{organicMatterPct}%</strong>
                </p>
              </div>

              <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/5 text-xs flex items-start gap-2.5">
                <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div style={{ color: 'var(--text-secondary)' }}>
                  <strong className="block text-amber-800 dark:text-amber-300 mb-0.5">
                    Model Scope & Agronomic Caveat
                  </strong>
                  Predictions are derived from the Stage 6 tabular yield baseline trained on
                  regional agro-climatic profiles. Realized harvest yields depend on cultivar
                  genetics, pest/disease suppression, and intra-season extreme weather events.
                </div>
              </div>

              {result.record_id && (
                <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                  Persisted in Provenance Audit Log as Record #{result.record_id}
                </p>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
