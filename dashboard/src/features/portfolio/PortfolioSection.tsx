import { MetricCard } from "../../components/cards/MetricCard";
import { SectionPanel } from "../../components/common/SectionPanel";
import type { DashboardState } from "../../types/dashboard";
import { formatCurrency, formatNumber, formatPercent } from "../../utils/formatters";
import { getValue } from "../../utils/guards";

export function PortfolioSection({ state }: { state?: DashboardState }) {
  const portfolio = state?.portfolio;
  const risk = state?.risk;
  const today = state?.trades?.today;

  return (
    <SectionPanel title="Portfolio" subtitle="Bankroll, exposure, and paper trade performance.">
      <div className="metric-grid">
        <MetricCard label="Bankroll" value={formatCurrency(getValue(portfolio, ["bankroll", "balance", "account_balance"]))} />
        <MetricCard label="Balance source" value={String(getValue(portfolio, ["balance_source", "source"]) ?? "n/a")} />
        <MetricCard label="Open positions" value={formatNumber(getValue(portfolio, ["open_position_count", "positions_open"]), 0)} />
        <MetricCard label="Exposure" value={formatCurrency(getValue(risk, ["current_exposure", "exposure"]))} />
        <MetricCard label="Realized PnL" value={formatCurrency(getValue(today, ["total_realized_pnl", "realized_pnl"]))} />
        <MetricCard label="Win rate" value={formatPercent(getValue(today, ["win_rate"]))} />
      </div>
    </SectionPanel>
  );
}
