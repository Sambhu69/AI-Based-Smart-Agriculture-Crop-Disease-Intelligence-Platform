import { apiRequest } from './client';
import type {
  CropIrrigationAdvisoryRequest,
  CropIrrigationAdvisoryResponse,
  DiseasePredictionResponse,
  FarmCreateRequest,
  FarmDetailResponse,
  FarmResponse,
  FieldObservationCreateRequest,
  FieldObservationResponse,
  HistoryResponse,
  IntelligenceAssessmentRequest,
  IntelligenceAssessmentResponse,
  PlotCreateRequest,
  PlotResponse,
  SystemHealthResponse,
  TwinSimulationRequest,
  TwinSimulationResponse,
  YieldPredictionRequest,
  YieldPredictionResponse,
} from '../../types/api';

export const healthService = {
  check: () => apiRequest<SystemHealthResponse>('/api/v1/health', { method: 'GET' }, 5000),
};

export const farmService = {
  list: (skip = 0, limit = 100) =>
    apiRequest<FarmResponse[]>(`/api/v1/farms?skip=${skip}&limit=${limit}`),
  getById: (farmId: number) => apiRequest<FarmDetailResponse>(`/api/v1/farms/${farmId}`),
  create: (payload: FarmCreateRequest) =>
    apiRequest<FarmResponse>('/api/v1/farms', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

export const plotService = {
  listByFarm: (farmId: number) => apiRequest<PlotResponse[]>(`/api/v1/farms/${farmId}/plots`),
  create: (farmId: number, payload: PlotCreateRequest) =>
    apiRequest<PlotResponse>(`/api/v1/farms/${farmId}/plots`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

export const observationService = {
  listByPlot: (farmId: number, plotId: number) =>
    apiRequest<FieldObservationResponse[]>(
      `/api/v1/farms/${farmId}/plots/${plotId}/observations`
    ),
  create: (farmId: number, plotId: number, payload: FieldObservationCreateRequest) =>
    apiRequest<FieldObservationResponse>(
      `/api/v1/farms/${farmId}/plots/${plotId}/observations`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),
};

export const diseaseService = {
  predict: (file: File, options?: { plotId?: number | null; topK?: number }) => {
    const formData = new FormData();
    formData.append('file', file);
    const params = new URLSearchParams();
    params.set('top_k', String(options?.topK ?? 3));
    if (options?.plotId) {
      params.set('plot_id', String(options.plotId));
    }
    return apiRequest<DiseasePredictionResponse>(
      `/api/v1/predict/disease?${params.toString()}`,
      {
        method: 'POST',
        body: formData,
      },
      25000
    );
  },
};

export const yieldService = {
  predict: (payload: YieldPredictionRequest) =>
    apiRequest<YieldPredictionResponse>('/api/v1/predict/yield', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

export const recommendationService = {
  recommend: (payload: CropIrrigationAdvisoryRequest) =>
    apiRequest<CropIrrigationAdvisoryResponse>('/api/v1/recommend/crop-irrigation', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

export const twinService = {
  simulate: (payload: TwinSimulationRequest) =>
    apiRequest<TwinSimulationResponse>('/api/v1/twin/simulate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

export const intelligenceService = {
  assess: (payload: IntelligenceAssessmentRequest) =>
    apiRequest<IntelligenceAssessmentResponse>('/api/v1/intelligence/assess', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

export const historyService = {
  list: (params?: { limit?: number; moduleName?: string | null }) => {
    const search = new URLSearchParams();
    search.set('limit', String(params?.limit ?? 50));
    if (params?.moduleName) {
      search.set('module_name', params.moduleName);
    }
    return apiRequest<HistoryResponse>(`/api/v1/history?${search.toString()}`);
  },
};
