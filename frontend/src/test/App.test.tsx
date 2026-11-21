import React from 'react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppProvider } from '../context/AppContext';
import { AppRoutes } from '../App';
import { ProvenanceBadge } from '../components/ui/ProvenanceBadge';
import { getApiBaseUrl, setApiBaseUrl } from '../services/api/client';
import { getDiseaseKnowledge } from '../data/diseaseKnowledgeBase';

function renderWithProviders(initialRoute = '/dashboard') {
  const qc = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={qc}>
      <AppProvider>
        <MemoryRouter initialEntries={[initialRoute]}>
          <AppRoutes />
        </MemoryRouter>
      </AppProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();

  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method || 'GET';

    if (url.includes('/api/v1/health')) {
      return new Response(
        JSON.stringify({
          status: 'healthy',
          api_version: 'v1',
          model_loaded: true,
          model_version: '1.1.0',
          model_architecture: 'resnet50',
          num_classes: 15,
          inference_device: 'cuda',
        }),
        { status: 200 }
      );
    }
    if (url.match(/\/api\/v1\/farms\?/)) {
      return new Response(
        JSON.stringify([
          {
            id: 1,
            name: 'Chitwan Research Farm',
            location: 'Chitwan, Nepal',
            created_at: '2026-11-20T10:00:00Z',
            updated_at: '2026-11-20T10:00:00Z',
          },
        ]),
        { status: 200 }
      );
    }
    if (url.match(/\/api\/v1\/farms\/1$/)) {
      return new Response(
        JSON.stringify({
          id: 1,
          name: 'Chitwan Research Farm',
          location: 'Chitwan, Nepal',
          created_at: '2026-11-20T10:00:00Z',
          updated_at: '2026-11-20T10:00:00Z',
          plots: [
            {
              id: 10,
              farm_id: 1,
              name: 'North Tomato Block',
              crop_type: 'Tomato',
              area_hectares: 2.5,
              created_at: '2026-11-20T10:05:00Z',
            },
          ],
        }),
        { status: 200 }
      );
    }
    if (url.includes('/api/v1/predict/yield') && method === 'POST') {
      return new Response(
        JSON.stringify({
          crop_type: 'Tomato',
          predicted_yield_kg_per_ha: 21500.0,
          total_projected_yield_kg: 43000.0,
          area_hectares: 2.0,
          harvest_year: 2025,
          model_name: 'ridge_regression_baseline',
          epistemic_type: 'predicted',
          record_id: 301,
        }),
        { status: 200 }
      );
    }
    if (url.includes('/api/v1/recommend/crop-irrigation') && method === 'POST') {
      return new Response(
        JSON.stringify({
          epistemic_type: 'recommended',
          crop_type: 'Tomato',
          crop_suitability_ranking: [
            {
              crop_type: 'Tomato',
              suitability: 'Highly Suitable',
              suitability_score: 0.94,
              reasons: ['Optimal temperature and soil pH match'],
              crop_notes: 'Prefers well-drained loamy soil.',
            },
          ],
          irrigation_recommendation: {
            urgency: 'Moderate',
            action: 'Apply drip irrigation in morning window',
            estimated_water_liters_per_m2: 4.5,
          },
          fertilizer_recommendation: {
            soil_ph_status: 'Optimal',
            guidance_notes: ['Maintain balanced NPK fertigation'],
          },
          assumptions: ['Standard root depth assumed'],
          limitations: 'Rule-based advisory.',
          record_id: 302,
        }),
        { status: 200 }
      );
    }
    if (url.includes('/api/v1/twin/simulate') && method === 'POST') {
      return new Response(
        JSON.stringify({
          epistemic_type: 'simulated',
          crop_type: 'Tomato',
          scenario: 'warming_2c',
          baseline_yield_kg_ha: 20000.0,
          simulated_yield_kg_ha: 18400.0,
          yield_change_pct: -8.0,
          combined_yield_factor: 0.92,
          factor_breakdown: {
            temperature: 0.92,
            rainfall_moisture: 1.0,
            irrigation: 1.0,
            fertilizer: 1.0,
            disease: 1.0,
          },
          key_drivers: ['Mild heat stress at +2°C'],
          assumptions: ['Multiplicative factors'],
          limitations: 'Simplified scenario engine.',
          record_id: 303,
        }),
        { status: 200 }
      );
    }
    if (url.includes('/api/v1/intelligence/assess') && method === 'POST') {
      return new Response(
        JSON.stringify({
          epistemic_type: 'predicted',
          crop_type: 'Tomato',
          risk_assessment: {
            epistemic_type: 'predicted',
            crop_type: 'Tomato',
            risk_score: 0.78,
            risk_level: 'Critical',
            environmental_risk_subscore: 0.82,
            visual_anomaly_score: 0.25,
            estimated_leaf_wetness_hours: 11.4,
            primary_threats: ['Late Blight (Phytophthora infestans)'],
            contributing_factors: ['Critical relative humidity (88.0%)'],
            preventative_actions: ['Apply protective bio-fungicide'],
            caveats: 'Statistical risk estimation.',
          },
          assistant_response: {
            query: 'Check outbreak risk',
            intent_detected: 'disease_risk_assessment',
            epistemic_type: 'predicted',
            tools_invoked: ['assess_outbreak_and_multimodal_risk'],
            guidance: 'Assessed disease outbreak risk for Tomato: Critical (score: 0.78).',
            tool_data: null,
            limitations: 'Grounded in domain heuristics.',
          },
          limitations: 'Statistical risk estimation.',
          record_id: 304,
        }),
        { status: 200 }
      );
    }
    if (url.match(/\/api\/v1\/farms\/1\/plots\/10\/observations/)) {
      if (method === 'POST') {
        return new Response(
          JSON.stringify({
            id: 501,
            plot_id: 10,
            epistemic_type: 'observed',
            source: 'field_scout',
            observed_at: '2026-11-21T10:00:00Z',
            data: { temperature_c: 23.5, soil_moisture_pct: 64.0, soil_ph: 6.4 },
            notes: 'Healthy canopy',
          }),
          { status: 201 }
        );
      }
      return new Response(
        JSON.stringify([
          {
            id: 500,
            plot_id: 10,
            epistemic_type: 'observed',
            source: 'field_scout',
            observed_at: '2026-11-21T07:00:00Z',
            data: { temperature_c: 22.0, soil_moisture_pct: 61.0, soil_ph: 6.4 },
            notes: 'Morning scout check',
          },
          {
            id: 501,
            plot_id: 10,
            epistemic_type: 'external',
            source: 'nasa_power_agro',
            observed_at: '2026-11-21T08:00:00Z',
            data: { temperature_c: 24.0, soil_moisture_pct: 63.0, rainfall_mm: 3.2 },
            notes: 'Daily agroclimatology pull',
          },
        ]),
        { status: 200 }
      );
    }
    if (url.includes('/api/v1/history')) {
      return new Response(
        JSON.stringify({
          count: 2,
          limit: 50,
          module_name: null,
          items: [
            {
              record_type: 'prediction',
              id: 101,
              plot_id: 10,
              epistemic_type: 'predicted',
              module_name: 'crop_disease_classification',
              model_version: '1.1.0',
              timestamp: '2026-11-21T08:30:00Z',
              summary: 'resnet50: Tomato_Late_blight (confidence 0.99)',
            },
            {
              record_type: 'twin_scenario',
              id: 202,
              plot_id: 10,
              epistemic_type: 'simulated',
              module_name: 'twin_service_v1',
              model_version: null,
              timestamp: '2026-11-21T09:15:00Z',
              summary: "Scenario 'warming_2c'",
            },
          ],
        }),
        { status: 200 }
      );
    }
    return new Response(JSON.stringify([]), { status: 200 });
  });
});

