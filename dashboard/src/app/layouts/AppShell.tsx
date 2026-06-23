import type { ReactNode } from "react";

import { StatusBadge } from "../../components/badges/StatusBadge";
import { Sidebar } from "../../components/navigation/Sidebar";
import { Topbar } from "../../components/navigation/Topbar";
import { ReadOnlyBanner } from "../../components/common/ReadOnlyBanner";
import type { DashboardState } from "../../types/dashboard";
import { getStateTone, getValue } from "../../utils/guards";
import { formatCurrency } from "../../utils/formatters";


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

  // Tier 1 Metrics
  const portfolio = state?.portfolio;
  const today = state?.trades?.today;
  const risk = state?.risk;

  const bankrollVal = formatCurrency(getValue(portfolio, ["bankroll", "balance", "account_balance"]));
  const equityVal = formatCurrency(getValue(portfolio, ["equity", "net_asset_value"]) ?? getValue(portfolio, ["bankroll", "balance", "account_balance"]));
  const pnlVal = formatCurrency(getValue(today, ["total_realized_pnl", "realized_pnl"]));
  const pnlNum = Number(getValue(today, ["total_realized_pnl", "realized_pnl"]) ?? 0);
  const riskMode = String(getValue(risk, ["risk_mode", "mode"]) ?? getValue(state?.safety, ["mode"]) ?? "DEFENSIVE").toUpperCase();

  return (
    <header className="flex flex-col gap-4 p-4 border border-[#d9d9d9] bg-white rounded-lg mb-3 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[#d9d9d9] pb-3">
        <div>
          <p className="text-[12px] text-[#666666] font-bold uppercase tracking-wider m-0">Polymarket BTC 5M Quant Engine</p>
          <h1 className="text-[20px] font-bold text-black tracking-tight m-0 mb-1 flex flex-wrap items-center gap-2">
            Quant Operator Terminal V3
            <ReadOnlyBanner />
          </h1>
        </div>
        <div className="flex flex-wrap gap-1 md:justify-end">
          <StatusBadge label={safetyMode} tone={safetyMode.toUpperCase().includes("LIVE") ? "bad" : "good"} />
          <StatusBadge label={`State ${stateStatus}`} tone={tone} />
          <StatusBadge label={`API ${apiStatus ?? "unknown"}`} tone={apiStatus === "ok" ? "good" : "warn"} />
          <StatusBadge label={isFetching ? "refreshing" : "15s polling"} />
          <StatusBadge
            label={`alerts W:${warningCount} C:${criticalCount}`}
            tone={criticalCount > 0 ? "bad" : warningCount > 0 ? "warn" : "good"}
          />
        </div>
      </div>

      {/* Tier 1 Primary Metrics Ribbon */}
      <div className="grid grid-cols-1 sm:grid-cols-2 min-[1200px]:grid-cols-4 gap-3 pt-1">
        <div className="p-4 border-2 border-[#000000] bg-white rounded shadow-sm">
          <div className="text-[12px] text-[#404040] font-bold uppercase tracking-wider">Bankroll</div>
          <div className="text-2xl font-mono font-semibold text-black mt-2">{bankrollVal}</div>
        </div>
        <div className="p-4 border-2 border-[#000000] bg-white rounded shadow-sm">
          <div className="text-[12px] text-[#404040] font-bold uppercase tracking-wider">Portfolio Equity</div>
          <div className="text-2xl font-mono font-semibold text-black mt-2">{equityVal}</div>
        </div>
        <div className="p-4 border-2 border-[#000000] bg-white rounded shadow-sm">
          <div className="text-[12px] text-[#404040] font-bold uppercase tracking-wider">Realized PnL</div>
          <div className={`text-2xl font-mono font-semibold mt-2 ${pnlNum > 0 ? "text-[#008f39]" : pnlNum < 0 ? "text-[#c62828]" : "text-black"}`}>
            {pnlVal}
          </div>
        </div>
        <div className="p-4 border-2 border-[#000000] bg-white rounded shadow-sm">
          <div className="text-[12px] text-[#404040] font-bold uppercase tracking-wider">Risk Mode</div>
          <div className={`text-2xl font-mono font-semibold mt-2 ${riskMode === "LOCKDOWN" ? "text-[#c62828]" : "text-black"}`}>
            {riskMode}
          </div>
        </div>
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
    <div className="p-3 px-4 border border-[#b8860b] bg-[#fef7e0] text-[#000000] text-[13px] font-mono rounded-lg mb-3 flex flex-wrap gap-2 items-center">
      <strong>Dashboard state is {stateStatus ?? "UNKNOWN"}.</strong>
      <span>{state?.meta?.state_status_reason ?? "Inspect alerts before acting on this evidence."}</span>
      {warnings.length ? <span className="text-[#404040]">| {warnings.slice(0, 2).join(" | ")}</span> : null}
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
    <main className="w-full max-w-[2200px] mx-auto p-4 flex flex-col min-h-screen text-[#404040] font-sans">
      <Header state={state} isFetching={isFetching} apiStatus={apiStatus} />
      {stateError && state ? (
        <div className="p-3 px-4 border border-[#c62828] bg-[#fce8e6] text-[#000000] text-[13px] font-mono rounded-lg mb-3">
          Refresh failed; showing last successful dashboard state.
        </div>
      ) : null}
      <WarningBanner state={state} />
      <div className="flex flex-col min-[1600px]:flex-row gap-4 items-stretch min-[1600px]:items-start">
        <Sidebar />
        <div className="flex-grow min-w-0">
          <Topbar stateStatus={state?.meta?.state_status} apiStatus={apiStatus} isFetching={isFetching} />
          {children}
        </div>
      </div>
      <footer className="mt-auto pt-4 border-t border-[#d9d9d9] flex justify-between gap-2 text-[12px] text-[#666666] font-mono">
        <span>No trading buttons. No runtime controls. No config editing. HTTP polling only.</span>
        <span>Backend target: http://127.0.0.1:8000/api/dashboard/state</span>
      </footer>
    </main>
  );
}


export function ApiOffline({ error }: { error: unknown }) {
  return (
    <main className="max-w-[1480px] mx-auto p-4 flex flex-col min-h-screen text-[#404040] font-sans">
      <div className="max-w-[720px] mx-auto my-16 p-5 border border-[#c62828] bg-white rounded-lg text-[#000000] text-sm shadow-sm">
        <p className="text-[12px] text-[#c62828] font-bold uppercase tracking-wider m-0 mb-1">API offline state</p>
        <h1 className="text-xl font-bold text-black m-0 mb-2">Dashboard API is not reachable</h1>
        <p className="m-0 mb-3">
          Start the read-only API with{" "}
          <code className="bg-[#f2f2f2] text-black p-1 px-2 rounded font-mono text-[12px] border border-[#d9d9d9]">
            python -m uvicorn api.dashboard_api:app --host 127.0.0.1 --port 8000
          </code>.
        </p>
        <pre className="whitespace-pre-wrap text-[12px] font-mono text-[#c62828] bg-[#f7f7f7] p-3 rounded border border-[#d9d9d9]">
          {error instanceof Error ? error.message : "Unknown API error"}
        </pre>
      </div>
    </main>
  );
}
