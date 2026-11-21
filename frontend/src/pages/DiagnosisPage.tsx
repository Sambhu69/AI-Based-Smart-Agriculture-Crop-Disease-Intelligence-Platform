import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  Cpu,
  FileImage,
  Info,
  Leaf,
  RefreshCw,
  ShieldAlert,
  Trash2,
  Upload,
} from 'lucide-react';
import { useAppContext } from '../context/AppContext';
import { getDiseaseKnowledge } from '../data/diseaseKnowledgeBase';
import { useFarmDetail, usePredictDiseaseMutation } from '../hooks/useAgriQueries';
import { ProvenanceBadge } from '../components/ui/ProvenanceBadge';
import { Button, Card, ErrorAlert } from '../components/ui/Primitives';
import type { DiseasePredictionResponse } from '../types/api';

const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/bmp'];
const MAX_BYTES = 10 * 1024 * 1024; // 10 MB

export const DiagnosisPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { selectedFarmId } = useAppContext();
  const { data: farmDetail } = useFarmDetail(selectedFarmId);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imgDimensions, setImgDimensions] = useState<{ w: number; h: number } | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const [plotId, setPlotId] = useState<number | null>(() => {
    const p = searchParams.get('plotId');
    return p ? Number(p) : null;
  });
  const [topK, setTopK] = useState<number>(3);
  const [result, setResult] = useState<DiseasePredictionResponse | null>(null);

  const predictMutation = usePredictDiseaseMutation();

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const handleFileSelection = (file: File | null | undefined) => {
    setValidationError(null);
    if (!file) return;

    if (!ALLOWED_TYPES.includes(file.type)) {
      setValidationError(
        `Unsupported file type "${file.type || 'unknown'}". Please select a JPEG, PNG, WebP, or BMP leaf photograph.`
      );
      return;
    }

    if (file.size > MAX_BYTES) {
      setValidationError(
        `File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds the 10 MB maximum upload limit.`
      );
      return;
    }

    if (file.size === 0) {
      setValidationError('The selected image file is empty (0 bytes).');
      return;
    }

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    const objectUrl = URL.createObjectURL(file);
    setSelectedFile(file);
    setPreviewUrl(objectUrl);
    setResult(null);

    const img = new Image();
    img.onload = () => {
      setImgDimensions({ w: img.naturalWidth, h: img.naturalHeight });
    };
    img.src = objectUrl;
  };

  const clearSelection = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(null);
    setPreviewUrl(null);
    setImgDimensions(null);
    setValidationError(null);
    setResult(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleRunDiagnosis = async () => {
    if (!selectedFile) {
      setValidationError('Please select a crop leaf image before running diagnosis.');
      return;
    }
    setValidationError(null);
    try {
      const res = await predictMutation.mutateAsync({
        file: selectedFile,
        plotId: plotId || null,
        topK,
      });
      setResult(res);
    } catch {
      // handled by predictMutation.error
    }
  };

  const primary = result?.primary_prediction;
  const kb = primary ? getDiseaseKnowledge(primary.class_name) : null;

  return (
    <div className="space-y-5">
      {/* Header Banner */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <ProvenanceBadge type="predicted" />
              <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                COMPUTER VISION PATHOLOGY • RESNET-50
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-extrabold font-display">
              Crop Leaf Disease Diagnostic Studio
            </h2>
            <p className="text-xs sm:text-sm" style={{ color: 'var(--text-secondary)' }}>
              Upload or capture a leaf photograph (Tomato, Potato, Bell Pepper) for instant
              15-class ResNet-50 softmax classification and agronomic intervention guidance.
            </p>
          </div>
        </div>
      </Card>

      {/* Main Two-Column Responsive Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left 5 Cols: Image Upload, Preview & Inference Controls */}
        <div className="lg:col-span-5 space-y-4">
          <Card padding="md" className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm sm:text-base font-bold font-display flex items-center gap-2">
                <Camera className="w-4 h-4 text-emerald-600" />
                <span>1. Select or Capture Leaf Photo</span>
              </h3>
              {selectedFile && (
                <button
                  type="button"
                  onClick={clearSelection}
                  className="text-xs font-semibold text-red-600 dark:text-red-400 inline-flex items-center gap-1 hover:underline"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Remove
                </button>
              )}
            </div>

            {/* Hidden Native File Input (Supports mobile camera/photo picker) */}
            <input
              ref={fileInputRef}
              id="leaf-image-upload"
              type="file"
              accept="image/jpeg,image/png,image/webp,image/bmp"
              onChange={(e) => handleFileSelection(e.target.files?.[0])}
              className="sr-only"
            />

            {!previewUrl ? (
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  handleFileSelection(e.dataTransfer.files?.[0]);
                }}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
                style={{
                  borderColor: isDragging ? 'var(--brand-primary)' : 'var(--border-strong)',
                  backgroundColor: isDragging ? 'var(--brand-soft)' : 'var(--bg-subtle)',
                }}
                className="border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center cursor-pointer transition-colors flex flex-col items-center justify-center min-h-[220px]"
              >
                <div
                  className="w-12 h-12 rounded-2xl flex items-center justify-center mb-3"
                  style={{
                    backgroundColor: 'var(--bg-surface)',
                    color: 'var(--brand-primary)',
                  }}
                >
                  <Upload className="w-6 h-6" />
                </div>
                <p className="text-sm font-bold mb-1">
                  Tap to choose photo or drag & drop leaf image
                </p>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  Supports JPEG, PNG, WebP, BMP • Maximum 10 MB
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <div
                  className="relative rounded-2xl overflow-hidden border bg-black/5 flex items-center justify-center max-h-80"
                  style={{ borderColor: 'var(--border-default)' }}
                >
                  <img
                    src={previewUrl}
                    alt={`Selected leaf preview: ${selectedFile?.name || 'Leaf'}`}
                    className="max-h-80 w-auto object-contain"
                  />
                </div>

                {/* File Telemetry Bar */}
                <div className="p-3 rounded-xl surface-subtle text-xs flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <FileImage className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span className="font-semibold truncate">{selectedFile?.name}</span>
                  </div>
                  <div className="text-[11px] tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                    {imgDimensions ? `${imgDimensions.w}×${imgDimensions.h}px • ` : ''}
                    {selectedFile ? `${(selectedFile.size / 1024).toFixed(1)} KB` : ''}
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Replace Photo
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    leftIcon={<Trash2 className="w-3.5 h-3.5" />}
                    onClick={clearSelection}
                  >
                    Clear
                  </Button>
                </div>
              </div>
            )}

            {validationError && <ErrorAlert title="File Validation Error" message={validationError} />}

            {/* Inference Parameters */}
            <div className="pt-3 border-t space-y-3" style={{ borderColor: 'var(--border-default)' }}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label htmlFor="diag-plot-select" className="block text-xs font-bold mb-1">
                    Link to Farm Plot (Optional)
                  </label>
                  <select
                    id="diag-plot-select"
                    value={plotId ?? ''}
                    onChange={(e) => setPlotId(e.target.value ? Number(e.target.value) : null)}
                    className="input-field text-xs"
                  >
                    <option value="">Unlinked Inspection</option>
                    {farmDetail?.plots?.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.crop_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="diag-topk-select" className="block text-xs font-bold mb-1">
                    Top-K Ranked Classes
                  </label>
                  <select
                    id="diag-topk-select"
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="input-field text-xs"
                  >
                    <option value={3}>Top 3 Candidates</option>
                    <option value={5}>Top 5 Candidates</option>
                    <option value={10}>Top 10 Candidates</option>
                  </select>
                </div>
              </div>

              <Button
                type="button"
                variant="primary"
                size="lg"
                className="w-full"
                disabled={!selectedFile}
                isLoading={predictMutation.isPending}
                leftIcon={<Leaf className="w-5 h-5" />}
                onClick={handleRunDiagnosis}
              >
                {predictMutation.isPending
                  ? 'Running ResNet-50 Inference…'
                  : 'Run Disease Diagnosis'}
              </Button>
            </div>
          </Card>

          {/* Scientific Generalization Disclaimer */}
          <Card padding="sm" className="border-amber-500/30 bg-amber-500/5">
            <div className="flex items-start gap-2.5 text-xs">
              <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div style={{ color: 'var(--text-secondary)' }}>
                <strong className="block text-amber-800 dark:text-amber-300 mb-0.5">
                  Laboratory vs. Field Generalization Notice
                </strong>
                This ResNet-50 classifier was trained on standardized PlantVillage leaf imagery.
                Real-world field photographs with complex soil backgrounds, dew, or multi-pathogen
                co-infections should be corroborated with physical scouting.
              </div>
            </div>
          </Card>
        </div>

        {/* Right 7 Cols: Diagnosis Results & Agronomic Treatment Protocol */}
        <div className="lg:col-span-7 space-y-4">
          {predictMutation.isError && (
            <ErrorAlert
              title="Disease Classification Failed"
              message={
                predictMutation.error instanceof Error
                  ? predictMutation.error.message
                  : 'Error executing POST /api/v1/predict/disease'
              }
              onRetry={handleRunDiagnosis}
            />
          )}

          {!result ? (
            <Card padding="lg" className="min-h-[340px] flex flex-col items-center justify-center text-center">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
                style={{ backgroundColor: 'var(--brand-soft)', color: 'var(--brand-primary)' }}
              >
                <Leaf className="w-7 h-7" />
              </div>
              <h3 className="text-base sm:text-lg font-bold font-display mb-1">
                Ready for Leaf Pathology Inspection
              </h3>
              <p className="text-xs sm:text-sm max-w-md" style={{ color: 'var(--text-secondary)' }}>
                Select a leaf image on the left and tap <strong>Run Disease Diagnosis</strong> to
                execute live PyTorch ResNet-50 classification via{' '}
                <code>POST /api/v1/predict/disease</code>.
              </p>
            </Card>
          ) : (
            kb &&
            primary && (
              <>
                {/* 1. Primary Classification Result Card */}
                <Card padding="lg" className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <ProvenanceBadge type={result.epistemic_type} size="md" />
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold uppercase ${
                          kb.severity === 'None'
                            ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                            : kb.severity === 'Moderate'
                            ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300'
                            : 'bg-red-500/15 text-red-700 dark:text-red-300'
                        }`}
                      >
                        {kb.statusTag}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-xs tabular-nums" style={{ color: 'var(--text-muted)' }}>
                      <Cpu className="w-3.5 h-3.5" />
                      <span>
                        {result.model_architecture} v{result.model_version} •{' '}
                        {result.inference_device.toUpperCase()} •{' '}
                        {result.inference_time_ms.toFixed(1)} ms
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
                    <div>
                      <h3 className="text-xl sm:text-2xl font-extrabold font-display">
                        {kb.displayName}
                      </h3>
                      <p className="text-xs sm:text-sm italic" style={{ color: 'var(--text-secondary)' }}>
                        Pathogen / Species: {kb.scientificName}
                      </p>
                    </div>
                    <div className="text-left sm:text-right">
                      <span className="text-xs uppercase font-bold block" style={{ color: 'var(--text-muted)' }}>
                        Softmax Confidence
                      </span>
                      <span className="text-2xl sm:text-3xl font-extrabold font-display tabular-nums text-emerald-600 dark:text-emerald-400">
                        {primary.confidence_pct}
                      </span>
                    </div>
                  </div>

                  {/* Confidence Progress Bar */}
                  <div className="w-full h-3 rounded-full overflow-hidden surface-subtle">
                    <div
                      className="h-full rounded-full transition-all duration-300"
                      style={{
                        width: `${Math.min(100, primary.confidence * 100).toFixed(1)}%`,
                        backgroundColor:
                          kb.severity === 'None'
                            ? '#10b981'
                            : kb.severity === 'Moderate'
                            ? '#f59e0b'
                            : '#ef4444',
                      }}
                    />
                  </div>

                  {/* Symptom Pattern Box */}
                  <div className="p-3.5 rounded-xl surface-subtle text-xs sm:text-sm space-y-1">
                    <div className="font-bold text-xs uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                      Characteristic Symptom Pattern
                    </div>
                    <p>{kb.overview}</p>
                  </div>

                  {result.record_id && (
                    <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                      Logged in Provenance Audit Ledger as Prediction Record #{result.record_id}
                    </p>
                  )}
                </Card>

                {/* 2. Agronomic Treatment Advisory Card (Explicit RECOMMENDED Provenance) */}
                <Card padding="md" className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className="text-base font-bold font-display flex items-center gap-2">
                      {kb.severity === 'None' ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                      ) : (
                        <ShieldAlert className="w-5 h-5 text-amber-600" />
                      )}
                      <span>Agronomic Management & Containment Protocol</span>
                    </h4>
                    <ProvenanceBadge type="recommended" />
                  </div>

                  <ul className="space-y-2 text-xs sm:text-sm pl-5 list-disc">
                    {kb.treatments.map((step, idx) => (
                      <li key={idx} className="leading-relaxed">
                        {step}
                      </li>
                    ))}
                  </ul>
                </Card>

                {/* 3. Ranked Top-K Class Probabilities */}
                <Card padding="md" className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm sm:text-base font-bold font-display">
                      Top-{result.top_k_predictions.length} Softmax Class Distribution
                    </h4>
                    <ProvenanceBadge type="predicted" />
                  </div>

                  <div className="space-y-2.5">
                    {result.top_k_predictions.map((item) => {
                      const entryKb = getDiseaseKnowledge(item.class_name);
                      const pct = Math.min(100, item.confidence * 100);
                      return (
                        <div key={item.class_name} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold">
                              #{item.rank} {entryKb.displayName}
                            </span>
                            <span className="font-bold tabular-nums">{item.confidence_pct}</span>
                          </div>
                          <div className="w-full h-2 rounded-full overflow-hidden surface-subtle">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${pct.toFixed(1)}%`,
                                backgroundColor:
                                  item.rank === 1 ? 'var(--brand-primary)' : '#64748b',
                              }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              </>
            )
          )}
        </div>
      </div>
    </div>
  );
};
