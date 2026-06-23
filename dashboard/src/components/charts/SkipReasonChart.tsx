import type { DashboardState } from "../../types/dashboard";
import { entriesFromRecord } from "../../utils/formatters";
import { BarMetricChart } from "./chartPrimitives";

export function SkipReasonChart({ state }: { state?: DashboardState }) {
  return (
    <BarMetricChart
      data={entriesFromRecord(state?.phase_b?.candidate_funnel_today?.skip_reason_counts)}
      emptyLabel="No skip reason data available."
    />
  );
}
