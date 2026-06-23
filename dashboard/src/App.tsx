import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fetchDashboardHealth, fetchDashboardState } from "./api";
import {
  entriesFromRecord,
  formatCurrency,
  formatNumber,
  formatPercent,
  getStateTone,
  storageRows,
  storageUnitLabel,
  sumRecordValues,
  toWinLossRows,
} from "./dashboardData";
import type { AlertRecord, ChartRow, DashboardState, Tone } from "./types";

const COLORS = ["#5eead4", "#60a5fa", "#c084fc", "#fbbf24", "#fb7185", "#a3e635"];

function getValue(source: Record<string, unknown> | undefined, keys: string[]): unknown {
  if (!source) {
    return undefined;
  }
  return keys.map((key) => source[key]).find((value) => value !== undefined && value !== null);
}

function StatusBadge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  return <span className={`status-badge status-${tone}`}>{label}</span>;
}

function MetricCard({
  label,
  value,
  helper,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  helper?: string;
  tone?: Tone;
}) {
  return (
    <div className={`metric-card metric-${tone}`}>
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
      {helper ? <small>{helper}</small> : null}
    </div>
  );
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="section-panel">
      <div className="section-heading">
        <h2>{title}</h2>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}

function EmptyState({ label }: { label: string }) {
  return <div className="empty-state">{label}</div>;
}

