import { RiskSection } from "../../features/risk/RiskSection";
import type { DashboardState } from "../../types/dashboard";

export function RiskPage({ state }: { state?: DashboardState }) {
  return <RiskSection state={state} />;
}
