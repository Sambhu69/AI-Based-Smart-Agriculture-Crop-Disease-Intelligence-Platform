import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  diseaseService,
  farmService,
  healthService,
  historyService,
  intelligenceService,
  observationService,
  plotService,
  recommendationService,
  twinService,
  yieldService,
} from '../services/api';
import type {
  CropIrrigationAdvisoryRequest,
  FarmCreateRequest,
  FieldObservationCreateRequest,
  IntelligenceAssessmentRequest,
  PlotCreateRequest,
  TwinSimulationRequest,
  YieldPredictionRequest,
} from '../types/api';

export function useSystemHealth() {
  return useQuery({
    queryKey: ['system-health'],
    queryFn: () => healthService.check(),
    staleTime: 15000,
    refetchInterval: 30000,
    retry: 1,
  });
}

export function useFarmsList() {
  return useQuery({
    queryKey: ['farms'],
    queryFn: () => farmService.list(0, 100),
    staleTime: 10000,
    retry: 1,
  });
}

export function useFarmDetail(farmId: number | null) {
  return useQuery({
    queryKey: ['farm', farmId],
    queryFn: () => farmService.getById(farmId as number),
    enabled: typeof farmId === 'number' && farmId > 0,
    staleTime: 8000,
    retry: 1,
  });
}

export function usePlotObservations(farmId: number | null, plotId: number | null) {
  return useQuery({
    queryKey: ['observations', farmId, plotId],
    queryFn: () => observationService.listByPlot(farmId as number, plotId as number),
    enabled:
      typeof farmId === 'number' &&
      farmId > 0 &&
      typeof plotId === 'number' &&
      plotId > 0,
    staleTime: 5000,
    retry: 1,
  });
}

export function useHistoryList(params?: { limit?: number; moduleName?: string | null }) {
  return useQuery({
    queryKey: ['history', params?.limit ?? 50, params?.moduleName ?? 'all'],
    queryFn: () => historyService.list(params),
    staleTime: 5000,
    retry: 1,
  });
}

export function useCreateFarmMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: FarmCreateRequest) => farmService.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['farms'] });
    },
  });
}

export function useCreatePlotMutation(farmId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PlotCreateRequest) => plotService.create(farmId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['farm', farmId] });
      qc.invalidateQueries({ queryKey: ['farms'] });
    },
  });
}

export function useCreateObservationMutation(farmId: number, plotId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: FieldObservationCreateRequest) =>
      observationService.create(farmId, plotId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['observations', farmId, plotId] });
    },
  });
}

export function usePredictDiseaseMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { file: File; plotId?: number | null; topK?: number }) =>
      diseaseService.predict(args.file, { plotId: args.plotId, topK: args.topK }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['history'] });
    },
  });
}

export function usePredictYieldMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: YieldPredictionRequest) => yieldService.predict(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['history'] });
    },
  });
}

export function useRecommendAgronomyMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CropIrrigationAdvisoryRequest) =>
      recommendationService.recommend(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['history'] });
    },
  });
}

export function useSimulateTwinMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TwinSimulationRequest) => twinService.simulate(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['history'] });
    },
  });
}

export function useAssessIntelligenceMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: IntelligenceAssessmentRequest) =>
      intelligenceService.assess(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['history'] });
    },
  });
}
