import { BloombergMetricRow } from "../../components/cards/MetricCard";
import { SectionPanel } from "../../components/common/SectionPanel";
import type { DashboardState } from "../../types/dashboard";
import { formatCurrency, formatNumber } from "../../utils/formatters";
import { getValue } from "../../utils/guards";

export function RiskSection({ state }: { state?: DashboardState }) {
  const risk = state?.risk;
  const safety = state?.safety;

  return (
    <SectionPanel title="Risk Controls" subtitle="Risk mode, exposure, budget, and reconciliation status.">
      <div className="grid grid-cols-1 min-[900px]:grid-cols-2 gap-x-6">
        <BloombergMetricRow label="Risk mode" value={String(getValue(risk, ["risk_mode", "mode"]) ?? "n/a")} tone={getValue(risk, ["risk_mode", "mode"]) === "LOCKDOWN" ? "bad" : "neutral"} />
        <BloombergMetricRow label="Available budget" value={formatCurrency(getValue(risk, ["available_risk_budget", "risk_budget_available"]))} />
        <BloombergMetricRow label="Current exposure" value={formatCurrency(getValue(risk, ["current_exposure", "exposure"]))} />
        <BloombergMetricRow label="Risk events today" value={formatNumber(getValue(risk, ["risk_event_count_today"]), 0)} />
        <BloombergMetricRow label="Risk-plan-zero" value={formatNumber(getValue(risk, ["risk_plan_zero_count_today"]), 0)} tone={Number(getValue(risk, ["risk_plan_zero_count_today"]) ?? 0) > 0 ? "warn" : "neutral"} />
        <BloombergMetricRow label="Reconciliation" value={String(getValue(safety, ["reconciliation_class", "reconciliation_status"]) ?? "n/a")} tone={getValue(safety, ["reconciliation_class", "reconciliation_status"]) === "FLAT" ? "good" : "warn"} />
      </div>
    </SectionPanel>
  );
}
