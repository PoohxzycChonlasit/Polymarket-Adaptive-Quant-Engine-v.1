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
    status: "active v1",
  },
  {
    title: "No Entry Analytics",
    description: "Zero-trade diagnostics, root cause attribution, operational blocks, and capital protection details.",
    status: "active v1",
  },
  {
    title: "Candidate Lifecycle Analytics",
    description: "Stage-by-stage candidate survival rates, drop-off points, and operational kill reasons.",
    status: "active v1",
  },
  {
    title: "Regime Analytics",
    description: "Market regime breakdowns, signal performance by regime, and volatility-state comparisons.",
    status: "active v1",
  },
  {
    title: "MAE/MFE Analytics",
    description: "Hold-time expectancy, exit excursion proxies, profit factor, exit-reason distribution, and regime/side/asset breakdowns.",
    status: "active v1",
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

  const noEntryAnalytics = research?.no_entry_analytics;
  const noEntrySummary = noEntryAnalytics?.summary;
  const timingCutoff = noEntryAnalytics?.timing_cutoff;
  const riskZero = noEntryAnalytics?.risk_zero;
  const liquidity = noEntryAnalytics?.liquidity;
  const evMissing = noEntryAnalytics?.ev_missing;

  const sessionAnalytics = research?.session_analytics;
  const sessionSummary = sessionAnalytics?.summary;

  const lifecycleAnalytics = research?.lifecycle_analytics;
  const lifecycleSummary = lifecycleAnalytics?.summary;

  const regimeAnalytics = research?.regime_analytics;
  const regimeSummary = regimeAnalytics?.summary;

  const maeMfe = research?.mae_mfe_analytics;
  const maeMfeSummary = maeMfe?.summary;

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

      <SectionPanel title="No Entry Analytics V1" subtitle="Zero-trade diagnostics, root cause attribution, operational blocks, and capital protection details.">
        {!noEntryAnalytics || noEntryAnalytics.status === "MISSING" ? (
          <EmptyState label="No entry analytics data is available. Ensure latest no-entry report exists." />
        ) : (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 md:grid-cols-2 min-[1600px]:grid-cols-4 gap-3">
              <MetricCard
                label="No Entry Status"
                value={noEntryAnalytics.status ?? "n/a"}
                helper="latest report status"
                tone={noEntryAnalytics.status === "OK" ? "good" : "warn"}
              />
              <MetricCard
                label="Total Candidates"
                value={formatNumber(noEntrySummary?.total_candidates)}
                helper="opportunities scanned"
              />
              <MetricCard
                label="Entries / Rate"
                value={`${noEntrySummary?.entries ?? 0} entries`}
                helper={`Entry Rate: ${formatPercent(noEntrySummary?.entry_rate)}`}
                tone={(noEntrySummary?.entries ?? 0) > 0 ? "warn" : "good"}
              />
              <MetricCard
                label="Dominant Blocker"
                value={String(research?.reports?.no_entry?.root_cause_category ?? "n/a").toUpperCase()}
                helper="primary bottleneck source"
                tone={research?.reports?.no_entry?.root_cause_category === "strategy" ? "good" : "bad"}
              />
            </div>

            <div className="grid grid-cols-1 min-[1600px]:grid-cols-3 gap-4">
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Root Cause Breakdown</h3>
                <div className="flex flex-col gap-3 font-mono text-[12px] text-black">
                  {(noEntryAnalytics.root_causes ?? []).map(([category, count]) => {
                    const total = noEntrySummary?.total_candidates ?? 1;
                    const pct = total > 0 ? (count / total) * 100 : 0;
                    return (
                      <div key={category} className="flex flex-col gap-1">
                        <div className="flex justify-between">
                          <span className="font-bold uppercase">{category}</span>
                          <span>{count} ({pct.toFixed(1)}%)</span>
                        </div>
                        <div className="w-full bg-[#f2f2f2] h-2 rounded border border-[#d9d9d9]">
                          <div
                            className="bg-[#000000] h-full rounded"
                            style={{ width: `${Math.min(100, pct)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                  {(!noEntryAnalytics.root_causes || noEntryAnalytics.root_causes.length === 0) && (
                    <div className="text-muted">No root cause counts available.</div>
                  )}
                </div>
              </div>

              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm min-[1600px]:col-span-2">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Recommended Investigation</h3>
                {noEntryAnalytics.recommended_investigation && noEntryAnalytics.recommended_investigation.length > 0 ? (
                  <ul className="m-0 pl-5 text-[13px] leading-relaxed text-[#404040] font-mono">
                    {noEntryAnalytics.recommended_investigation.map((rec, i) => (
                      <li key={i} className="mb-1">{rec}</li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-[#666666] text-[13px]">No recommendations available.</div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 min-[1600px]:grid-cols-2 gap-4">
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Blocker Category Table</h3>
                <DataTable
                  rows={(noEntryAnalytics.blocker_categories ?? []).map(([reason, count]) => {
                    const total = noEntrySummary?.total_candidates ?? 1;
                    return {
                      reason,
                      count,
                      percentage: formatPercent(total > 0 ? count / total : 0)
                    };
                  })}
                  columns={[
                    { key: "reason", label: "Reason Blocker" },
                    { key: "count", label: "Count" },
                    { key: "percentage", label: "% of Total" }
                  ]}
                  empty="No blockers recorded."
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm font-mono text-[12px] text-black">
                  <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2 font-sans">Timing Cutoff Panel</h3>
                  <div className="flex flex-col gap-2">
                    <div className="flex justify-between">
                      <span className="text-[#666666]">Time Unsafe Skips:</span>
                      <span className="font-bold">{timingCutoff?.count_time_unsafe ?? 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#666666]">Avg Seconds Remaining:</span>
                      <span className="font-bold">{timingCutoff?.avg_seconds_remaining ? `${timingCutoff.avg_seconds_remaining.toFixed(1)}s` : "n/a"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#666666]">Closest Seconds:</span>
                      <span className="font-bold">{timingCutoff?.closest_seconds_remaining ? `${timingCutoff.closest_seconds_remaining}s` : "n/a"}</span>
                    </div>
                    <div className="mt-2 pt-2 border-t border-[#d9d9d9]">
                      <div className="font-bold text-[#666666] mb-1 font-sans text-[10px] uppercase">Timing Buckets</div>
                      {Object.entries(timingCutoff?.timing_buckets ?? {}).map(([b, count]) => (
                        <div key={b} className="flex justify-between text-[11px] mt-0.5">
                          <span className="capitalize">{b}:</span>
                          <span>{String(count)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm font-mono text-[12px] text-black">
                  <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2 font-sans">Risk Zero Panel</h3>
                  <div className="flex flex-col gap-2">
                    <div className="flex justify-between">
                      <span className="text-[#666666]">Risk Plan Zero Skips:</span>
                      <span className="font-bold">{riskZero?.count_risk_plan_zero ?? 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#666666]">Bankroll Tier Name:</span>
                      <span className="font-bold">{riskZero?.bankroll_tier_name ?? "n/a"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#666666]">Bankroll Mode:</span>
                      <span className="font-bold">{riskZero?.bankroll_mode ?? "n/a"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#666666]">Micro Position Size:</span>
                      <span className="font-bold">{riskZero?.micro_position_size ? formatCurrency(riskZero.micro_position_size) : "n/a"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#666666]">Micro Survival Active:</span>
                      <span className="font-bold">{String(riskZero?.micro_survival_active ?? "false")}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 min-[1600px]:grid-cols-3 gap-4">
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm font-mono text-[12px] text-black">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2 font-sans">Liquidity Panel</h3>
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between">
                    <span className="text-[#666666]">Orderbook Unavailable Skips:</span>
                    <span className="font-bold">{liquidity?.count_orderbook_unavailable_or_stale ?? 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666666]">Avg Orderbook Age:</span>
                    <span className="font-bold">{liquidity?.average_orderbook_age_ms ? `${liquidity.average_orderbook_age_ms.toFixed(1)}ms` : "n/a"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666666]">Token Mapping Warnings:</span>
                    <span className="font-bold text-[#c62828]">{liquidity?.token_mapping_warning_count ?? 0}</span>
                  </div>
                </div>
              </div>

              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm font-mono text-[12px] text-black">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2 font-sans">EV Missing Panel</h3>
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between">
                    <span className="text-[#666666]">Missing Prob Model Skips:</span>
                    <span className="font-bold">{evMissing?.no_probability_model_output ?? 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666666]">Missing Market Price Skips:</span>
                    <span className="font-bold">{evMissing?.no_market_price ?? 0}</span>
                  </div>
                </div>
              </div>

              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">CLOB Error Panel</h3>
                <DataTable
                  rows={Object.entries(noEntryAnalytics.clob_errors ?? {}).map(([error, count]) => ({ error, count }))}
                  columns={[
                    { key: "error", label: "CLOB Error Category" },
                    { key: "count", label: "Count" }
                  ]}
                  empty="No CLOB errors recorded."
                />
              </div>
            </div>
          </div>
        )}
      </SectionPanel>

      <SectionPanel title="Session Analytics V1" subtitle="Multi-session performance, leaderboard, entry yield, no-entry rate, risk rejection, and expectancy trends.">
        {!sessionAnalytics || sessionAnalytics.status === "MISSING" ? (
          <EmptyState label="No session analytics data is available. Ensure latest session runtime evaluation report exists." />
        ) : (
          <div className="flex flex-col gap-4">
            {/* Session Summary Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 min-[1600px]:grid-cols-4 gap-3">
              <MetricCard
                label="Best Session"
                value={sessionSummary?.best_session || "n/a"}
                helper="by net realized PnL"
                tone={(sessionSummary?.best_session && !sessionSummary.best_session.includes("$-")) ? "good" : "neutral"}
              />
              <MetricCard
                label="Worst Session"
                value={sessionSummary?.worst_session || "n/a"}
                helper="by net realized PnL"
                tone={(sessionSummary?.worst_session && sessionSummary.worst_session.includes("$-")) ? "bad" : "neutral"}
              />
              <MetricCard
                label="Highest Entry Rate"
                value={sessionSummary?.highest_entry_rate_session || "n/a"}
                helper="session date & rate"
              />
              <MetricCard
                label="Highest No-Entry Rate"
                value={sessionSummary?.highest_no_entry_session || "n/a"}
                helper="session date & skipped rate"
              />
            </div>

            {/* Session Leaderboard */}
            <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
              <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Session Leaderboard</h3>
              <div className="overflow-x-auto">
                <DataTable
                  rows={(sessionAnalytics.leaderboard ?? []).map((row) => ({
                    ...row,
                    net_pnl: formatCurrency(row.net_pnl),
                    win_rate: formatPercent(row.win_rate),
                    entry_rate: formatPercent(row.entry_rate),
                    expectancy: formatNumber(row.expectancy, 4),
                  }))}
                  columns={[
                    { key: "date", label: "Session Date" },
                    { key: "trades", label: "Trades" },
                    { key: "win_rate", label: "Win Rate" },
                    { key: "net_pnl", label: "PnL ($)" },
                    { key: "profit_factor", label: "Profit Factor" },
                    { key: "entry_rate", label: "Entry Rate" },
                    { key: "risk_rejects", label: "Risk Rejects" },
                    { key: "expectancy", label: "Expectancy" },
                    { key: "primary_bottleneck", label: "Primary Blocker" },
                    { key: "verdict", label: "Verdict" },
                  ]}
                  empty="No sessions recorded in leaderboard."
                />
              </div>
            </div>

            {/* Rates breakdown panels */}
            <div className="grid grid-cols-1 md:grid-cols-2 min-[1600px]:grid-cols-4 gap-4">
              {/* Entry Rate by Session */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Entry Rate By Session</h3>
                <DataTable
                  rows={(sessionAnalytics.entry_rate ?? []).map((row) => ({
                    ...row,
                    entry_rate: formatPercent(row.entry_rate),
                  }))}
                  columns={[
                    { key: "date", label: "Date" },
                    { key: "entry_rate", label: "Entry Rate" },
                  ]}
                  empty="No entry rate data available."
                />
              </div>

              {/* No Entry By Session */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">No Entry By Session</h3>
                <DataTable
                  rows={(sessionAnalytics.no_entry_rate ?? []).map((row) => ({
                    ...row,
                    no_entry_rate: formatPercent(row.no_entry_rate),
                  }))}
                  columns={[
                    { key: "date", label: "Date" },
                    { key: "no_entry_rate", label: "No-Entry Rate" },
                  ]}
                  empty="No no-entry rate data available."
                />
              </div>

              {/* Risk Reject By Session */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Risk Reject By Session</h3>
                <DataTable
                  rows={(sessionAnalytics.risk_reject_rate ?? []).map((row) => ({
                    ...row,
                    risk_reject_rate: formatPercent(row.risk_reject_rate),
                  }))}
                  columns={[
                    { key: "date", label: "Date" },
                    { key: "risk_reject_rate", label: "Risk Reject Rate" },
                  ]}
                  empty="No risk reject rate data available."
                />
              </div>

              {/* Expectancy By Session */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Expectancy By Session</h3>
                <DataTable
                  rows={(sessionAnalytics.expectancy ?? []).map((row) => ({
                    ...row,
                    expectancy: formatNumber(row.expectancy, 4),
                  }))}
                  columns={[
                    { key: "date", label: "Date" },
                    { key: "expectancy", label: "Expectancy" },
                  ]}
                  empty="No expectancy data available."
                />
              </div>
            </div>

            {/* Recommendations Panels */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-[#008f39] border-b border-[#d9d9d9] pb-2">Recommended Sessions</h3>
                {sessionAnalytics.recommended_sessions?.length ? (
                  <div className="flex flex-col gap-2">
                    {sessionAnalytics.recommended_sessions.map((rec) => (
                      <div key={rec.date} className="p-2 border border-[#d9d9d9] bg-[#e6f4ea]/10 rounded">
                        <div className="font-bold text-[13px] text-[#008f39] font-mono">{rec.date}</div>
                        <div className="text-[12px] text-[#404040] mt-1">{rec.reason}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState label="No recommended sessions found." />
                )}
              </div>

              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-[#c62828] border-b border-[#d9d9d9] pb-2">Sessions to Avoid</h3>
                {sessionAnalytics.sessions_to_avoid?.length ? (
                  <div className="flex flex-col gap-2">
                    {sessionAnalytics.sessions_to_avoid.map((rec) => (
                      <div key={rec.date} className="p-2 border border-[#d9d9d9] bg-[#fde8e8]/20 rounded">
                        <div className="font-bold text-[13px] text-[#c62828] font-mono">{rec.date}</div>
                        <div className="text-[12px] text-[#404040] mt-1">{rec.reason}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState label="No sessions to avoid found." />
                )}
              </div>
            </div>
          </div>
        )}
      </SectionPanel>

      <SectionPanel title="Candidate Lifecycle Analytics V1" subtitle="Stage-by-stage candidate throughput, survival rates, blocker attribution, and kill reasons.">
        {!lifecycleAnalytics || lifecycleAnalytics.status === "MISSING" ? (
          <EmptyState label="No candidate lifecycle analytics data is available. Ensure latest reports exist." />
        ) : (
          <div className="flex flex-col gap-4">
            {/* Lifecycle Summary Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 min-[1600px]:grid-cols-4 gap-3">
              <MetricCard
                label="Total Scanned Candidates"
                value={formatNumber(lifecycleSummary?.candidate_count)}
                helper="opportunities detected"
              />
              <MetricCard
                label="Throughput / Exit Volume"
                value={`${lifecycleSummary?.exit_count ?? 0} exits`}
                helper={`Throughput Rate: ${lifecycleSummary?.candidate_count ? ((lifecycleSummary.exit_count! / lifecycleSummary.candidate_count!) * 100).toFixed(2) : 0}%`}
                tone={(lifecycleSummary?.exit_count ?? 0) > 0 ? "good" : "neutral"}
              />
              <MetricCard
                label="Risk Approved Candidates"
                value={formatNumber(lifecycleSummary?.risk_pass_count)}
                helper={`${lifecycleSummary?.ev_pass_count ?? 0} EV passes`}
              />
              <MetricCard
                label="Execution Transmission Fills"
                value={formatNumber(lifecycleSummary?.entry_count)}
                helper={`${lifecycleSummary?.execution_pass_count ?? 0} CLOB attempts`}
              />
            </div>

            {/* Lifecycle Funnel Layout */}
            <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
              <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Lifecycle Stage Funnel</h3>
              <div className="flex flex-col md:flex-row items-stretch justify-between gap-3 text-mono text-[12px] text-black">
                {(lifecycleAnalytics.funnel ?? []).map((row, index, arr) => (
                  <div key={row.stage} className="flex flex-col md:flex-row flex-1 items-stretch gap-2">
                    <div className="flex-1 p-2.5 border border-[#d9d9d9] text-center bg-[#f9f9f9] flex flex-col justify-center rounded">
                      <div className="font-bold text-[#666666] text-[10px] uppercase">{row.stage}</div>
                      <div className="text-lg font-bold mt-1 font-mono">{formatNumber(row.count)}</div>
                      <span className="text-[9px] text-[#008f39] font-bold mt-0.5">{row.yield.toFixed(1)}% yield</span>
                    </div>
                    {index < arr.length - 1 && (
                      <div className="flex items-center justify-center text-[#666666] font-bold font-mono self-center">➔</div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Stage Losses & Top Kill Reasons */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Stage Losses */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Stage Loss Attribution</h3>
                <DataTable
                  rows={(lifecycleAnalytics.stage_losses ?? []).map((row) => {
                    const total = lifecycleSummary?.candidate_count ?? 1;
                    const pct = total > 0 ? (row.lost / total) * 100 : 0;
                    return {
                      ...row,
                      lost_count: formatNumber(row.lost),
                      percentage: `${pct.toFixed(1)}%`
                    };
                  })}
                  columns={[
                    { key: "stage", label: "Pipeline Filter Stage" },
                    { key: "lost_count", label: "Candidates Lost" },
                    { key: "percentage", label: "% of Total Candidates" }
                  ]}
                  empty="No stage losses recorded."
                />
              </div>

              {/* Top Kill Reasons */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Top Kill Reasons</h3>
                <DataTable
                  rows={(lifecycleAnalytics.top_kill_reasons ?? []).map((row) => ({
                    ...row,
                    count: formatNumber(row.count)
                  }))}
                  columns={[
                    { key: "reason", label: "Operational Skip/Block Reason" },
                    { key: "count", label: "Count" }
                  ]}
                  empty="No kill reasons recorded."
                />
              </div>
            </div>

            {/* Opportunity Cost & Leaderboard */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Opportunity Cost */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Opportunity Cost By Block Reason</h3>
                <DataTable
                  rows={(lifecycleAnalytics.opportunity_cost ?? []).map((row) => ({
                    ...row,
                    lost_candidates: formatNumber(row.lost_candidates)
                  }))}
                  columns={[
                    { key: "reason", label: "Block Reason" },
                    { key: "lost_candidates", label: "Missed Candidate Opportunities" }
                  ]}
                  empty="No opportunity cost records."
                />
              </div>

              {/* Lifecycle Leaderboard */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Lifecycle History Leaderboard</h3>
                <DataTable
                  rows={(lifecycleAnalytics.leaderboard ?? []).map((row) => ({
                    ...row,
                    scanned: formatNumber(row.scanned),
                    entries: formatNumber(row.entries),
                    throughput_rate: formatPercent(row.throughput_rate),
                    dominant_blocker: row.dominant_blocker.toUpperCase()
                  }))}
                  columns={[
                    { key: "date", label: "Session Date" },
                    { key: "scanned", label: "Scanned" },
                    { key: "entries", label: "Entries" },
                    { key: "throughput_rate", label: "Throughput Rate" },
                    { key: "dominant_blocker", label: "Dominant Blocker" }
                  ]}
                  empty="No lifecycle history leaderboard."
                />
              </div>
            </div>
          </div>
        )}
      </SectionPanel>

      <SectionPanel title="Regime Analytics V1" subtitle="Breakdown of system throughput, risk rejections, expectancy, and PnL by market regime.">
        {!regimeAnalytics || regimeAnalytics.status === "MISSING" ? (
          <EmptyState label="No regime analytics data is available. Ensure valid reports exist." />
        ) : (
          <div className="flex flex-col gap-4">
            {/* Regime Summary KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 min-[1600px]:grid-cols-5 gap-3">
              <MetricCard
                label="Best Performing Regime"
                value={regimeSummary?.best_regime || "N/A"}
                helper="by net PnL"
                tone="good"
              />
              <MetricCard
                label="Worst Performing Regime"
                value={regimeSummary?.worst_regime || "N/A"}
                helper="by net PnL"
                tone="bad"
              />
              <MetricCard
                label="Highest Entry Rate"
                value={regimeSummary?.highest_entry_rate_regime || "N/A"}
                helper="max entries / scanned"
              />
              <MetricCard
                label="Highest No-Entry Rate"
                value={regimeSummary?.highest_no_entry_regime || "N/A"}
                helper="max skips / scanned"
              />
              <MetricCard
                label="Highest Risk Rejections"
                value={regimeSummary?.highest_risk_reject_regime || "N/A"}
                helper="max risk rejects"
              />
            </div>

            {/* Regime Leaderboard */}
            <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
              <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Regime Leaderboard</h3>
              <DataTable
                rows={(regimeAnalytics.leaderboard ?? []).map((row) => ({
                  ...row,
                  scanned: formatNumber(row.scanned),
                  entries: formatNumber(row.entries),
                  entry_rate: formatPercent(row.entry_rate),
                  no_entries: formatNumber(row.no_entries),
                  no_entry_rate: formatPercent(row.no_entry_rate),
                  risk_rejections: formatNumber(row.risk_rejections),
                  risk_rejection_rate: formatPercent(row.risk_rejection_rate),
                  net_pnl: `$${formatNumber(row.net_pnl, 2)}`,
                  expectancy: formatNumber(row.expectancy, 4),
                  win_rate: formatPercent(row.win_rate),
                  profit_factor: formatNumber(row.profit_factor, 2)
                }))}
                columns={[
                  { key: "regime", label: "Market Regime" },
                  { key: "scanned", label: "Scanned" },
                  { key: "entries", label: "Entries" },
                  { key: "entry_rate", label: "Entry Rate" },
                  { key: "no_entries", label: "No-Entries" },
                  { key: "no_entry_rate", label: "No-Entry Rate" },
                  { key: "risk_rejections", label: "Risk Rejections" },
                  { key: "risk_rejection_rate", label: "Risk Reject Rate" },
                  { key: "net_pnl", label: "Net PnL" },
                  { key: "expectancy", label: "Expectancy" },
                  { key: "win_rate", label: "Win Rate" },
                  { key: "profit_factor", label: "Profit Factor" },
                  { key: "verdict", label: "Verdict" }
                ]}
                empty="No regime leaderboard available."
              />
            </div>

            {/* Grid of Rates & Expectancy */}
            <div className="grid grid-cols-1 min-[1400px]:grid-cols-2 gap-4">
              {/* Entry Rate by Regime */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Entry Rate by Regime</h3>
                <DataTable
                  rows={(regimeAnalytics.entry_rate ?? []).map((row) => ({
                    ...row,
                    entry_rate: formatPercent(row.entry_rate),
                    entries: formatNumber(row.entries),
                    scanned: formatNumber(row.scanned)
                  }))}
                  columns={[
                    { key: "regime", label: "Market Regime" },
                    { key: "entry_rate", label: "Entry Rate" },
                    { key: "entries", label: "Entries" },
                    { key: "scanned", label: "Scanned" }
                  ]}
                  empty="No entry rate statistics available."
                />
              </div>

              {/* No Entry Rate by Regime */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">No-Entry Rate by Regime</h3>
                <DataTable
                  rows={(regimeAnalytics.no_entry_rate ?? []).map((row) => ({
                    ...row,
                    no_entry_rate: formatPercent(row.no_entry_rate),
                    no_entries: formatNumber(row.no_entries),
                    scanned: formatNumber(row.scanned)
                  }))}
                  columns={[
                    { key: "regime", label: "Market Regime" },
                    { key: "no_entry_rate", label: "No-Entry Rate" },
                    { key: "no_entries", label: "No-Entries" },
                    { key: "scanned", label: "Scanned" }
                  ]}
                  empty="No no-entry rate statistics available."
                />
              </div>
            </div>

            <div className="grid grid-cols-1 min-[1400px]:grid-cols-2 gap-4">
              {/* Risk Reject Rate by Regime */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Risk Rejection Rate by Regime</h3>
                <DataTable
                  rows={(regimeAnalytics.risk_reject_rate ?? []).map((row) => ({
                    ...row,
                    risk_rejection_rate: formatPercent(row.risk_rejection_rate),
                    rejections: formatNumber(row.rejections),
                    skipped: formatNumber(row.skipped)
                  }))}
                  columns={[
                    { key: "regime", label: "Market Regime" },
                    { key: "risk_rejection_rate", label: "Risk Reject Rate" },
                    { key: "rejections", label: "Rejections" },
                    { key: "skipped", label: "Skips" }
                  ]}
                  empty="No risk rejection rate statistics available."
                />
              </div>

              {/* Expectancy by Regime */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Expectancy by Regime</h3>
                <DataTable
                  rows={(regimeAnalytics.expectancy ?? []).map((row) => ({
                    ...row,
                    expectancy: formatNumber(row.expectancy, 4),
                    net_pnl: `$${formatNumber(row.net_pnl, 2)}`
                  }))}
                  columns={[
                    { key: "regime", label: "Market Regime" },
                    { key: "expectancy", label: "Expectancy" },
                    { key: "net_pnl", label: "Net PnL" }
                  ]}
                  empty="No expectancy statistics available."
                />
              </div>
            </div>

            {/* Candidate Loss & Recommendations */}
            <div className="grid grid-cols-1 min-[1400px]:grid-cols-2 gap-4">
              {/* Candidate Loss by Stage */}
              <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-black border-b border-[#d9d9d9] pb-2">Candidate Loss by Regime Stage</h3>
                <DataTable
                  rows={(regimeAnalytics.candidate_loss ?? []).map((row) => ({
                    ...row,
                    lost: formatNumber(row.lost)
                  }))}
                  columns={[
                    { key: "regime", label: "Market Regime" },
                    { key: "stage", label: "Pipeline Filter Stage" },
                    { key: "lost", label: "Candidates Lost" }
                  ]}
                  empty="No candidate loss data available."
                />
              </div>

              {/* Recommended & Avoid Regimes */}
              <div className="flex flex-col gap-4">
                <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm flex-1">
                  <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-[#008f39] border-b border-[#d9d9d9] pb-2">Recommended Regimes</h3>
                  {regimeAnalytics.recommended_regimes?.length ? (
                    <div className="flex flex-col gap-2">
                      {regimeAnalytics.recommended_regimes.map((rec) => (
                        <div key={rec.regime} className="p-2 border border-[#d9d9d9] bg-[#e6f4ea]/10 rounded">
                          <div className="font-bold text-[13px] text-[#008f39] font-mono">{rec.regime}</div>
                          <div className="text-[12px] text-[#404040] mt-1">{rec.reason}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState label="No recommended regimes found." />
                  )}
                </div>

                <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm flex-1">
                  <h3 className="m-0 mb-3 text-[14px] font-bold uppercase tracking-wider text-[#c62828] border-b border-[#d9d9d9] pb-2">Regimes to Avoid</h3>
                  {regimeAnalytics.avoid_regimes?.length ? (
                    <div className="flex flex-col gap-2">
                      {regimeAnalytics.avoid_regimes.map((rec) => (
                        <div key={rec.regime} className="p-2 border border-[#d9d9d9] bg-[#fde8e8]/20 rounded">
                          <div className="font-bold text-[13px] text-[#c62828] font-mono">{rec.regime}</div>
                          <div className="text-[12px] text-[#404040] mt-1">{rec.reason}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState label="No regimes to avoid found." />
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </SectionPanel>

      {/* ------------------------------------------------------------------ */}
      {/* MAE/MFE ANALYTICS V1                                                 */}
      {/* ------------------------------------------------------------------ */}
      <SectionPanel
        title="MAE/MFE Analytics V1"
        subtitle="Hold-time expectancy, exit excursion proxies, profit factor, and exit-reason breakdown. Read-only offline evidence — exit price minus entry price proxy only, no intra-trade tick MAE/MFE."
      >
        {!maeMfe || maeMfe.status === "MISSING" ? (
          <EmptyState label="MAE/MFE analytics unavailable. Ensure canonical_regime_enriched_trades_v1.csv exists in runtime/research_exports/." />
        ) : (
          <div className="flex flex-col gap-4">

            {/* Data warning note */}
            <div className="px-3 py-2 bg-[#F5F5F0] border border-[#D4C5A9] rounded text-[11px] text-[#6B6B8A] italic font-mono">
              ⚠ {maeMfe.data_warning} — Source: {maeMfe.source_csv?.split(/[\/\\]/).pop() ?? "n/a"} — {maeMfe.total_trades} canonical trades
            </div>

            {/* Summary metric cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 min-[1600px]:grid-cols-6 gap-3">
              <MetricCard
                label="MAE/MFE Status"
                value={maeMfe.status}
                helper="analytics status"
                tone={maeMfe.status === "OK" ? "good" : maeMfe.status === "PARTIAL" ? "warn" : "neutral"}
              />
              <MetricCard
                label="Total Trades"
                value={String(maeMfe.total_trades)}
                helper={`TP: ${maeMfeSummary?.tp_count ?? 0}  SL: ${maeMfeSummary?.sl_count ?? 0}`}
              />
              <MetricCard
                label="Win Rate"
                value={formatPercent(maeMfeSummary?.win_rate)}
                helper="winners / total"
                tone={(maeMfeSummary?.win_rate ?? 0) >= 0.5 ? "good" : (maeMfeSummary?.win_rate ?? 0) > 0 ? "warn" : "neutral"}
              />
              <MetricCard
                label="Profit Factor"
                value={maeMfeSummary?.profit_factor != null ? maeMfeSummary.profit_factor.toFixed(4) : "n/a"}
                helper="TP gross / SL gross"
                tone={(maeMfeSummary?.profit_factor ?? 0) >= 1.0 ? "good" : (maeMfeSummary?.profit_factor ?? 0) > 0 ? "bad" : "neutral"}
              />
              <MetricCard
                label="Avg Winner Hold"
                value={maeMfeSummary?.avg_winner_hold_s != null ? `${maeMfeSummary.avg_winner_hold_s.toFixed(1)}s` : "n/a"}
                helper="seconds"
                tone="good"
              />
              <MetricCard
                label="Avg Loser Hold"
                value={maeMfeSummary?.avg_loser_hold_s != null ? `${maeMfeSummary.avg_loser_hold_s.toFixed(1)}s` : "n/a"}
                helper="seconds"
                tone="bad"
              />
            </div>

            {/* Exit excursion proxies + Exit reason distribution */}
            <div className="grid grid-cols-1 min-[1600px]:grid-cols-2 gap-4">

              <div className="p-4 border border-[#D4C5A9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[13px] font-bold uppercase tracking-wider text-[#1A1A2E] border-b border-[#D4C5A9] pb-2">
                  Exit Excursion Proxies
                </h3>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div className="p-3 border border-[#D4C5A9] bg-[#F5F5F0] rounded">
                    <div className="text-[10px] font-bold uppercase text-[#006B3C] tracking-wider mb-1">MFE Proxy (Winners / TP)</div>
                    <div className="text-[11px] italic text-[#6B6B8A] mb-2">{maeMfe.mfe_proxy?.label}</div>
                    <div className="grid grid-cols-2 gap-1 text-[12px] font-mono">
                      <span className="text-[#5C4A1E]">Mean:</span>
                      <span className="font-bold text-[#006B3C]">{maeMfe.mfe_proxy?.winner_mean != null ? `+${maeMfe.mfe_proxy.winner_mean.toFixed(4)}` : "n/a"}</span>
                      <span className="text-[#5C4A1E]">Median:</span>
                      <span className="font-bold text-[#006B3C]">{maeMfe.mfe_proxy?.winner_median != null ? `+${maeMfe.mfe_proxy.winner_median.toFixed(4)}` : "n/a"}</span>
                      <span className="text-[#5C4A1E]">Max:</span>
                      <span className="font-bold">{maeMfe.mfe_proxy?.winner_max != null ? `+${maeMfe.mfe_proxy.winner_max.toFixed(4)}` : "n/a"}</span>
                      <span className="text-[#5C4A1E]">Min:</span>
                      <span className="font-bold">{maeMfe.mfe_proxy?.winner_min != null ? `+${maeMfe.mfe_proxy.winner_min.toFixed(4)}` : "n/a"}</span>
                      <span className="text-[#5C4A1E]">P25:</span>
                      <span className="font-bold">{maeMfe.mfe_proxy?.winner_p25 != null ? `+${maeMfe.mfe_proxy.winner_p25.toFixed(4)}` : "n/a"}</span>
                      <span className="text-[#5C4A1E]">P75:</span>
                      <span className="font-bold">{maeMfe.mfe_proxy?.winner_p75 != null ? `+${maeMfe.mfe_proxy.winner_p75.toFixed(4)}` : "n/a"}</span>
                    </div>
                  </div>

                  <div className="p-3 border border-[#D4C5A9] bg-[#F5F5F0] rounded">
                    <div className="text-[10px] font-bold uppercase text-[#8B0000] tracking-wider mb-1">MAE Proxy (Losers / SL)</div>
                    <div className="text-[11px] italic text-[#6B6B8A] mb-2">{maeMfe.mae_proxy?.label}</div>
                    <div className="grid grid-cols-2 gap-1 text-[12px] font-mono">
                      <span className="text-[#5C4A1E]">Mean:</span>
                      <span className="font-bold text-[#8B0000]">{maeMfe.mae_proxy?.loser_mean != null ? maeMfe.mae_proxy.loser_mean.toFixed(4) : "n/a"}</span>
                      <span className="text-[#5C4A1E]">Median:</span>
                      <span className="font-bold text-[#8B0000]">{maeMfe.mae_proxy?.loser_median != null ? maeMfe.mae_proxy.loser_median.toFixed(4) : "n/a"}</span>
                      <span className="text-[#5C4A1E]">Max:</span>
                      <span className="font-bold">{maeMfe.mae_proxy?.loser_max != null ? maeMfe.mae_proxy.loser_max.toFixed(4) : "n/a"}</span>
                      <span className="text-[#5C4A1E]">Min:</span>
                      <span className="font-bold">{maeMfe.mae_proxy?.loser_min != null ? maeMfe.mae_proxy.loser_min.toFixed(4) : "n/a"}</span>
                      <span className="text-[#5C4A1E]">P25:</span>
                      <span className="font-bold">{maeMfe.mae_proxy?.loser_p25 != null ? maeMfe.mae_proxy.loser_p25.toFixed(4) : "n/a"}</span>
                      <span className="text-[#5C4A1E]">P75:</span>
                      <span className="font-bold">{maeMfe.mae_proxy?.loser_p75 != null ? maeMfe.mae_proxy.loser_p75.toFixed(4) : "n/a"}</span>
                    </div>
                  </div>
                </div>

                {/* Avg winner/loser PnL row */}
                <div className="grid grid-cols-2 gap-3 mt-2">
                  <div className="p-2 border border-[#D4C5A9] bg-[#F5F5F0] rounded text-center">
                    <div className="text-[10px] uppercase text-[#006B3C] font-bold">Avg Winner PnL</div>
                    <div className="font-bold font-mono text-[14px] text-[#006B3C]">
                      {maeMfeSummary?.avg_winner_pnl != null ? formatCurrency(maeMfeSummary.avg_winner_pnl) : "n/a"}
                    </div>
                  </div>
                  <div className="p-2 border border-[#D4C5A9] bg-[#F5F5F0] rounded text-center">
                    <div className="text-[10px] uppercase text-[#8B0000] font-bold">Avg Loser PnL</div>
                    <div className="font-bold font-mono text-[14px] text-[#8B0000]">
                      {maeMfeSummary?.avg_loser_pnl != null ? formatCurrency(maeMfeSummary.avg_loser_pnl) : "n/a"}
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-4 border border-[#D4C5A9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[13px] font-bold uppercase tracking-wider text-[#1A1A2E] border-b border-[#D4C5A9] pb-2">
                  Exit Reason Distribution
                </h3>
                {maeMfe.exit_reason_distribution?.length ? (
                  <div className="flex flex-col gap-2">
                    {maeMfe.exit_reason_distribution.map((row) => (
                      <div key={row.reason} className="flex items-center gap-2">
                        <div className="flex-1">
                          <div className="flex justify-between text-[12px] font-mono mb-1">
                            <span className="text-[#1A1A2E] font-bold truncate max-w-[200px]" title={row.reason}>
                              {row.reason}
                            </span>
                            <span className={`font-bold shrink-0 ml-2 ${
                              row.reason === "take_profit_target_reached" ? "text-[#006B3C]" : "text-[#8B0000]"
                            }`}>
                              {row.count} ({(row.share * 100).toFixed(1)}%)
                            </span>
                          </div>
                          <div className="h-1.5 bg-[#F5F5F0] rounded overflow-hidden">
                            <div
                              className={`h-full rounded ${
                                row.reason === "take_profit_target_reached" ? "bg-[#006B3C]" : "bg-[#8B0000]"
                              }`}
                              style={{ width: `${(row.share * 100).toFixed(1)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState label="No exit reason data." />
                )}
              </div>
            </div>

            {/* Hold-time expectancy table */}
            <div className="p-4 border border-[#D4C5A9] bg-white rounded shadow-sm">
              <div className="flex items-center justify-between mb-3 border-b border-[#D4C5A9] pb-2">
                <h3 className="m-0 text-[13px] font-bold uppercase tracking-wider text-[#1A1A2E]">
                  Hold-Time Expectancy Table
                </h3>
                <div className="flex gap-2 text-[11px]">
                  {maeMfe.dominant_loss_bucket && (
                    <span className="px-2 py-0.5 bg-[#5C4A1E] text-white rounded font-mono font-bold">
                      ↓ Dominant Loss: {maeMfe.dominant_loss_bucket}
                    </span>
                  )}
                  {maeMfe.optimal_hold_bucket && (
                    <span className="px-2 py-0.5 bg-[#006B3C] text-white rounded font-mono font-bold">
                      ✓ Optimal: {maeMfe.optimal_hold_bucket}
                    </span>
                  )}
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-[12px] font-mono border-collapse">
                  <thead>
                    <tr className="bg-[#F5F5F0]">
                      <th className="text-left px-3 py-2 border border-[#D4C5A9] font-bold text-[#1A1A2E] text-[11px] uppercase">Bucket</th>
                      <th className="text-right px-3 py-2 border border-[#D4C5A9] font-bold text-[#1A1A2E] text-[11px] uppercase">n</th>
                      <th className="text-right px-3 py-2 border border-[#D4C5A9] font-bold text-[#1A1A2E] text-[11px] uppercase">Win%</th>
                      <th className="text-right px-3 py-2 border border-[#D4C5A9] font-bold text-[#1A1A2E] text-[11px] uppercase">Mean PnL</th>
                      <th className="text-right px-3 py-2 border border-[#D4C5A9] font-bold text-[#1A1A2E] text-[11px] uppercase">Total PnL</th>
                      <th className="text-right px-3 py-2 border border-[#D4C5A9] font-bold text-[#006B3C] text-[11px] uppercase">TP</th>
                      <th className="text-right px-3 py-2 border border-[#D4C5A9] font-bold text-[#8B0000] text-[11px] uppercase">SL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(maeMfe.hold_time_buckets ?? []).map((row) => {
                      const isLoss = (row.total_pnl ?? 0) < 0;
                      const isOptimal = row.bucket === maeMfe.optimal_hold_bucket;
                      const isDominantLoss = row.bucket === maeMfe.dominant_loss_bucket;
                      return (
                        <tr
                          key={row.bucket}
                          className={`border-b border-[#D4C5A9] ${
                            isOptimal ? "bg-[#e6f4ea]/40" : isDominantLoss ? "bg-[#fde8e8]/40" : isLoss ? "bg-[#fff8f8]" : "bg-white"
                          }`}
                        >
                          <td className={`px-3 py-2 border border-[#D4C5A9] font-bold ${
                            isOptimal ? "text-[#006B3C]" : isDominantLoss ? "text-[#8B0000]" : "text-[#1A1A2E]"
                          }`}>
                            {row.bucket}
                            {isOptimal && <span className="ml-1 text-[10px]">✓</span>}
                            {isDominantLoss && <span className="ml-1 text-[10px]">↓</span>}
                          </td>
                          <td className="px-3 py-2 border border-[#D4C5A9] text-right text-[#1A1A2E]">{row.n}</td>
                          <td className={`px-3 py-2 border border-[#D4C5A9] text-right font-bold ${
                            (row.win_rate ?? 0) >= 0.5 ? "text-[#006B3C]" : "text-[#8B0000]"
                          }`}>
                            {row.win_rate != null ? `${(row.win_rate * 100).toFixed(1)}%` : "n/a"}
                          </td>
                          <td className={`px-3 py-2 border border-[#D4C5A9] text-right font-bold ${
                            (row.mean_pnl ?? 0) >= 0 ? "text-[#006B3C]" : "text-[#8B0000]"
                          }`}>
                            {row.mean_pnl != null ? formatCurrency(row.mean_pnl) : "n/a"}
                          </td>
                          <td className={`px-3 py-2 border border-[#D4C5A9] text-right font-bold ${
                            (row.total_pnl ?? 0) >= 0 ? "text-[#006B3C]" : "text-[#8B0000]"
                          }`}>
                            {row.total_pnl != null ? formatCurrency(row.total_pnl) : "n/a"}
                          </td>
                          <td className="px-3 py-2 border border-[#D4C5A9] text-right text-[#006B3C] font-bold">{row.tp_count}</td>
                          <td className="px-3 py-2 border border-[#D4C5A9] text-right text-[#8B0000] font-bold">{row.sl_count}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {!maeMfe.hold_time_buckets?.length && <EmptyState label="No hold-time bucket data." />}
              </div>
            </div>

            {/* Regime / Side / Asset breakdowns */}
            <div className="grid grid-cols-1 min-[1600px]:grid-cols-3 gap-4">
              <div className="p-4 border border-[#D4C5A9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[13px] font-bold uppercase tracking-wider text-[#1A1A2E] border-b border-[#D4C5A9] pb-2">Regime Breakdown</h3>
                <DataTable
                  rows={(maeMfe.regime_breakdown ?? []).map((r) => ({
                    regime: r.regime ?? "—",
                    n: r.n,
                    win_rate: r.win_rate != null ? `${(r.win_rate * 100).toFixed(1)}%` : "n/a",
                    mean_pnl: r.mean_pnl != null ? formatCurrency(r.mean_pnl) : "n/a",
                    avg_hold_s: r.avg_hold_s != null ? `${r.avg_hold_s.toFixed(1)}s` : "n/a",
                  }))}
                  columns={[
                    { key: "regime", label: "Regime" },
                    { key: "n", label: "n" },
                    { key: "win_rate", label: "Win%" },
                    { key: "mean_pnl", label: "Mean PnL" },
                    { key: "avg_hold_s", label: "Avg Hold" },
                  ]}
                  empty="No regime breakdown."
                />
              </div>

              <div className="p-4 border border-[#D4C5A9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[13px] font-bold uppercase tracking-wider text-[#1A1A2E] border-b border-[#D4C5A9] pb-2">Side Breakdown (YES / NO)</h3>
                <DataTable
                  rows={(maeMfe.side_breakdown ?? []).map((r) => ({
                    side: r.side ?? "—",
                    n: r.n,
                    win_rate: r.win_rate != null ? `${(r.win_rate * 100).toFixed(1)}%` : "n/a",
                    mean_pnl: r.mean_pnl != null ? formatCurrency(r.mean_pnl) : "n/a",
                    avg_hold_s: r.avg_hold_s != null ? `${r.avg_hold_s.toFixed(1)}s` : "n/a",
                  }))}
                  columns={[
                    { key: "side", label: "Side" },
                    { key: "n", label: "n" },
                    { key: "win_rate", label: "Win%" },
                    { key: "mean_pnl", label: "Mean PnL" },
                    { key: "avg_hold_s", label: "Avg Hold" },
                  ]}
                  empty="No side breakdown."
                />
              </div>

              <div className="p-4 border border-[#D4C5A9] bg-white rounded shadow-sm">
                <h3 className="m-0 mb-3 text-[13px] font-bold uppercase tracking-wider text-[#1A1A2E] border-b border-[#D4C5A9] pb-2">Asset Breakdown (BTC / ETH)</h3>
                <DataTable
                  rows={(maeMfe.asset_breakdown ?? []).map((r) => ({
                    asset: r.asset ?? "—",
                    n: r.n,
                    win_rate: r.win_rate != null ? `${(r.win_rate * 100).toFixed(1)}%` : "n/a",
                    mean_pnl: r.mean_pnl != null ? formatCurrency(r.mean_pnl) : "n/a",
                    avg_hold_s: r.avg_hold_s != null ? `${r.avg_hold_s.toFixed(1)}s` : "n/a",
                  }))}
                  columns={[
                    { key: "asset", label: "Asset" },
                    { key: "n", label: "n" },
                    { key: "win_rate", label: "Win%" },
                    { key: "mean_pnl", label: "Mean PnL" },
                    { key: "avg_hold_s", label: "Avg Hold" },
                  ]}
                  empty="No asset breakdown."
                />
              </div>
            </div>

            {/* Verdict banner */}
            <div className={`p-4 border rounded ${
              maeMfe.verdict === "EXPECTANCY_POSITIVE"
                ? "border-[#006B3C] bg-[#e6f4ea]/30"
                : maeMfe.verdict === "EXPECTANCY_NEGATIVE"
                ? "border-[#8B0000] bg-[#fde8e8]/30"
                : "border-[#D4C5A9] bg-[#F5F5F0]"
            }`}>
              <div className={`text-[13px] font-bold font-mono uppercase tracking-wider mb-1 ${
                maeMfe.verdict === "EXPECTANCY_POSITIVE" ? "text-[#006B3C]" :
                maeMfe.verdict === "EXPECTANCY_NEGATIVE" ? "text-[#8B0000]" :
                "text-[#5C4A1E]"
              }`}>
                {maeMfe.verdict === "EXPECTANCY_POSITIVE" && "✓ "}
                {maeMfe.verdict === "EXPECTANCY_NEGATIVE" && "!! "}
                VERDICT: {maeMfe.verdict ?? "—"}
              </div>
              <div className="text-[12px] text-[#1A1A2E] leading-relaxed">{maeMfe.verdict_reason}</div>
              {maeMfe.alerts?.length ? (
                <div className="mt-2 text-[11px] text-[#6B6B8A] italic">
                  {maeMfe.alerts.join(" | ")}
                </div>
              ) : null}
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
