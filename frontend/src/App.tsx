import React from 'react';
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppProvider } from './context/AppContext';
import { AppShell } from './components/layout/AppShell';
import { Button, Card } from './components/ui/Primitives';
import { DashboardPage } from './pages/DashboardPage';
import { FarmsPage } from './pages/FarmsPage';
import { PlotDetailPage } from './pages/PlotDetailPage';
import { DiagnosisPage } from './pages/DiagnosisPage';
import { YieldPredictionPage } from './pages/YieldPredictionPage';
import { RecommendationsPage } from './pages/RecommendationsPage';
import { DigitalTwinPage } from './pages/DigitalTwinPage';
import { IntelligencePage } from './pages/IntelligencePage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
    },
  },
});

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();
  return (
    <Card padding="lg" className="text-center py-12 space-y-3">
      <h2 className="text-2xl font-extrabold font-display">404 — Page Not Found</h2>
      <p className="text-xs sm:text-sm max-w-md mx-auto" style={{ color: 'var(--text-secondary)' }}>
        The requested route does not exist in the AgriTwin Intelligence Platform.
      </p>
      <div>
        <Button onClick={() => navigate('/dashboard')}>Return to Dashboard</Button>
      </div>
    </Card>
  );
};

export const AppRoutes: React.FC = () => (
  <AppShell>
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/farms" element={<FarmsPage />} />
      <Route path="/farms/:farmId/plots/:plotId" element={<PlotDetailPage />} />
      <Route path="/diagnosis" element={<DiagnosisPage />} />
      <Route path="/yield-prediction" element={<YieldPredictionPage />} />
      <Route path="/recommendations" element={<RecommendationsPage />} />
      <Route path="/digital-twin" element={<DigitalTwinPage />} />
      <Route path="/intelligence" element={<IntelligencePage />} />
      <Route path="/history" element={<HistoryPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  </AppShell>
);

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AppProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AppProvider>
    </QueryClientProvider>
  );
};

export default App;