describe('Provenance Design System (<ProvenanceBadge />)', () => {
  it('renders all 5 canonical provenance categories with accessible labels', () => {
    const categories = ['observed', 'external', 'predicted', 'simulated', 'recommended'] as const;
    const { unmount } = render(
      <div>
        {categories.map((cat) => (
          <ProvenanceBadge key={cat} type={cat} />
        ))}
      </div>
    );

    expect(screen.getByText('Observed')).toBeInTheDocument();
    expect(screen.getByText('External')).toBeInTheDocument();
    expect(screen.getByText('Predicted')).toBeInTheDocument();
    expect(screen.getByText('Simulated')).toBeInTheDocument();
    expect(screen.getByText('Recommended')).toBeInTheDocument();
    unmount();
  });
});

describe('Responsive AppShell, Mobile Navigation & Theme System', () => {
  it('renders Overview Dashboard, mobile bottom nav, and opens More drawer', async () => {
    renderWithProviders('/dashboard');

    expect(
      await screen.findByText(/Agricultural Digital Twin & Food Security Command/i)
    ).toBeInTheDocument();

    const moreBtn = screen.getByRole('button', { name: /More navigation modules/i });
    expect(moreBtn).toBeInTheDocument();

    fireEvent.click(moreBtn);
    expect(screen.getByText(/All Platform Modules/i)).toBeInTheDocument();
  });

  it('toggles between light and dark theme and persists to localStorage', async () => {
    renderWithProviders('/dashboard');

    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    const themeBtn = screen.getByRole('button', { name: /Switch to dark mode/i });
    fireEvent.click(themeBtn);

    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    expect(window.localStorage.getItem('agri_theme_mode')).toBe('dark');
  });
});

