import type { DashboardState } from "../../types/dashboard";
import { toWinLossRows } from "../../utils/formatters";
import { PieMetricChart } from "./chartPrimitives";

export function WinLossChart({ state }: { state?: DashboardState }) {
  return <PieMetricChart data={toWinLossRows(state?.trades?.today)} emptyLabel="No win/loss data available." />;
}
