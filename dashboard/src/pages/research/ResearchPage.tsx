import { MetricCard } from "../../components/cards/MetricCard";
import { DataTable } from "../../components/common/DataTable";
import { EmptyState } from "../../components/common/EmptyState";
import { SectionPanel } from "../../components/common/SectionPanel";
import { useDashboardState } from "../../hooks/useDashboardState";
import { formatNumber, formatPercent } from "../../utils/formatters";

const researchRoadmap = [
  {
    title: "Replay Analytics",
    description: "Closed-trade replay, attribution review, lifecycle truth checks, and replay-key coverage.",
    status: "read-only planned",
  },
  {
    title: "Session Analytics",
    description: "Paper-session health, entry funnel movement, runtime stability, and trade-count progression.",
    status: "read-only planned",
  },
  {
    title: "Regime Analytics",
    description: "Market regime breakdowns, signal performance by regime, and volatility-state comparisons.",
    status: "read-only planned",
  },
  {
    title: "Expectancy Analytics",
    description: "Entry EV, realized PnL, win rate, signal reason, and candidate-instance comparisons.",
    status: "read-only planned",
  },
  {
    title: "Backtesting Workbench",
    description: "Offline backtest summaries and parameter evidence. No runtime or live controls.",
    status: "read-only planned",
  },
  {
    title: "Monte Carlo Lab",
    description: "Risk-of-ruin, drawdown path simulation, bankroll survivability, and sample-size planning.",
    status: "read-only planned",
  },
];

function reasonRows(rows?: { name?: string; count?: number | null }[]) {
  return (rows ?? []).map((row) => ({
    name: row.name ?? "unknown",
    count: row.count ?? "n/a",
  }));
}

function reportStatusRows(reports?: Record<string, Record<string, unknown> | undefined>) {
  const reportNames = [
    ["replay", "Replay"],
    ["no_entry", "No Entry"],
    ["session_runtime", "Session Runtime"],
    ["data_quality", "Data Quality"],
  ];
  return reportNames.map(([key, label]) => {
    const report = reports?.[key];
    const path = String(report?.path ?? "");
    return {
      report: label,
      status: path ? "available" : "missing",
      source: path ? path.split(/[\\/]/).pop() : "n/a",
    };
  });
}

function firstReportValue(report: Record<string, unknown> | undefined, key: string) {
  const value = report?.[key];
  return value === undefined || value === null || value === "" ? "n/a" : String(value);
}

