import { AlertsSection } from "../../features/alerts/AlertsSection";
import { PortfolioSection } from "../../features/portfolio/PortfolioSection";
import { RiskSection } from "../../features/risk/RiskSection";
import { RuntimeHealthSection } from "../../features/runtime/RuntimeHealthSection";
import { SignalIntelligenceSection } from "../../features/signals/SignalIntelligenceSection";
import { StorageSection } from "../../features/storage/StorageSection";
import { TradeSnapshotSection } from "../../features/trades/TradeSnapshotSection";
import type { AlertRecord, DashboardState } from "../../types/dashboard";

export function OverviewPage({ state, alerts }: { state?: DashboardState; alerts?: AlertRecord[] }) {
  return (
    <div className="grid grid-cols-1 min-[1600px]:grid-cols-3 gap-3">
      {/* Main metrics & telemetry charts columns (Left 2/3) */}
      <div className="min-[1600px]:col-span-2 flex flex-col gap-3">
        <PortfolioSection state={state} />
        <SignalIntelligenceSection state={state} />
        <TradeSnapshotSection state={state} />
      </div>

      {/* Operator health, risk status and warnings control panels (Right 1/3) */}
      <div className="flex flex-col gap-3">
        <RuntimeHealthSection state={state} />
        <RiskSection state={state} />
        <StorageSection state={state} compact={true} />
        <AlertsSection alerts={alerts} />
      </div>
    </div>
  );
}
