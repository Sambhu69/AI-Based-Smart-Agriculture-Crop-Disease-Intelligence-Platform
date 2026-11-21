import React, { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity,
  BarChart3,
  BrainCircuit,
  ChevronLeft,
  ChevronRight,
  Compass,
  FolderKanban,
  History,
  LayoutDashboard,
  Leaf,
  Menu,
  Moon,
  Settings,
  Sliders,
  Sprout,
  Sun,
  X,
} from 'lucide-react';
import { useAppContext } from '../../context/AppContext';
import { useFarmsList, useSystemHealth } from '../../hooks/useAgriQueries';
import { ConnectionBadge } from '../ui/ConnectionBadge';

interface NavItem {
  to: string;
  label: string;
  shortLabel: string;
  group: 'Operations' | 'Intelligence' | 'Simulation' | 'Governance';
  Icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    to: '/dashboard',
    label: 'Overview Dashboard',
    shortLabel: 'Home',
    group: 'Operations',
    Icon: LayoutDashboard,
  },
  {
    to: '/farms',
    label: 'Farms & Plots',
    shortLabel: 'Farms',
    group: 'Operations',
    Icon: FolderKanban,
  },
  {
    to: '/diagnosis',
    label: 'Disease Diagnosis',
    shortLabel: 'Diagnose',
    group: 'Intelligence',
    Icon: Leaf,
    badge: 'CV',
  },
  {
    to: '/yield-prediction',
    label: 'Yield Prediction',
    shortLabel: 'Yield',
    group: 'Intelligence',
    Icon: BarChart3,
  },
  {
    to: '/recommendations',
    label: 'Crop & Irrigation',
    shortLabel: 'Advisory',
    group: 'Intelligence',
    Icon: Compass,
  },
  {
    to: '/digital-twin',
    label: 'Digital Twin Studio',
    shortLabel: 'Twin',
    group: 'Simulation',
    Icon: Sliders,
  },
  {
    to: '/intelligence',
    label: 'Intelligence Center',
    shortLabel: 'Intelligence',
    group: 'Simulation',
    Icon: BrainCircuit,
  },
  {
    to: '/history',
    label: 'Provenance History',
    shortLabel: 'History',
    group: 'Governance',
    Icon: History,
  },
  {
    to: '/settings',
    label: 'Platform Settings',
    shortLabel: 'Settings',
    group: 'Governance',
    Icon: Settings,
  },
];

