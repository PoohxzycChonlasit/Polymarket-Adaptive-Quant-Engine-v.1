import type { DashboardState } from "../../types/dashboard";
import { storageRows, storageUnitLabel } from "../../utils/formatters";
import { BarMetricChart } from "./chartPrimitives";

export function StorageByCategoryChart({ state }: { state?: DashboardState }) {
  return (
    <BarMetricChart
      data={storageRows(state)}
      emptyLabel="No storage category data available."
      unit={storageUnitLabel(state)}
    />
  );
}
