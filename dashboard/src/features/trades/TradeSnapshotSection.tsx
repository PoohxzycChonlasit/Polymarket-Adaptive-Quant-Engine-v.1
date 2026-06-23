import { BarMetricChart } from "../../components/charts/chartPrimitives";
import { WinLossChart } from "../../components/charts/WinLossChart";
import { SectionPanel } from "../../components/common/SectionPanel";
import type { DashboardState } from "../../types/dashboard";
import { entriesFromRecord } from "../../utils/formatters";

export function TradeSnapshotSection({ state }: { state?: DashboardState }) {
  return (
    <SectionPanel title="Trade Snapshot" subtitle="Read-only trade summary charts from dashboard state.">
      <div className="chart-grid">
        <div className="chart-card">
          <h3>Win / Loss Summary</h3>
          <WinLossChart state={state} />
        </div>
        <div className="chart-card">
          <h3>Signal Name Distribution</h3>
          <BarMetricChart
            data={entriesFromRecord(state?.phase_b?.candidate_funnel_today?.signal_name_counts)}
            emptyLabel="No signal name distribution available."
          />
        </div>
      </div>
    </SectionPanel>
  );
}
