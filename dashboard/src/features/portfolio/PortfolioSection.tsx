import { BloombergMetricRow } from "../../components/cards/MetricCard";
import { SectionPanel } from "../../components/common/SectionPanel";
import type { DashboardState } from "../../types/dashboard";
import { formatCurrency, formatNumber, formatPercent } from "../../utils/formatters";
import { getValue } from "../../utils/guards";

export function PortfolioSection({ state }: { state?: DashboardState }) {
  const portfolio = state?.portfolio;
  const risk = state?.risk;
  const today = state?.trades?.today;

  const pnl = Number(getValue(today, ["total_realized_pnl", "realized_pnl"]) ?? 0);
  const winRate = Number(getValue(today, ["win_rate"]) ?? 0);

  return (
    <SectionPanel title="Portfolio State" subtitle="Tier-one capital, exposure, and realized paper performance.">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
        <div className="flex flex-col">
          <BloombergMetricRow label="Bankroll" value={formatCurrency(getValue(portfolio, ["bankroll", "balance", "account_balance"]))} />
          <BloombergMetricRow label="Balance source" value={String(getValue(portfolio, ["balance_source", "source"]) ?? "n/a")} />
          <BloombergMetricRow label="Open positions" value={formatNumber(getValue(portfolio, ["open_position_count", "positions_open"]), 0)} />
        </div>
        <div className="flex flex-col">
          <BloombergMetricRow label="Exposure" value={formatCurrency(getValue(risk, ["current_exposure", "exposure"]))} />
          <BloombergMetricRow label="Realized PnL" value={formatCurrency(pnl)} tone={pnl > 0 ? "good" : pnl < 0 ? "bad" : "neutral"} />
          <BloombergMetricRow label="Win rate" value={formatPercent(winRate)} tone={winRate >= 0.5 ? "good" : winRate > 0 ? "warn" : "neutral"} />
        </div>
      </div>
    </SectionPanel>
  );
}