// Primary 4 destinations for mobile bottom navigation + "More" trigger
const MOBILE_PRIMARY_PATHS = ['/dashboard', '/farms', '/diagnosis', '/intelligence'];

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { theme, toggleTheme, selectedFarmId, setSelectedFarmId } = useAppContext();
  const { data: health, isLoading: healthLoading, isError: healthError } = useSystemHealth();
  const { data: farms } = useFarmsList();
  const location = useLocation();
  const navigate = useNavigate();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [moreDrawerOpen, setMoreDrawerOpen] = useState(false);

  const activeNav =
    NAV_ITEMS.find((item) => location.pathname.startsWith(item.to)) || NAV_ITEMS[0];

  const primaryMobileItems = NAV_ITEMS.filter((i) => MOBILE_PRIMARY_PATHS.includes(i.to));
  const secondaryMobileItems = NAV_ITEMS.filter((i) => !MOBILE_PRIMARY_PATHS.includes(i.to));
  const isSecondaryActive = secondaryMobileItems.some((i) =>
    location.pathname.startsWith(i.to)
  );

  return (
    <div className="min-h-screen flex flex-col md:flex-row" style={{ backgroundColor: 'var(--bg-canvas)' }}>
      {/* =====================================================================
          DESKTOP & TABLET SIDEBAR (md: >= 768px)
      ===================================================================== */}
      <aside
        aria-label="Primary Sidebar Navigation"
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border-default)',
        }}
        className={`hidden md:flex flex-col shrink-0 border-r sticky top-0 h-screen transition-all duration-200 ${
          sidebarCollapsed ? 'w-20' : 'w-64'
        }`}
      >
        {/* Brand Header */}
        <div
          className="h-16 px-4 flex items-center justify-between border-b"
          style={{ borderColor: 'var(--border-default)' }}
        >
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2.5 text-left focus:outline-none"
          >
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-white font-bold"
              style={{ backgroundColor: 'var(--brand-primary)' }}
            >
              <Sprout className="w-5 h-5" />
            </div>
            {!sidebarCollapsed && (
              <div className="leading-tight">
                <span className="font-display font-extrabold text-sm tracking-tight block">
                  AgriTwin AI
                </span>
                <span className="text-[11px] block" style={{ color: 'var(--text-muted)' }}>
                  Precision Digital Twin
                </span>
              </div>
            )}
          </button>

          <button
            type="button"
            onClick={() => setSidebarCollapsed((c) => !c)}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="w-8 h-8 rounded-lg flex items-center justify-center hover:opacity-80"
            style={{ color: 'var(--text-secondary)', backgroundColor: 'var(--bg-subtle)' }}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-5">
          {(['Operations', 'Intelligence', 'Simulation', 'Governance'] as const).map((group) => {
            const items = NAV_ITEMS.filter((i) => i.group === group);
            return (
              <div key={group}>
                {!sidebarCollapsed && (
                  <div
                    className="px-2.5 mb-1.5 text-[11px] font-bold uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {group}
                  </div>
                )}
                <ul className="space-y-1">
                  {items.map((item) => {
                    const { Icon } = item;
                    return (
                      <li key={item.to}>
                        <NavLink
                          to={item.to}
                          title={sidebarCollapsed ? item.label : undefined}
                          className={({ isActive }) =>
                            `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                              isActive
                                ? 'font-semibold'
                                : 'hover:opacity-90'
                            }`
                          }
                          style={({ isActive }) =>
                            isActive
                              ? {
                                  backgroundColor: 'var(--brand-soft)',
                                  color: 'var(--brand-text)',
                                }
                              : {
                                  color: 'var(--text-secondary)',
                                }
                          }
                        >
                          <Icon className="w-5 h-5 shrink-0" />
                          {!sidebarCollapsed && (
                            <span className="flex-1 truncate">{item.label}</span>
                          )}
                          {!sidebarCollapsed && item.badge && (
                            <span
                              className="px-1.5 py-0.5 text-[10px] font-bold rounded-md"
                              style={{
                                backgroundColor: 'var(--bg-subtle)',
                                color: 'var(--text-secondary)',
                              }}
                            >
                              {item.badge}
                            </span>
                          )}
                        </NavLink>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </nav>

        {/* Sidebar Footer: Model Telemetry Summary */}
        <div
          className="p-3 border-t text-xs"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-subtle)' }}
        >
          {!sidebarCollapsed ? (
            <div className="space-y-1">
              <div className="flex items-center justify-between font-semibold">
                <span className="flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-emerald-600" />
                  ResNet-50 Engine
                </span>
                <span className="text-[11px] opacity-80">
                  v{health?.model_version || '1.1.0'}
                </span>
              </div>
              <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                {health?.num_classes ?? 15} disease classes • Provenance-enforced
              </p>
            </div>
          ) : (
            <div className="flex justify-center" title="ResNet-50 Engine Ready">
              <Activity className="w-4 h-4 text-emerald-600" />
            </div>
          )}
        </div>
      </aside>

      {/* =====================================================================
          MAIN CONTENT COLUMN
      ===================================================================== */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header (Responsive for Mobile, Tablet, and Desktop) */}
        <header
          style={{
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border-default)',
          }}
          className="sticky top-0 z-30 h-14 sm:h-16 px-3 sm:px-6 border-b flex items-center justify-between gap-2"
        >
          {/* Left: Mobile Brand + Current Page Title */}
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="md:hidden w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-white"
              style={{ backgroundColor: 'var(--brand-primary)' }}
              aria-label="Go to Overview Dashboard"
            >
              <Sprout className="w-5 h-5" />
            </button>
            <div className="min-w-0">
              <h1 className="text-sm sm:text-base font-bold font-display truncate">
                {activeNav.label}
              </h1>
              <p
                className="hidden sm:block text-[11px] truncate"
                style={{ color: 'var(--text-muted)' }}
              >
                Autonomous Precision Agriculture Digital Twin & Food Security Intelligence
              </p>
            </div>
          </div>

          {/* Right Controls: Farm Selector + API Health + Theme Toggle */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Global Farm Context Selector */}
            <label htmlFor="global-farm-select" className="sr-only">
              Active Farm Context
            </label>
            <select
              id="global-farm-select"
              aria-label="Active Farm Context"
              value={selectedFarmId ?? ''}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedFarmId(val ? Number(val) : null);
              }}
              style={{
                backgroundColor: 'var(--bg-subtle)',
                color: 'var(--text-primary)',
                borderColor: 'var(--border-default)',
              }}
              className="min-h-[38px] max-w-[135px] sm:max-w-[200px] px-2.5 py-1 rounded-xl border text-xs font-medium truncate focus:outline-none"
            >
              <option value="">All Farms ({farms?.length ?? 0})</option>
              {farms?.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>

            <ConnectionBadge
              health={health}
              isLoading={healthLoading}
              isError={healthError}
              compact={false}
            />

            <button
              type="button"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
              title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
              style={{
                backgroundColor: 'var(--bg-subtle)',
                color: 'var(--text-primary)',
                borderColor: 'var(--border-default)',
              }}
              className="touch-target w-10 h-10 rounded-xl border inline-flex items-center justify-center hover:opacity-80"
            >
              {theme === 'light' ? (
                <Moon className="w-4 h-4" />
              ) : (
                <Sun className="w-4 h-4 text-amber-400" />
              )}
            </button>
          </div>
        </header>

        {/* Main Page Content Container */}
        <main className="flex-1 w-full max-w-7xl mx-auto px-3.5 sm:px-6 pt-4 sm:pt-6 pb-safe-nav">
          {children}
        </main>
      </div>

      {/* =====================================================================
          MOBILE BOTTOM NAVIGATION BAR (< 768px)
      ===================================================================== */}
      <nav
        aria-label="Mobile Primary Navigation"
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border-default)',
        }}
        className="md:hidden fixed bottom-0 inset-x-0 z-40 border-t px-1.5 py-1 flex items-center justify-around"
      >
        {primaryMobileItems.map((item) => {
          const { Icon } = item;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMoreDrawerOpen(false)}
              className="touch-target flex-1 flex flex-col items-center justify-center py-1 rounded-xl text-[11px] font-semibold transition-colors"
              style={({ isActive }) =>
                isActive
                  ? { color: 'var(--brand-primary)' }
                  : { color: 'var(--text-muted)' }
              }
            >
              <Icon className="w-5 h-5 mb-0.5" />
              <span>{item.shortLabel}</span>
            </NavLink>
          );
        })}

        {/* 5th Tab: More Drawer Trigger */}
        <button
          type="button"
          onClick={() => setMoreDrawerOpen((o) => !o)}
          aria-expanded={moreDrawerOpen}
          aria-label="More navigation modules"
          className="touch-target flex-1 flex flex-col items-center justify-center py-1 rounded-xl text-[11px] font-semibold"
          style={
            moreDrawerOpen || isSecondaryActive
              ? { color: 'var(--brand-primary)' }
              : { color: 'var(--text-muted)' }
          }
        >
          {moreDrawerOpen ? (
            <X className="w-5 h-5 mb-0.5" />
          ) : (
            <Menu className="w-5 h-5 mb-0.5" />
          )}
          <span>More</span>
        </button>
      </nav>

      {/* =====================================================================
          MOBILE "MORE" SLIDE-UP NAVIGATION SHEET (< 768px)
      ===================================================================== */}
      {moreDrawerOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Additional platform modules"
          className="md:hidden fixed inset-0 z-30 bg-black/50 backdrop-blur-xs flex items-end"
          onClick={(e) => {
            if (e.target === e.currentTarget) setMoreDrawerOpen(false);
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderColor: 'var(--border-default)',
            }}
            className="w-full rounded-t-2xl border-t p-4 pb-20 space-y-3"
          >
            <div className="flex items-center justify-between pb-2 border-b" style={{ borderColor: 'var(--border-default)' }}>
              <span className="text-sm font-bold font-display">
                All Platform Modules
              </span>
              <button
                type="button"
                onClick={() => setMoreDrawerOpen(false)}
                className="touch-target p-2 rounded-lg"
                aria-label="Close menu"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              {secondaryMobileItems.map((item) => {
                const { Icon } = item;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMoreDrawerOpen(false)}
                    className="touch-target flex items-center gap-2.5 p-3 rounded-xl border text-xs font-semibold"
                    style={({ isActive }) =>
                      isActive
                        ? {
                            backgroundColor: 'var(--brand-soft)',
                            color: 'var(--brand-text)',
                            borderColor: 'var(--brand-primary)',
                          }
                        : {
                            backgroundColor: 'var(--bg-subtle)',
                            color: 'var(--text-primary)',
                            borderColor: 'var(--border-default)',
                          }
                    }
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
