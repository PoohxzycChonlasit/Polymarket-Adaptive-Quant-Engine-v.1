import { DataTable } from "../../components/common/DataTable";
import { SectionPanel } from "../../components/common/SectionPanel";
import { TradeSnapshotSection } from "../../features/trades/TradeSnapshotSection";
import type { DashboardState } from "../../types/dashboard";

export function TradesPage({ state }: { state?: DashboardState }) {
  const recentTrades = Array.isArray(state?.trades?.recent) ? (state.trades.recent as Record<string, unknown>[]) : [];

  return (
    <>
      <TradeSnapshotSection state={state} />
      <SectionPanel title="Recent Trades" subtitle="Recent trade rows when provided by dashboard state.">
        <DataTable
          rows={recentTrades}
          columns={[
            { key: "timestamp", label: "Timestamp" },
            { key: "asset", label: "Asset" },
            { key: "side", label: "Side" },
            { key: "realized_pnl", label: "Realized PnL" },
          ]}
          empty="No recent trade rows available in dashboard state."
        />
      </SectionPanel>
    </>
  );
}
