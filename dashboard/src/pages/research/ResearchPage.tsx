import { MetricCard } from "../../components/cards/MetricCard";
import { DataTable } from "../../components/common/DataTable";
import { EmptyState } from "../../components/common/EmptyState";
import { SectionPanel } from "../../components/common/SectionPanel";
import { useDashboardState } from "../../hooks/useDashboardState";
import { formatCurrency, formatNumber, formatPercent } from "../../utils/formatters";

const researchRoadmap = [
  {
    title: "Replay Analytics",
    description: "Closed-trade replay, attribution review, lifecycle truth checks, and replay-key coverage.",
    status: "active v1",
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

  const replayAnalytics = research?.replay_analytics;
  const summary = replayAnalytics?.summary;
  const opportunity = replayAnalytics?.opportunity_cost;
  const funnel = replayAnalytics?.lifecycle_funnel;

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

      <SectionPanel title="Replay Analytics V1" subtitle="Attribution review, lifecycle truth checks, opportunity costs, and trade-level replay evidence.">
        {!replayAnalytics || replayAnalytics.status === "MISSING" ? (
          <EmptyState label="No replay analytics data is available. Ensure latest replay report exists." />
        ) : (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 md:grid-cols-2 min-[1600px]:grid-cols-4 gap-3">
              <MetricCard
                label="Replay Status"
                value={replayAnalytics.status ?? "n/a"}
                helper="latest report"
                tone={replayAnalytics.status === "OK" ? "good" : "warn"}
              />
              <MetricCard
                label="Trades / Win Rate"
                value={`${summary?.trades ?? 0} trades`}
                helper={`Win Rate: ${formatPercent(summary?.win_rate)} (${summary?.wins ?? 0}W / ${summary?.losses ?? 0}L)`}
                tone={(summary?.win_rate ?? 0) >= 0.5 ? "good" : (summary?.win_rate ?? 0) > 0 ? "warn" : "neutral"}
              />
              <MetricCard
                label="Net Replay PnL"
                value={formatCurrency(summary?.net_pnl)}
                helper={`Profit Factor: ${summary?.profit_factor ?? "n/a"}`}
                tone={(summary?.net_pnl ?? 0) > 0 ? "good" : (summary?.net_pnl ?? 0) < 0 ? "bad" : "neutral"}
              />
              <MetricCard
                label="Avg Holding Time"
                value={replay?.average_holding_time_seconds ? `${formatNumber(replay.average_holding_time_seconds, 1)}s` : "n/a"}
                helper="seconds"
              />
            </div>

            <div className="grid grid-cols-1 min-[1600px]:grid-cols-3 gap-4">
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm min-[1600px]:col-span-2">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Lifecycle Stage Funnel</h3>
                <div className="flex flex-col md:flex-row items-stretch justify-between gap-3 text-mono text-[12px] text-black">
                  <div className="flex-1 p-2.5 border border-[#d9d9d9] text-center bg-[#f9f9f9] flex flex-col justify-center">
                    <div className="font-bold text-[#666666] text-[10px] uppercase">Candidates</div>
                    <div className="text-lg font-bold mt-1 font-mono">{funnel?.candidates ?? 0}</div>
                    <span className="text-[9px] text-[#666666] mt-0.5">Scanned</span>
                  </div>
                  <div className="flex items-center justify-center text-[#666666] font-bold font-mono self-center">➔</div>
                  <div className="flex-1 p-2.5 border border-[#d9d9d9] text-center bg-[#f9f9f9] flex flex-col justify-center">
                    <div className="font-bold text-[#666666] text-[10px] uppercase">Signals</div>
                    <div className="text-lg font-bold mt-1 font-mono">{funnel?.signals ?? 0}</div>
                    <div className="text-[9px] text-[#008f39] font-bold mt-0.5">
                      {funnel?.candidates ? ((funnel.signals! / funnel.candidates!) * 100).toFixed(1) : 0}% yield
                    </div>
                  </div>
                  <div className="flex items-center justify-center text-[#666666] font-bold font-mono self-center">➔</div>
                  <div className="flex-1 p-2.5 border border-[#d9d9d9] text-center bg-[#f9f9f9] flex flex-col justify-center">
                    <div className="font-bold text-[#666666] text-[10px] uppercase">Risk Passed</div>
                    <div className="text-lg font-bold mt-1 font-mono">{funnel?.risk_pass ?? 0}</div>
                    <div className="text-[9px] text-[#008f39] font-bold mt-0.5">
                      {funnel?.signals ? ((funnel.risk_pass! / funnel.signals!) * 100).toFixed(1) : 0}% yield
                    </div>
                  </div>
                  <div className="flex items-center justify-center text-[#666666] font-bold font-mono self-center">➔</div>
                  <div className={`flex-1 p-2.5 border text-center flex flex-col justify-center ${funnel?.entries ? "border-[#008f39] bg-[#e6f4ea]/10" : "border-[#d9d9d9] bg-[#f9f9f9]"}`}>
                    <div className={`font-bold text-[10px] uppercase ${funnel?.entries ? "text-[#008f39]" : "text-[#666666]"}`}>Entries</div>
                    <div className={`text-lg font-bold mt-1 font-mono ${funnel?.entries ? "text-[#008f39]" : "text-black"}`}>{funnel?.entries ?? 0}</div>
                    <div className="text-[9px] text-[#008f39] font-bold mt-0.5">
                      {funnel?.candidates ? ((funnel.entries! / funnel.candidates!) * 100).toFixed(1) : 0}% total
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm font-mono text-[12px] text-black">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2 font-sans">Opportunity Cost (Timing)</h3>
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between">
                    <span className="text-[#666666]">Avg Seconds Remaining:</span>
                    <span className="font-bold">{String(opportunity?.timing_decay?.avg_seconds_remaining ?? "n/a")}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666666]">Min Seconds Remaining:</span>
                    <span className="font-bold">{String(opportunity?.timing_decay?.min_seconds_remaining ?? "n/a")}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666666]">Max Seconds Remaining:</span>
                    <span className="font-bold">{String(opportunity?.timing_decay?.max_seconds_remaining ?? "n/a")}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666666]">First Seen:</span>
                    <span className="font-bold">{String(opportunity?.timing_decay?.first_seen_seconds_remaining ?? "n/a")}s</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 min-[1600px]:grid-cols-2 gap-4">
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Skip Reason Cost</h3>
                <DataTable
                  rows={(opportunity?.top_skip_reasons ?? []).map(([reason, count]) => ({ reason, count }))}
                  columns={[{ key: "reason", label: "Reason" }, { key: "count", label: "Count" }]}
                  empty="No skip reason opportunity costs."
                />
              </div>

              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Session Breakdown</h3>
                <DataTable
                  rows={(replayAnalytics.session_breakdown ?? []).map((row) => ({
                    ...row,
                    pnl: formatCurrency(row.pnl)
                  }))}
                  columns={[
                    { key: "date", label: "Date / Run" },
                    { key: "verdict", label: "Verdict" },
                    { key: "trades", label: "Trades" },
                    { key: "pnl", label: "PnL ($)" },
                    { key: "bottleneck", label: "Bottleneck" }
                  ]}
                  empty="No session breakdown history."
                />
              </div>
            </div>

            <div className="grid grid-cols-1 min-[1600px]:grid-cols-2 gap-4">
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-[#008f39] border-b border-[#d9d9d9] pb-2">Top Winners</h3>
                <DataTable
                  rows={(replayAnalytics.top_winners ?? []).map((row) => ({
                    ...row,
                    pnl: formatCurrency(row.pnl),
                    timestamp_utc: row.timestamp_utc ? row.timestamp_utc.split("T").pop()?.slice(0, 8) : "n/a"
                  }))}
                  columns={[
                    { key: "timestamp_utc", label: "Time" },
                    { key: "asset", label: "Asset" },
                    { key: "outcome", label: "Outcome" },
                    { key: "pnl", label: "PnL ($)" }
                  ]}
                  empty="No winning trades."
                />
              </div>

              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-[#c62828] border-b border-[#d9d9d9] pb-2">Top Losers</h3>
                <DataTable
                  rows={(replayAnalytics.top_losers ?? []).map((row) => ({
                    ...row,
                    pnl: formatCurrency(row.pnl),
                    timestamp_utc: row.timestamp_utc ? row.timestamp_utc.split("T").pop()?.slice(0, 8) : "n/a"
                  }))}
                  columns={[
                    { key: "timestamp_utc", label: "Time" },
                    { key: "asset", label: "Asset" },
                    { key: "outcome", label: "Outcome" },
                    { key: "pnl", label: "PnL ($)" }
                  ]}
                  empty="No losing trades."
                />
              </div>
            </div>

            <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
              <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Evidence Table</h3>
              <div className="overflow-x-auto">
                <DataTable
                  rows={(replayAnalytics.evidence_table ?? []).map((row) => ({
                    ...row,
                    pnl: formatCurrency(row.pnl),
                    holding_seconds: row.holding_seconds ? `${row.holding_seconds.toFixed(1)}s` : "n/a"
                  }))}
                  columns={[
                    { key: "timestamp_utc", label: "Time (UTC)" },
                    { key: "asset", label: "Asset" },
                    { key: "side", label: "Side" },
                    { key: "signal", label: "Signal" },
                    { key: "holding_seconds", label: "Holding" },
                    { key: "outcome", label: "Outcome" },
                    { key: "pnl", label: "PnL ($)" }
                  ]}
                  empty="No trade evidence in latest report."
                />
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
