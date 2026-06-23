import { SignalIntelligenceSection } from "../../features/signals/SignalIntelligenceSection";
import type { DashboardState } from "../../types/dashboard";

export function SignalsPage({ state }: { state?: DashboardState }) {
  return <SignalIntelligenceSection state={state} />;
}
