import { MetricCard } from "../../components/cards/MetricCard";
import { SectionPanel } from "../../components/common/SectionPanel";
import type { DashboardState } from "../../types/dashboard";
import { formatCurrency, formatNumber } from "../../utils/formatters";
import { getValue } from "../../utils/guards";

export function RiskSection({ state }: { state?: DashboardState }) {
  const risk = state?.risk;
  const safety = state?.safety;

  return (
    <SectionPanel title="Risk" subtitle="Evidence-only risk mode, budget, exposure, and reconciliation state.">
      <div className="metric-grid">
        <MetricCard label="Risk mode" value={String(getValue(risk, ["risk_mode", "mode"]) ?? "n/a")} />
        <MetricCard label="Available risk budget" value={formatCurrency(getValue(risk, ["available_risk_budget", "risk_budget_available"]))} />
        <MetricCard label="Current exposure" value={formatCurrency(getValue(risk, ["current_exposure", "exposure"]))} />
        <MetricCard label="Risk events today" value={formatNumber(getValue(risk, ["risk_event_count_today"]), 0)} />
        <MetricCard label="Risk-plan-zero" value={formatNumber(getValue(risk, ["risk_plan_zero_count_today"]), 0)} />
        <MetricCard label="Reconciliation" value={String(getValue(safety, ["reconciliation_class", "reconciliation_status"]) ?? "n/a")} />
      </div>
    </SectionPanel>
  );
}
