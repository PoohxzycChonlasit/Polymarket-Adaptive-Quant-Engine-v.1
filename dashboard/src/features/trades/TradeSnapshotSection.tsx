import { BarMetricChart } from "../../components/charts/chartPrimitives";
import { WinLossChart } from "../../components/charts/WinLossChart";
import { SectionPanel } from "../../components/common/SectionPanel";
import type { DashboardState } from "../../types/dashboard";
import { entriesFromRecord } from "../../utils/formatters";

export function TradeSnapshotSection({ state }: { state?: DashboardState }) {
  return (
    <SectionPanel title="Trade Snapshot">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="bg-white border border-slate-600 p-2.5 rounded flex flex-col shadow-sm">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2 border-b border-slate-600/30 pb-1">Win / Loss Summary</h3>
          <WinLossChart state={state} height={280} />
        </div>
        <div className="bg-white border border-slate-600 p-2.5 rounded flex flex-col shadow-sm">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2 border-b border-slate-600/30 pb-1">Signal Name Distribution</h3>
          <BarMetricChart
            data={entriesFromRecord(state?.phase_b?.candidate_funnel_today?.signal_name_counts)}
            emptyLabel="No signal name distribution available."
            height={280}
          />
        </div>
      </div>
    </SectionPanel>
  );
}