function DataTable({
  rows,
  columns,
  empty,
}: {
  rows: Record<string, unknown>[];
  columns: { key: string; label: string }[];
  empty: string;
}) {
  if (!rows.length) {
    return <EmptyState label={empty} />;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.code ?? row.name ?? index}`}>
              {columns.map((column) => (
                <td key={column.key}>{String(row[column.key] ?? "n/a")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PieMetricChart({ data, emptyLabel }: { data: ChartRow[]; emptyLabel: string }) {
  if (!data.length) {
    return <EmptyState label={emptyLabel} />;
  }

  return (
    <ResponsiveContainer width="100%" height={230}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={82} paddingAngle={2}>
          {data.map((entry, index) => (
            <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}

function BarMetricChart({
  data,
  emptyLabel,
  unit,
}: {
  data: ChartRow[];
  emptyLabel: string;
  unit?: string;
}) {
  if (!data.length) {
    return <EmptyState label={emptyLabel} />;
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data.slice(0, 8)} margin={{ top: 10, right: 10, left: 0, bottom: 24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="name" angle={-20} textAnchor="end" interval={0} height={70} stroke="#94a3b8" />
        <YAxis stroke="#94a3b8" />
        <Tooltip formatter={(value) => [`${value}${unit ? ` ${unit}` : ""}`, "value"]} />
        <Bar dataKey="value" fill="#5eead4" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

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
        <p className="read-only">READ ONLY DASHBOARD - OBSERVABILITY ONLY</p>
      </div>
      <div className="header-badges">
        <StatusBadge label={safetyMode} tone={safetyMode.toUpperCase().includes("LIVE") ? "bad" : "good"} />
        <StatusBadge label={`State ${stateStatus}`} tone={tone} />
        <StatusBadge label={`API ${apiStatus ?? "unknown"}`} tone={apiStatus === "ok" ? "good" : "warn"} />
        <StatusBadge label={isFetching ? "refreshing" : "15s polling"} />
        <StatusBadge label={`alerts W:${warningCount} C:${criticalCount}`} tone={criticalCount > 0 ? "bad" : warningCount > 0 ? "warn" : "good"} />
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

function RuntimeHealth({ state }: { state?: DashboardState }) {
  const runtime = state?.runtime;
  const ownerPid = getValue(runtime, ["owner_pid", "pid", "process_id"]);
  const ownerStatus = getValue(runtime, ["owner_status", "status"]);
  const runId = getValue(runtime, ["run_id", "owner_run_id"]);
  const heartbeatAge = state?.health?.freshness?.owner_heartbeat_age_seconds;

  return (
    <Section title="Runtime Health" subtitle="Liveness, owner state, heartbeat freshness, and state generation.">
      <div className="metric-grid">
        <MetricCard label="Runtime status" value={String(ownerStatus ?? "unknown")} tone={ownerStatus === "active" ? "good" : "warn"} />
        <MetricCard label="Owner PID" value={String(ownerPid ?? "n/a")} />
        <MetricCard label="Run ID" value={String(runId ?? "n/a")} />
        <MetricCard label="Heartbeat age" value={`${formatNumber(heartbeatAge, 0)}s`} tone={Number(heartbeatAge ?? 0) > 300 ? "warn" : "good"} />
        <MetricCard label="State generated" value={state?.meta?.generated_at_utc ?? "n/a"} />
        <MetricCard label="System health rows" value={formatNumber(state?.health?.system_health_rows_today, 0)} />
      </div>
    </Section>
  );
}

function Portfolio({ state }: { state?: DashboardState }) {
  const portfolio = state?.portfolio;
  const risk = state?.risk;
  const today = state?.trades?.today;

  return (
    <Section title="Portfolio" subtitle="Bankroll, exposure, and paper trade performance.">
      <div className="metric-grid">
        <MetricCard label="Bankroll" value={formatCurrency(getValue(portfolio, ["bankroll", "balance", "account_balance"]))} />
        <MetricCard label="Balance source" value={String(getValue(portfolio, ["balance_source", "source"]) ?? "n/a")} />
        <MetricCard label="Open positions" value={formatNumber(getValue(portfolio, ["open_position_count", "positions_open"]), 0)} />
        <MetricCard label="Exposure" value={formatCurrency(getValue(risk, ["current_exposure", "exposure"]))} />
        <MetricCard label="Realized PnL" value={formatCurrency(getValue(today, ["total_realized_pnl", "realized_pnl"]))} />
        <MetricCard label="Win rate" value={formatPercent(getValue(today, ["win_rate"]))} />
      </div>
    </Section>
  );
}

function SignalIntelligence({ state }: { state?: DashboardState }) {
  const funnel = state?.phase_b?.candidate_funnel_today;
  const skipRows = entriesFromRecord(funnel?.skip_reason_counts);
  const assetRows = entriesFromRecord(funnel?.asset_counts);
  const signalRows = entriesFromRecord(funnel?.signal_name_counts);
  const skips = sumRecordValues(funnel?.skip_reason_counts);

  const signalAssetRows = Object.entries(state?.signals?.assets ?? {}).map(([asset, details]) => ({
    asset,
    signal_name: String(getValue(details, ["signal_name", "name"]) ?? "n/a"),
    signal_reason: String(getValue(details, ["signal_reason", "reason"]) ?? "n/a"),
    side: String(getValue(details, ["side", "selected_side"]) ?? "n/a"),
    score: String(getValue(details, ["score"]) ?? "n/a"),
  }));

  return (
    <Section title="Signal Intelligence" subtitle="Candidate activity, signal shape, and skip bottlenecks.">
      <div className="metric-grid">
        <MetricCard label="Decisions today" value={formatNumber(funnel?.decision_count, 0)} />
        <MetricCard label="Entries today" value={formatNumber(state?.trades?.today?.trade_open_count, 0)} />
        <MetricCard label="Skips today" value={formatNumber(skips, 0)} />
        <MetricCard label="Top skip reason" value={skipRows[0]?.name ?? "n/a"} helper={skipRows[0] ? String(skipRows[0].value) : undefined} />
      </div>
      <div className="chart-grid">
        <div className="chart-card">
          <h3>Skip Reason Distribution</h3>
          <BarMetricChart data={skipRows} emptyLabel="No skip reason data available." />
        </div>
        <div className="chart-card">
          <h3>Signal Asset Distribution</h3>
          <PieMetricChart data={assetRows.length ? assetRows : signalRows} emptyLabel="No asset or signal distribution available." />
        </div>
      </div>
      <DataTable
        rows={signalAssetRows}
        columns={[
          { key: "asset", label: "Asset" },
          { key: "signal_name", label: "Signal" },
          { key: "signal_reason", label: "Reason" },
          { key: "side", label: "Side" },
          { key: "score", label: "Score" },
        ]}
        empty="No per-asset signal details available."
      />
    </Section>
  );
}

function Risk({ state }: { state?: DashboardState }) {
  const risk = state?.risk;
  const safety = state?.safety;

  return (
    <Section title="Risk" subtitle="Evidence-only risk mode, budget, exposure, and reconciliation state.">
      <div className="metric-grid">
        <MetricCard label="Risk mode" value={String(getValue(risk, ["risk_mode", "mode"]) ?? "n/a")} />
        <MetricCard label="Available risk budget" value={formatCurrency(getValue(risk, ["available_risk_budget", "risk_budget_available"]))} />
        <MetricCard label="Current exposure" value={formatCurrency(getValue(risk, ["current_exposure", "exposure"]))} />
        <MetricCard label="Risk events today" value={formatNumber(getValue(risk, ["risk_event_count_today"]), 0)} />
        <MetricCard label="Risk-plan-zero" value={formatNumber(getValue(risk, ["risk_plan_zero_count_today"]), 0)} />
        <MetricCard label="Reconciliation" value={String(getValue(safety, ["reconciliation_class", "reconciliation_status"]) ?? "n/a")} />
      </div>
    </Section>
  );
}

function Storage({ state }: { state?: DashboardState }) {
  const rows = storageRows(state);
  const unit = storageUnitLabel(state);

  const tableRows = Object.entries(state?.storage?.categories ?? {}).map(([name, details]) => ({
    name,
    size: String(getValue(details, ["size_mb", "total_size_mb", "size_bytes"]) ?? "n/a"),
    jsonl_count: String(getValue(details, ["jsonl_count"]) ?? "n/a"),
    gz_count: String(getValue(details, ["gz_count"]) ?? "n/a"),
    latest_file: String(getValue(details, ["latest_file"]) ?? "n/a"),
  }));

  return (
    <Section title="Storage" subtitle="Runtime storage footprint and compression evidence.">
      <div className="metric-grid">
        <MetricCard label="Runtime total" value={formatNumber(getValue(state?.storage, ["runtime_total_mb", "total_size_mb"]), 2)} helper="MB if provided by state" />
        <MetricCard label="Compression candidates" value={formatNumber(getValue(state?.storage, ["compression_candidate_count", "candidate_count"]), 0)} />
        <MetricCard label="Expected reclaim" value={formatNumber(getValue(state?.storage, ["expected_reclaim_mb", "expected_reclaim_gb"]), 2)} />
      </div>
      <div className="chart-card">
        <h3>Storage By Category</h3>
        <BarMetricChart data={rows} emptyLabel="No storage category data available." unit={unit} />
      </div>
      <DataTable
        rows={tableRows}
        columns={[
          { key: "name", label: "Category" },
          { key: "size", label: "Size" },
          { key: "jsonl_count", label: "JSONL" },
          { key: "gz_count", label: "GZ" },
          { key: "latest_file", label: "Latest file" },
        ]}
        empty="No storage category details available."
      />
    </Section>
  );
}

function Alerts({ alerts }: { alerts?: AlertRecord[] }) {
  const rows = (alerts ?? []).map((alert) => ({
    severity: alert.severity ?? "unknown",
    code: alert.code ?? "unknown",
    message: alert.message ?? "n/a",
    source: alert.source ?? "n/a",
  }));

  return (
    <Section title="Alerts" subtitle="Recent and active observability warnings from dashboard state.">
      <DataTable
        rows={rows}
        columns={[
          { key: "severity", label: "Severity" },
          { key: "code", label: "Code" },
          { key: "message", label: "Message" },
          { key: "source", label: "Source" },
        ]}
        empty="No active alerts reported."
      />
    </Section>
  );
}

function TradeCharts({ state }: { state?: DashboardState }) {
  const winLossRows = toWinLossRows(state?.trades?.today);

  return (
    <Section title="Trade Snapshot" subtitle="Read-only trade summary charts from dashboard state.">
      <div className="chart-grid">
        <div className="chart-card">
          <h3>Win / Loss Summary</h3>
          <PieMetricChart data={winLossRows} emptyLabel="No win/loss data available." />
        </div>
        <div className="chart-card">
          <h3>Signal Name Distribution</h3>
          <BarMetricChart
            data={entriesFromRecord(state?.phase_b?.candidate_funnel_today?.signal_name_counts)}
            emptyLabel="No signal name distribution available."
          />
        </div>
      </div>
    </Section>
  );
}

function ApiOffline({ error }: { error: unknown }) {
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

export default function App() {
  const stateQuery = useQuery({
    queryKey: ["dashboard-state"],
    queryFn: fetchDashboardState,
  });
  const healthQuery = useQuery({
    queryKey: ["dashboard-health"],
    queryFn: fetchDashboardHealth,
  });

  const state = stateQuery.data;
  const alerts = useMemo(() => {
    return state?.alerts?.active?.length ? state.alerts.active : state?.alerts?.recent;
  }, [state]);

  if (stateQuery.isError && !state) {
    return <ApiOffline error={stateQuery.error} />;
  }

  return (
    <main className="app-shell">
      <Header state={state} isFetching={stateQuery.isFetching} apiStatus={healthQuery.data?.status} />
      {stateQuery.isLoading ? <div className="loading-card">Loading dashboard state...</div> : null}
      {stateQuery.isError && state ? <div className="warning-banner">Refresh failed; showing last successful dashboard state.</div> : null}
      <WarningBanner state={state} />
      <RuntimeHealth state={state} />
      <Portfolio state={state} />
      <SignalIntelligence state={state} />
      <Risk state={state} />
      <TradeCharts state={state} />
      <Storage state={state} />
      <Alerts alerts={alerts} />
      <footer className="app-footer">
        <span>No trading buttons. No runtime controls. No config editing. HTTP polling only.</span>
        <span>Backend target: http://127.0.0.1:8000/api/dashboard/state</span>
      </footer>
    </main>
  );
}
