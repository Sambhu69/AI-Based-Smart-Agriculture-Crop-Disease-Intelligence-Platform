import React, { createContext, useContext, useEffect, useState } from 'react';
import { getApiBaseUrl, setApiBaseUrl } from '../services/api/client';

export type ThemeMode = 'light' | 'dark';

interface AppContextValue {
  theme: ThemeMode;
  toggleTheme: () => void;
  setTheme: (mode: ThemeMode) => void;
  selectedFarmId: number | null;
  setSelectedFarmId: (farmId: number | null) => void;
  apiBaseUrl: string;
  updateApiBaseUrl: (url: string) => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

const STORAGE_THEME = 'agri_theme_mode';
const STORAGE_FARM = 'agri_selected_farm_id';

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    if (typeof window !== 'undefined') {
      const saved = window.localStorage.getItem(STORAGE_THEME);
      if (saved === 'dark' || saved === 'light') return saved;
    }
    return 'light';
  });

  const [selectedFarmId, setSelectedFarmIdState] = useState<number | null>(() => {
    if (typeof window !== 'undefined') {
      const saved = window.localStorage.getItem(STORAGE_FARM);
      if (saved) {
        const parsed = Number(saved);
        return Number.isFinite(parsed) ? parsed : null;
      }
    }
    return null;
  });

  const [apiBaseUrl, setApiBaseUrlState] = useState<string>(() => getApiBaseUrl());

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    window.localStorage.setItem(STORAGE_THEME, theme);
  }, [theme]);

  const setTheme = (mode: ThemeMode) => setThemeState(mode);
  const toggleTheme = () => setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'));

  const setSelectedFarmId = (farmId: number | null) => {
    setSelectedFarmIdState(farmId);
    if (typeof window !== 'undefined') {
      if (farmId === null) {
        window.localStorage.removeItem(STORAGE_FARM);
      } else {
        window.localStorage.setItem(STORAGE_FARM, String(farmId));
      }
    }
  };

  const updateApiBaseUrl = (url: string) => {
    setApiBaseUrl(url);
    setApiBaseUrlState(getApiBaseUrl());
  };

  return (
    <AppContext.Provider
      value={{
        theme,
        toggleTheme,
        setTheme,
        selectedFarmId,
        setSelectedFarmId,
        apiBaseUrl,
        updateApiBaseUrl,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error('useAppContext must be used inside an AppProvider');
  }
  return ctx;
}