export function ResearchPage() {
  const { state, stateQuery } = useDashboardState();
  const research = state?.research_analytics;
  const latest = research?.latest_research_state;
  const reports = research?.reports;
  const dataQuality = reports?.data_quality;
  const replay = reports?.replay;
  const noEntry = reports?.no_entry;

  return (
    <div className="flex flex-col gap-3">
      <SectionPanel title="Research Terminal" subtitle="Read-only offline evidence from replay, no-entry, session, data-quality, and compact research state reports.">
        {stateQuery.isError ? (
          <EmptyState label="Research analytics unavailable because dashboard state could not be loaded." />
        ) : (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 md:grid-cols-2 min-[1600px]:grid-cols-4 gap-3">
              <MetricCard label="Research Status" value={research?.status ?? "MISSING"} helper="dashboard state" tone={research?.status === "OK" ? "good" : research?.status === "PARTIAL" ? "warn" : "bad"} />
              <MetricCard label="Replay Confidence" value={latest?.latest_replay_confidence ?? "n/a"} helper="latest compact state" />
              <MetricCard label="Direct Field Rate" value={formatPercent(latest?.direct_field_rate)} helper="compact state" />
              <MetricCard label="Unknown Lifecycle" value={formatPercent(latest?.unknown_lifecycle_rate)} helper="compact state" />
            </div>

            <div className="grid grid-cols-1 min-[1600px]:grid-cols-3 gap-4">
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Research State Summary</h3>
                <div className="grid grid-cols-1 gap-2 text-[13px] font-mono text-black">
                  <div><span className="font-bold text-[#404040]">latest_run_id:</span> {latest?.latest_run_id ?? "n/a"}</div>
                  <div><span className="font-bold text-[#404040]">replay_truth:</span> {latest?.replay_truth_maturity ?? "n/a"}</div>
                  <div><span className="font-bold text-[#404040]">direct_fields:</span> {latest?.direct_field_maturity ?? "n/a"}</div>
                  <div><span className="font-bold text-[#404040]">proxy_rate:</span> {formatPercent(latest?.proxy_field_rate)}</div>
                </div>
              </div>

              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm min-[1600px]:col-span-2">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Recommended Next Step</h3>
                <p className="m-0 text-[14px] leading-relaxed text-[#404040]">
                  {latest?.recommended_next_step ?? "No compact research next step is available yet."}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 min-[1600px]:grid-cols-3 gap-4">
              <div>
                <h3 className="m-0 mb-2 text-[14px] font-bold uppercase tracking-wider text-black">Candidate Loss Reasons</h3>
                <DataTable rows={reasonRows(research?.candidate_loss_reasons)} columns={[{ key: "name", label: "Reason" }, { key: "count", label: "Count" }]} empty="No candidate loss reasons available." />
              </div>
              <div>
                <h3 className="m-0 mb-2 text-[14px] font-bold uppercase tracking-wider text-black">Lifecycle Bottlenecks</h3>
                <DataTable rows={reasonRows(research?.lifecycle_bottlenecks)} columns={[{ key: "name", label: "Bottleneck" }, { key: "count", label: "Count" }]} empty="No lifecycle bottlenecks available." />
              </div>
              <div>
                <h3 className="m-0 mb-2 text-[14px] font-bold uppercase tracking-wider text-black">EV Null Reasons</h3>
                <DataTable rows={reasonRows(research?.ev_null_reasons)} columns={[{ key: "name", label: "Reason" }, { key: "count", label: "Count" }]} empty="No EV null reasons available." />
              </div>
            </div>

            <div className="grid grid-cols-1 min-[1600px]:grid-cols-2 gap-4">
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Replay / No-Entry Snapshot</h3>
                <div className="grid grid-cols-2 gap-3">
                  <MetricCard label="Replay Trades" value={firstReportValue(replay, "total_trades")} helper={`PnL ${formatNumber(replay?.gross_pnl)}`} />
                  <MetricCard label="Replay Win Rate" value={formatPercent(replay?.win_rate)} helper={`${firstReportValue(replay, "wins")}W / ${firstReportValue(replay, "losses")}L`} />
                  <MetricCard label="No Entry Root" value={firstReportValue(noEntry, "root_cause_category")} helper="latest no-entry report" />
                  <MetricCard label="Scanned / Skipped" value={`${firstReportValue(noEntry, "total_scanned")} / ${firstReportValue(noEntry, "total_skipped")}`} helper="no-entry funnel" />
                </div>
              </div>

              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Data Quality / Report Availability</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                  <MetricCard label="Quality OK" value={String(dataQuality?.ok ?? "n/a")} helper="latest quality report" tone={dataQuality?.ok === true ? "good" : dataQuality?.ok === false ? "warn" : "neutral"} />
                  <MetricCard label="Bad JSON" value={firstReportValue(dataQuality, "bad_json_lines")} helper={`${firstReportValue(dataQuality, "files_scanned")} files`} />
                  <MetricCard label="Replay Continuity" value={firstReportValue(dataQuality, "replay_continuity_status")} helper="quality report" />
                </div>
                <DataTable rows={reportStatusRows(reports)} columns={[{ key: "report", label: "Report" }, { key: "status", label: "Status" }, { key: "source", label: "Source" }]} empty="No report availability data." />
              </div>
            </div>

            <div className="grid grid-cols-1 min-[1600px]:grid-cols-2 gap-4">
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Blind Spots</h3>
                {latest?.blind_spots?.length ? (
                  <ul className="m-0 pl-5 text-[13px] leading-relaxed text-[#404040]">
                    {latest.blind_spots.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                ) : (
                  <EmptyState label="No compact research blind spots found." />
                )}
              </div>

              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Research Alerts</h3>
                {research?.alerts?.length ? (
                  <DataTable rows={research.alerts as unknown as Record<string, unknown>[]} columns={[{ key: "code", label: "Code" }, { key: "message", label: "Message" }]} empty="No research alerts." />
                ) : (
                  <EmptyState label="No research analytics parser alerts." />
                )}
              </div>
            </div>
          </div>
        )}
      </SectionPanel>

      <SectionPanel title="Research Roadmap" subtitle="Read-only future analytics workbench placeholders.">
        <div className="grid grid-cols-1 min-[1200px]:grid-cols-2 gap-4">
          {researchRoadmap.map((item) => (
            <div key={item.title} className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
              <div className="flex items-start justify-between gap-3 mb-3">
                <h3 className="m-0 text-[15px] font-bold text-black">{item.title}</h3>
                <span className="shrink-0 text-[11px] font-mono font-semibold uppercase text-[#666666] border border-[#d9d9d9] bg-[#f7f7f7] rounded px-2 py-1">
                  {item.status}
                </span>
              </div>
              <p className="m-0 text-[13px] leading-relaxed text-[#404040]">{item.description}</p>
            </div>
          ))}
        </div>
      </SectionPanel>
    </div>
  );
}