describe('Module Routing, API Submissions & Form Validation', () => {
  it('renders Crop Disease Diagnostic Studio and validates unsupported file types', async () => {
    renderWithProviders('/diagnosis');
    expect(
      await screen.findByText(/Crop Leaf Disease Diagnostic Studio/i)
    ).toBeInTheDocument();

    const fileInput = document.getElementById('leaf-image-upload') as HTMLInputElement;
    const badFile = new File(['hello'], 'notes.txt', { type: 'text/plain' });
    fireEvent.change(fileInput, { target: { files: [badFile] } });

    expect(await screen.findByText(/Unsupported file type/i)).toBeInTheDocument();
  });

  it('submits Yield Prediction form and displays PREDICTED yield output', async () => {
    renderWithProviders('/yield-prediction');
    expect(await screen.findByText(/Crop Yield Prediction Studio/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Compute Yield Forecast/i });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/21,500 kg\/ha/i)).toBeInTheDocument();
    expect(screen.getByText(/43,000 kg/i)).toBeInTheDocument();
  });

  it('submits Crop & Irrigation Advisory form and displays RECOMMENDED output', async () => {
    renderWithProviders('/recommendations');
    expect(
      await screen.findByText(/Crop Suitability, Irrigation & Fertilizer Advisory/i)
    ).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Generate Agronomic Advisory/i });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/Apply drip irrigation in morning window/i)).toBeInTheDocument();
    expect(screen.getByText(/94.0% match/i)).toBeInTheDocument();
  });

  it('submits Digital Twin Scenario simulation and displays SIMULATED comparison', async () => {
    renderWithProviders('/digital-twin');
    expect(
      await screen.findByText(/Agricultural Digital Twin Scenario Studio/i)
    ).toBeInTheDocument();

    const droughtBtn = screen.getByRole('button', { name: /Monsoon Drought/i });
    fireEvent.click(droughtBtn);
    expect(screen.getByText('×0.40')).toBeInTheDocument();

    const runBtn = screen.getByRole('button', { name: /Execute Digital Twin Simulation/i });
    fireEvent.click(runBtn);

    expect(await screen.findByText(/18,400 kg\/ha/i)).toBeInTheDocument();
    expect(screen.getByText(/-8%/i)).toBeInTheDocument();
  });

  it('submits Multimodal Intelligence Assessment and displays outbreak risk & assistant output', async () => {
    renderWithProviders('/intelligence');
    expect(
      await screen.findByText(/Agricultural Intelligence & Decision Support Center/i)
    ).toBeInTheDocument();

    const runBtn = screen.getByRole('button', { name: /Run Multimodal Risk & Assistant/i });
    fireEvent.click(runBtn);

    expect(await screen.findByText(/Critical Outbreak Risk/i)).toBeInTheDocument();
    expect(screen.getByText(/Late Blight \(Phytophthora infestans\)/i)).toBeInTheDocument();
  });

  it('renders Unified Provenance History and filters records by provenance', async () => {
    renderWithProviders('/history');
    expect(
      await screen.findByText(/Prediction & Digital Twin Scenario History/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText(/Tomato_Late_blight/i).length).toBeGreaterThan(0);
    });

    const simBtn = screen.getByRole('button', { name: /^simulated$/i });
    fireEvent.click(simBtn);
    expect(screen.getAllByText(/Scenario 'warming_2c'/i).length).toBeGreaterThan(0);
  });

  it('renders Farms & Plots Management and opens Register Farm modal', async () => {
    renderWithProviders('/farms');
    expect(
      await screen.findByText(/Farm & Plot Operations Management/i)
    ).toBeInTheDocument();
    expect(await screen.findByText(/North Tomato Block/i)).toBeInTheDocument();

    const regBtn = screen.getByRole('button', { name: /Register Farm/i });
    fireEvent.click(regBtn);
    expect(screen.getByText(/Register Agricultural Farm/i)).toBeInTheDocument();
  });

  it('renders Plot Detail Page with provenance-separated observations and filters', async () => {
    renderWithProviders('/farms/1/plots/10');
    expect(await screen.findByText(/North Tomato Block/i)).toBeInTheDocument();
    expect(await screen.findByText(/Morning scout check/i)).toBeInTheDocument();
    expect(screen.getByText(/Daily agroclimatology pull/i)).toBeInTheDocument();

    // Filter by External only
    const extBtn = screen.getByRole('button', { name: /^external$/i });
    fireEvent.click(extBtn);
    expect(screen.queryByText(/Morning scout check/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Daily agroclimatology pull/i)).toBeInTheDocument();
  });

  it('renders Platform Settings with theme controls, API diagnostic, and provenance taxonomy', async () => {
    renderWithProviders('/settings');
    expect(
      await screen.findByText(/Platform Settings, Appearance & API Diagnostics/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Canonical Data Provenance Taxonomy/i)).toBeInTheDocument();
    expect(screen.getByText(/Botanical Daylight \(Light\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Forest Obsidian \(Dark\)/i)).toBeInTheDocument();
  });

  it('renders 404 NotFoundPage for unknown routes', () => {
    renderWithProviders('/non-existent-route-xyz');
    expect(screen.getByText(/404 — Page Not Found/i)).toBeInTheDocument();
  });
});

describe('API Configuration & Disease Knowledge Base', () => {
  it('persists and retrieves API base URL override cleanly', () => {
    setApiBaseUrl('http://localhost:8000/');
    expect(getApiBaseUrl()).toBe('http://localhost:8000');
  });

  it('returns curated pathogen knowledge for all 15 PlantVillage classes', () => {
    const entry = getDiseaseKnowledge('Potato___Late_blight');
    expect(entry.scientificName).toBe('Phytophthora infestans');
    expect(entry.severity).toBe('Critical');
    expect(entry.treatments.length).toBeGreaterThan(2);
  });
});
