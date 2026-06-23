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
    <>
      <RuntimeHealthSection state={state} />
      <PortfolioSection state={state} />
      <SignalIntelligenceSection state={state} />
      <RiskSection state={state} />
      <TradeSnapshotSection state={state} />
      <StorageSection state={state} />
      <AlertsSection alerts={alerts} />
    </>
  );
}
