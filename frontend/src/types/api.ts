/**
 * Canonical TypeScript API Contracts
 * Mirrors app/schemas/contracts.py & app/api/v1/routes.py
 */

export type EpistemicType =
  | 'observed'
  | 'external'
  | 'predicted'
  | 'simulated'
  | 'recommended';

export interface SystemHealthResponse {
  status: string;
  api_version: string;
  model_loaded: boolean;
  model_version: string;
  model_architecture: string;
  num_classes: number;
  inference_device: string;
}

export interface FarmCreateRequest {
  name: string;
  location?: string | null;
}

export interface PlotResponse {
  id: number;
  farm_id: number;
  name: string;
  crop_type: string;
  area_hectares: number | null;
  created_at: string;
}

export interface FarmResponse {
  id: number;
  name: string;
  location: string | null;
  created_at: string;
  updated_at: string;
}

export interface FarmDetailResponse extends FarmResponse {
  plots: PlotResponse[];
}

export interface PlotCreateRequest {
  name: string;
  crop_type: string;
  area_hectares?: number | null;
}

export interface FieldObservationCreateRequest {
  source: string;
  epistemic_type: 'observed' | 'external';
  data: Record<string, unknown>;
  notes?: string | null;
}

export interface FieldObservationResponse {
  id: number;
  plot_id: number;
  epistemic_type: 'observed' | 'external';
  source: string;
  observed_at: string;
  data: Record<string, unknown>;
  notes: string | null;
}

export interface DiseasePredictionItem {
  rank: number;
  class_name: string;
  confidence: number;
  confidence_pct: string;
}

export interface DiseasePredictionResponse {
  filename: string;
  primary_prediction: DiseasePredictionItem;
  top_k_predictions: DiseasePredictionItem[];
  model_version: string;
  model_architecture: string;
  epistemic_type: 'predicted';
  inference_device: string;
  inference_time_ms: number;
  record_id: number | null;
}

export interface CropSuitabilityItem {
  crop_type: string;
  suitability: string;
  suitability_score: number;
  reasons: string[];
  crop_notes: string;
}

export interface IrrigationRecommendationItem {
  urgency: string;
  action: string;
  estimated_water_liters_per_m2: number;
}

export interface FertilizerRecommendationItem {
  soil_ph_status: string;
  guidance_notes: string[];
}

export interface CropIrrigationAdvisoryRequest {
  crop_type: string;
  soil_ph: number;
  temperature_c: number;
  soil_moisture_pct: number;
  precipitation_mm: number;
  plot_id?: number | null;
}

export interface CropIrrigationAdvisoryResponse {
  epistemic_type: 'recommended';
  crop_type: string;
  crop_suitability_ranking: CropSuitabilityItem[];
  irrigation_recommendation: IrrigationRecommendationItem;
  fertilizer_recommendation: FertilizerRecommendationItem;
  assumptions: string[];
  limitations: string;
  record_id: number | null;
}

export interface YieldPredictionRequest {
  crop_type: string;
  harvest_year: number;
  area_hectares: number;
  ph?: number;
  moisture_pct?: number;
  nitrogen_mg_kg?: number;
  organic_matter_pct?: number;
  plot_id?: number | null;
}

export interface YieldPredictionResponse {
  crop_type: string;
  predicted_yield_kg_per_ha: number;
  total_projected_yield_kg: number;
  area_hectares: number;
  harvest_year: number;
  model_name: string;
  epistemic_type: 'predicted';
  record_id: number | null;
}

export type TwinScenarioPreset =
  | 'baseline'
  | 'warming_2c'
  | 'monsoon_drought'
  | 'wet_monsoon'
  | 'custom';

export interface TwinSimulationRequest {
  crop_type: string;
  baseline_yield_kg_ha: number;
  scenario: TwinScenarioPreset | string;
  temperature_delta_c: number;
  rainfall_multiplier: number;
  irrigation_mm: number;
  fertilizer_kg_ha: number;
  disease_pressure: number;
  plot_id?: number | null;
}

export interface TwinFactorBreakdown {
  temperature: number;
  rainfall_moisture: number;
  irrigation: number;
  fertilizer: number;
  disease: number;
}

export interface TwinSimulationResponse {
  epistemic_type: 'simulated';
  crop_type: string;
  scenario: string;
  baseline_yield_kg_ha: number;
  simulated_yield_kg_ha: number;
  yield_change_pct: number;
  combined_yield_factor?: number | null;
  factor_breakdown?: TwinFactorBreakdown | null;
  key_drivers: string[];
  assumptions: string[];
  limitations: string;
  record_id: number | null;
}

export interface IntelligenceRiskAssessment {
  epistemic_type: 'predicted';
  crop_type: string;
  risk_score: number;
  risk_level: 'Low' | 'Moderate' | 'High' | 'Critical' | string;
  environmental_risk_subscore: number;
  visual_anomaly_score: number;
  estimated_leaf_wetness_hours: number;
  primary_threats: string[];
  contributing_factors: string[];
  preventative_actions: string[];
  caveats: string;
}

export interface IntelligenceAssistantResponse {
  query: string;
  intent_detected: string;
  epistemic_type: EpistemicType;
  tools_invoked: string[];
  guidance: string;
  tool_data: Record<string, unknown> | null;
  limitations: string;
}

export interface IntelligenceAssessmentRequest {
  crop_type: string;
  temperature_c: number;
  relative_humidity_pct: number;
  rainfall_mm: number;
  visual_anomaly_score: number;
  query?: string | null;
  plot_id?: number | null;
}

export interface IntelligenceAssessmentResponse {
  epistemic_type: 'predicted';
  crop_type: string;
  risk_assessment: IntelligenceRiskAssessment;
  assistant_response?: IntelligenceAssistantResponse | null;
  limitations: string;
  record_id: number | null;
}

export interface HistoryItem {
  record_type: 'prediction' | 'twin_scenario';
  id: number;
  plot_id: number | null;
  epistemic_type: EpistemicType;
  module_name: string;
  model_version: string | null;
  timestamp: string;
  summary: string;
}

export interface HistoryResponse {
  count: number;
  limit: number;
  module_name: string | null;
  items: HistoryItem[];
}
