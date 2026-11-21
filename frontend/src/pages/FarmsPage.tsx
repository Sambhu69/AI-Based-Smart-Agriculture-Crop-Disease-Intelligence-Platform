import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Calendar,
  FolderKanban,
  Layers,
  MapPin,
  Plus,
  Sprout,
} from 'lucide-react';
import { useAppContext } from '../context/AppContext';
import {
  useCreateFarmMutation,
  useCreatePlotMutation,
  useFarmDetail,
  useFarmsList,
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

const SUPPORTED_CROPS = ['Tomato', 'Potato', 'Pepper', 'Maize', 'Rice'];

export const FarmsPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectedFarmId, setSelectedFarmId } = useAppContext();

  const {
    data: farms,
    isLoading: farmsLoading,
    isError: farmsError,
    error: farmsErrObj,
    refetch: refetchFarms,
  } = useFarmsList();

  useEffect(() => {
    if (!selectedFarmId && farms && farms.length > 0) {
      setSelectedFarmId(farms[0].id);
    }
  }, [farms, selectedFarmId, setSelectedFarmId]);

  const activeFarmId = selectedFarmId ?? (farms && farms[0] ? farms[0].id : null);
  const {
    data: farmDetail,
    isLoading: detailLoading,
    refetch: refetchDetail,
  } = useFarmDetail(activeFarmId);

  // Create Farm Modal State
  const [farmModalOpen, setFarmModalOpen] = useState(false);
  const [farmName, setFarmName] = useState('');
  const [farmLocation, setFarmLocation] = useState('');
  const [farmFormError, setFarmFormError] = useState<string | null>(null);
  const createFarmMutation = useCreateFarmMutation();

  // Create Plot Modal State
  const [plotModalOpen, setPlotModalOpen] = useState(false);
  const [plotName, setPlotName] = useState('');
  const [plotCrop, setPlotCrop] = useState('Tomato');
  const [plotArea, setPlotArea] = useState('1.5');
  const [plotFormError, setPlotFormError] = useState<string | null>(null);
  const createPlotMutation = useCreatePlotMutation(activeFarmId ?? 0);

  const handleCreateFarm = async (e: React.FormEvent) => {
    e.preventDefault();
    setFarmFormError(null);
    const trimmed = farmName.trim();
    if (!trimmed) {
      setFarmFormError('Farm name is required.');
      return;
    }
    try {
      const created = await createFarmMutation.mutateAsync({
        name: trimmed,
        location: farmLocation.trim() || null,
      });
      setSelectedFarmId(created.id);
      setFarmName('');
      setFarmLocation('');
      setFarmModalOpen(false);
    } catch (err) {
      setFarmFormError(err instanceof Error ? err.message : 'Failed to create farm');
    }
  };

  const handleCreatePlot = async (e: React.FormEvent) => {
    e.preventDefault();
    setPlotFormError(null);
    if (!activeFarmId) {
      setPlotFormError('Please select a farm first.');
      return;
    }
    const trimmedName = plotName.trim();
    if (!trimmedName) {
      setPlotFormError('Plot name is required.');
      return;
    }
    const parsedArea = plotArea.trim() ? Number(plotArea) : null;
    if (parsedArea !== null && (Number.isNaN(parsedArea) || parsedArea < 0)) {
      setPlotFormError('Area must be a non-negative number in hectares.');
      return;
    }
    try {
      await createPlotMutation.mutateAsync({
        name: trimmedName,
        crop_type: plotCrop,
        area_hectares: parsedArea,
      });
      setPlotName('');
      setPlotArea('1.5');
      setPlotModalOpen(false);
      refetchDetail();
    } catch (err) {
      setPlotFormError(err instanceof Error ? err.message : 'Failed to create plot');
    }
  };

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <ProvenanceBadge type="observed" />
              <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                ASSET & PLOT REGISTRY
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-extrabold font-display">
              Farm & Plot Operations Management
            </h2>
            <p className="text-xs sm:text-sm" style={{ color: 'var(--text-secondary)' }}>
              Register physical farms, partition cultivated plots, and inspect plot-level field
              observations.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={() => setFarmModalOpen(true)}
            >
              Register Farm
            </Button>
            {activeFarmId && (
              <Button
                variant="secondary"
                leftIcon={<Sprout className="w-4 h-4" />}
                onClick={() => setPlotModalOpen(true)}
              >
                Add Plot
              </Button>
            )}
          </div>
        </div>
      </Card>

      {farmsError && (
        <ErrorAlert
          title="Could not load farms"
          message={farmsErrObj instanceof Error ? farmsErrObj.message : 'Error loading farms'}
          onRetry={() => refetchFarms()}
        />
      )}

      {/* Main Content Grid */}
      {farmsLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-4 space-y-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
          <div className="lg:col-span-8">
            <Skeleton className="h-64 w-full" />
          </div>
        </div>
      ) : !farms || farms.length === 0 ? (
        <EmptyState
          title="No Agricultural Farms Registered Yet"
          description="Create your first farm record to start organizing crop plots, recording field observations, and tracking model predictions."
          icon={<FolderKanban className="w-6 h-6" />}
          action={
            <Button leftIcon={<Plus className="w-4 h-4" />} onClick={() => setFarmModalOpen(true)}>
              Register First Farm
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Left 4 columns: Farms Directory List */}
          <div className="lg:col-span-4 space-y-3">
            <div className="flex items-center justify-between px-1">
              <h3 className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                Registered Farms ({farms.length})
              </h3>
            </div>
            <div className="space-y-2.5">
              {farms.map((farm) => {
                const isSelected = farm.id === activeFarmId;
                return (
                  <button
                    key={farm.id}
                    type="button"
                    onClick={() => setSelectedFarmId(farm.id)}
                    style={
                      isSelected
                        ? {
                            backgroundColor: 'var(--brand-soft)',
                            borderColor: 'var(--brand-primary)',
                          }
                        : {
                            backgroundColor: 'var(--bg-surface)',
                            borderColor: 'var(--border-default)',
                          }
                    }
                    className="w-full text-left p-4 rounded-2xl border transition-all flex items-start justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-bold font-display text-sm sm:text-base truncate">
                          {farm.name}
                        </span>
                        <span
                          className="text-[11px] px-2 py-0.5 rounded-full font-semibold"
                          style={{
                            backgroundColor: 'var(--bg-subtle)',
                            color: 'var(--text-secondary)',
                          }}
                        >
                          ID #{farm.id}
                        </span>
                      </div>
                      <div
                        className="flex items-center gap-1.5 text-xs mt-1"
                        style={{ color: 'var(--text-secondary)' }}
                      >
                        <MapPin className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate">{farm.location || 'Location not specified'}</span>
                      </div>
                      <div
                        className="flex items-center gap-1.5 text-[11px] mt-1.5"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        <Calendar className="w-3 h-3 shrink-0" />
                        <span>Registered {new Date(farm.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right 8 columns: Selected Farm Detail & Plots Grid */}
          <div className="lg:col-span-8">
            <Card padding="md" className="space-y-4">
              {detailLoading || !farmDetail ? (
                <div className="space-y-3">
                  <Skeleton className="h-12 w-1/2" />
                  <Skeleton className="h-32 w-full" />
                </div>
              ) : (
                <>
                  <div
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b"
                    style={{ borderColor: 'var(--border-default)' }}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-extrabold font-display">{farmDetail.name}</h3>
                        <ProvenanceBadge type="observed" />
                      </div>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                        {farmDetail.location
                          ? `Region / Location: ${farmDetail.location}`
                          : 'No regional location specified'}{' '}
                        • {farmDetail.plots.length} registered plot(s)
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="primary"
                      leftIcon={<Plus className="w-4 h-4" />}
                      onClick={() => setPlotModalOpen(true)}
                    >
                      New Plot
                    </Button>
                  </div>

                  {farmDetail.plots.length === 0 ? (
                    <EmptyState
                      title="No Cultivated Plots in This Farm"
                      description="Add a plot specifying the cultivated crop (e.g., Tomato, Potato, Pepper, Maize, Rice) and area in hectares."
                      icon={<Layers className="w-6 h-6" />}
                      action={
                        <Button
                          size="sm"
                          leftIcon={<Plus className="w-4 h-4" />}
                          onClick={() => setPlotModalOpen(true)}
                        >
                          Add First Plot
                        </Button>
                      }
                    />
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                      {farmDetail.plots.map((plot) => (
                        <div
                          key={plot.id}
                          className="p-4 rounded-2xl surface-subtle flex flex-col justify-between gap-3"
                        >
                          <div>
                            <div className="flex items-center justify-between gap-2 mb-1.5">
                              <span className="font-bold font-display text-sm sm:text-base flex items-center gap-1.5">
                                <Sprout className="w-4 h-4 text-emerald-600 shrink-0" />
                                {plot.name}
                              </span>
                              <span
                                className="text-[11px] font-bold px-2 py-0.5 rounded-full"
                                style={{
                                  backgroundColor: 'var(--brand-soft)',
                                  color: 'var(--brand-text)',
                                }}
                              >
                                {plot.crop_type}
                              </span>
                            </div>

                            <div
                              className="text-xs space-y-0.5"
                              style={{ color: 'var(--text-secondary)' }}
                            >
                              <div>
                                Plot ID: <strong className="tabular-nums">#{plot.id}</strong>
                              </div>
                              <div>
                                Cultivated Area:{' '}
                                <strong className="tabular-nums">
                                  {plot.area_hectares !== null
                                    ? `${plot.area_hectares} hectares`
                                    : 'Not specified'}
                                </strong>
                              </div>
                              <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                                Created {new Date(plot.created_at).toLocaleDateString()}
                              </div>
                            </div>
                          </div>

                          <div className="pt-2 border-t flex items-center justify-between gap-2" style={{ borderColor: 'var(--border-default)' }}>
                            <Button
                              size="sm"
                              variant="primary"
                              className="w-full"
                              onClick={() =>
                                navigate(`/farms/${farmDetail.id}/plots/${plot.id}`)
                              }
                            >
                              <span>Observations & Details</span>
                              <ArrowRight className="w-3.5 h-3.5 ml-1" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* =====================================================================
          MODAL 1: REGISTER NEW FARM (POST /api/v1/farms)
      ===================================================================== */}
      <ModalOrSheet
        isOpen={farmModalOpen}
        onClose={() => setFarmModalOpen(false)}
        title="Register Agricultural Farm"
        subtitle="Creates a persisted Farm record via POST /api/v1/farms"
      >
        <form onSubmit={handleCreateFarm} className="space-y-4">
          {farmFormError && <ErrorAlert message={farmFormError} />}
          <div>
            <label htmlFor="farm-name-input" className="block text-xs font-bold mb-1">
              Farm Name <span className="text-red-500">*</span>
            </label>
            <input
              id="farm-name-input"
              type="text"
              required
              maxLength={128}
              placeholder="e.g., Chitwan Valley Research Farm"
              value={farmName}
              onChange={(e) => setFarmName(e.target.value)}
              className="input-field"
            />
          </div>
          <div>
            <label htmlFor="farm-location-input" className="block text-xs font-bold mb-1">
              Geographic Region / Location (Optional)
            </label>
            <input
              id="farm-location-input"
              type="text"
              maxLength={256}
              placeholder="e.g., Chitwan, Terai Subtropical Zone"
              value={farmLocation}
              onChange={(e) => setFarmLocation(e.target.value)}
              className="input-field"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setFarmModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={createFarmMutation.isPending}
            >
              Create Farm
            </Button>
          </div>
        </form>
      </ModalOrSheet>

      {/* =====================================================================
          MODAL 2: ADD NEW PLOT (POST /api/v1/farms/{farm_id}/plots)
      ===================================================================== */}
      <ModalOrSheet
        isOpen={plotModalOpen}
        onClose={() => setPlotModalOpen(false)}
        title={`Add Plot to ${farmDetail?.name || 'Farm'}`}
        subtitle="Creates a cultivated plot record via POST /api/v1/farms/{farm_id}/plots"
      >
        <form onSubmit={handleCreatePlot} className="space-y-4">
          {plotFormError && <ErrorAlert message={plotFormError} />}
          <div>
            <label htmlFor="plot-name-input" className="block text-xs font-bold mb-1">
              Plot Identifier / Name <span className="text-red-500">*</span>
            </label>
            <input
              id="plot-name-input"
              type="text"
              required
              maxLength={128}
              placeholder="e.g., North Block A-1"
              value={plotName}
              onChange={(e) => setPlotName(e.target.value)}
              className="input-field"
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label htmlFor="plot-crop-select" className="block text-xs font-bold mb-1">
                Cultivated Crop <span className="text-red-500">*</span>
              </label>
              <select
                id="plot-crop-select"
                value={plotCrop}
                onChange={(e) => setPlotCrop(e.target.value)}
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
              <label htmlFor="plot-area-input" className="block text-xs font-bold mb-1">
                Area (Hectares)
              </label>
              <input
                id="plot-area-input"
                type="number"
                step="0.1"
                min="0"
                placeholder="1.5"
                value={plotArea}
                onChange={(e) => setPlotArea(e.target.value)}
                className="input-field"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setPlotModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={createPlotMutation.isPending}
            >
              Create Plot
            </Button>
          </div>
        </form>
      </ModalOrSheet>
    </div>
  );
};
