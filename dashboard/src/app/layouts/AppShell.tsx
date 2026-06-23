import type { ReactNode } from "react";

import { StatusBadge } from "../../components/badges/StatusBadge";
import { ReadOnlyBanner } from "../../components/common/ReadOnlyBanner";
import type { DashboardState } from "../../types/dashboard";
import { getStateTone, getValue } from "../../utils/guards";

function Header({
  state,
  isFetching,
  apiStatus,
}: {
  state?: DashboardState;
  isFetching: boolean;
  apiStatus?: string;
}) {
  const stateStatus = state?.meta?.state_status ?? "UNKNOWN";
  const tone = getStateTone(stateStatus);
  const warningCount = state?.alerts?.counts?.warning ?? 0;
  const criticalCount = state?.alerts?.counts?.critical ?? 0;
  const safetyMode = String(getValue(state?.safety, ["mode", "runtime_mode", "trading_mode"]) ?? "PAPER / UNKNOWN");

  return (
    <header className="app-header">
      <div>
        <p className="eyebrow">Polymarket BTC 5M Quant Engine</p>
        <h1>Quant Operator Dashboard V0</h1>
        <ReadOnlyBanner />
      </div>
      <div className="header-badges">
        <StatusBadge label={safetyMode} tone={safetyMode.toUpperCase().includes("LIVE") ? "bad" : "good"} />
        <StatusBadge label={`State ${stateStatus}`} tone={tone} />
        <StatusBadge label={`API ${apiStatus ?? "unknown"}`} tone={apiStatus === "ok" ? "good" : "warn"} />
        <StatusBadge label={isFetching ? "refreshing" : "15s polling"} />
        <StatusBadge
          label={`alerts W:${warningCount} C:${criticalCount}`}
          tone={criticalCount > 0 ? "bad" : warningCount > 0 ? "warn" : "good"}
        />
      </div>
    </header>
  );
}

function WarningBanner({ state }: { state?: DashboardState }) {
  const warnings = state?.meta?.warnings ?? [];
  const stateStatus = state?.meta?.state_status;
  if (stateStatus === "OK" && !warnings.length) {
    return null;
  }

  return (
    <div className="warning-banner">
      <strong>Dashboard state is {stateStatus ?? "UNKNOWN"}.</strong>
      <span>{state?.meta?.state_status_reason ?? "Inspect alerts before acting on this evidence."}</span>
      {warnings.length ? <span>{warnings.slice(0, 2).join(" | ")}</span> : null}
    </div>
  );
}

export function AppShell({
  state,
  isFetching,
  apiStatus,
  stateError,
  children,
}: {
  state?: DashboardState;
  isFetching: boolean;
  apiStatus?: string;
  stateError: boolean;
  children: ReactNode;
}) {
  return (
    <main className="app-shell">
      <Header state={state} isFetching={isFetching} apiStatus={apiStatus} />
      {stateError && state ? <div className="warning-banner">Refresh failed; showing last successful dashboard state.</div> : null}
      <WarningBanner state={state} />
      {children}
      <footer className="app-footer">
        <span>No trading buttons. No runtime controls. No config editing. HTTP polling only.</span>
        <span>Backend target: http://127.0.0.1:8000/api/dashboard/state</span>
      </footer>
    </main>
  );
}

export function ApiOffline({ error }: { error: unknown }) {
  return (
    <main className="app-shell">
      <div className="offline-state">
        <p className="eyebrow">API offline state</p>
        <h1>Dashboard API is not reachable</h1>
        <p>
          Start the read-only API with{" "}
          <code>python -m uvicorn api.dashboard_api:app --host 127.0.0.1 --port 8000</code>.
        </p>
        <pre>{error instanceof Error ? error.message : "Unknown API error"}</pre>
      </div>
    </main>
  );
}
