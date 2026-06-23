import { MetricCard } from "../../components/cards/MetricCard";
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

  return (
    <SectionPanel title="Signal Intelligence" subtitle="Candidate activity, signal shape, and skip bottlenecks.">
      <div className="metric-grid">
        <MetricCard label="Decisions today" value={formatNumber(funnel?.decision_count, 0)} />
        <MetricCard label="Entries today" value={formatNumber(state?.trades?.today?.trade_open_count, 0)} />
        <MetricCard label="Skips today" value={formatNumber(skips, 0)} />
        <MetricCard label="Top skip reason" value={skipRows[0]?.name ?? "n/a"} helper={skipRows[0] ? String(skipRows[0].value) : undefined} />
      </div>
      <div className="chart-grid">
        <div className="chart-card">
          <h3>Skip Reason Distribution</h3>
          <SkipReasonChart state={state} />
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
    </SectionPanel>
  );
}
