import { PieMetricChart } from "../../components/charts/chartPrimitives";
import { SkipReasonChart } from "../../components/charts/SkipReasonChart";
import { DataTable } from "../../components/common/DataTable";
import { SectionPanel } from "../../components/common/SectionPanel";
import type { DashboardState } from "../../types/dashboard";
import { entriesFromRecord, formatNumber, sumRecordValues } from "../../utils/formatters";
import { getValue } from "../../utils/guards";

export function SignalIntelligenceSection({ state }: { state?: DashboardState }) {
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

  const decisions = Number(funnel?.decision_count ?? 0);
  const skipCounts = funnel?.skip_reason_counts ?? {};
  let signalSkips = 0;
  let riskSkips = 0;

  Object.entries(skipCounts).forEach(([reason, count]) => {
    const cnt = Number(count) || 0;
    const lowerReason = reason.toLowerCase();
    const isRisk =
      lowerReason.includes("risk") ||
      lowerReason.includes("budget") ||
      lowerReason.includes("exposure") ||
      lowerReason.includes("lockdown") ||
      lowerReason.includes("reconciliation") ||
      lowerReason.includes("cooldown") ||
      lowerReason.includes("max_trades") ||
      lowerReason.includes("zero_size") ||
      lowerReason.includes("size_cap") ||
      lowerReason.includes("balance") ||
      lowerReason.includes("limit") ||
      lowerReason.includes("capital") ||
      lowerReason.includes("mismatch") ||
      lowerReason.includes("blocked") ||
      lowerReason.includes("risk_plan_zero") ||
      lowerReason.includes("risk_mode");

    if (isRisk) {
      riskSkips += cnt;
    } else {
      signalSkips += cnt;
    }
  });

  const signalPassed = Math.max(0, decisions - signalSkips);
  const riskPassed = Math.max(0, signalPassed - riskSkips);
  const entries = Number(state?.trades?.today?.trade_open_count ?? 0);
  const signalYield = decisions > 0 ? (signalPassed / decisions) * 100 : 0;
  const riskYield = signalPassed > 0 ? (riskPassed / signalPassed) * 100 : 0;
  const totalYield = decisions > 0 ? (entries / decisions) * 100 : 0;

  const funnelSteps = [
    { label: "Decisions", value: decisions, percent: 100, helper: "Total evaluations", tone: "neutral" },
    { label: "Signal Passed", value: signalPassed, percent: signalYield, helper: `${signalSkips} signal skips`, tone: signalSkips > 0 ? "bad" : "neutral" },
    { label: "Risk Passed", value: riskPassed, percent: riskYield, helper: `${riskSkips} risk skips`, tone: riskSkips > 0 ? "bad" : "neutral" },
    { label: "Entries", value: entries, percent: totalYield, helper: `${Math.max(0, riskPassed - entries)} post-risk drop`, tone: entries > 0 ? "good" : "neutral" },
  ];

  return (
    <SectionPanel title="Signal Intelligence" subtitle="Operator funnel, signal activity, and top skip bottlenecks.">
      <div className="grid grid-cols-1 min-[1600px]:grid-cols-4 gap-3 mb-4">
        {funnelSteps.map((step, index) => (
          <div key={step.label} className={`relative p-4 border-2 rounded bg-white shadow-sm ${index === funnelSteps.length - 1 ? "border-[#000000]" : "border-[#d9d9d9]"}`}>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[12px] font-bold uppercase tracking-wider text-[#404040]">{index + 1}. {step.label}</span>
              <span className="font-mono text-[13px] font-semibold text-[#404040]">{step.percent.toFixed(1)}%</span>
            </div>
            <div className={`font-mono text-3xl font-semibold mt-3 ${step.tone === "good" ? "text-[#008f39]" : "text-black"}`}>{formatNumber(step.value, 0)}</div>
            <div className={`text-[12px] mt-2 ${step.tone === "bad" ? "text-[#c62828]" : "text-[#666666]"}`}>{step.helper}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 min-[1600px]:grid-cols-2 gap-4 mb-4">
        <div className="bg-white border border-[#d9d9d9] p-4 rounded shadow-sm flex flex-col">
          <h3 className="text-[14px] font-bold text-black uppercase tracking-wider mb-3 border-b border-[#d9d9d9] pb-2">Skip Reason Distribution</h3>
          <SkipReasonChart state={state} height={380} />
        </div>
        <div className="bg-white border border-[#d9d9d9] p-4 rounded shadow-sm flex flex-col">
          <h3 className="text-[14px] font-bold text-black uppercase tracking-wider mb-3 border-b border-[#d9d9d9] pb-2">Signal Asset Distribution</h3>
          <PieMetricChart data={assetRows.length ? assetRows : signalRows} emptyLabel="No asset or signal distribution available." height={320} />
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

      <div className="mt-3 text-[12px] text-[#666666] font-mono">Total skips today: {formatNumber(skips, 0)}. Funnel uses current dashboard candidate_funnel_today telemetry only.</div>
    </SectionPanel>
  );
}
