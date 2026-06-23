import { StatusBadge } from "../badges/StatusBadge";
import { getStateTone } from "../../utils/guards";

export function Topbar({
  stateStatus,
  apiStatus,
  isFetching,
}: {
  stateStatus?: string;
  apiStatus?: string;
  isFetching: boolean;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 px-4 border border-[#d9d9d9] bg-white rounded-lg mb-3 shadow-sm">
      <div className="flex flex-col font-mono">
        <p className="text-[12px] uppercase font-bold tracking-wider text-[#666666] m-0">Local operator console</p>
        <strong className="text-[14px] text-[#000000] font-bold">Read-only dashboard</strong>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge label={`State ${stateStatus ?? "UNKNOWN"}`} tone={getStateTone(stateStatus)} />
        <StatusBadge label={`API ${apiStatus ?? "unknown"}`} tone={apiStatus === "ok" ? "good" : "warn"} />
        <StatusBadge label={isFetching ? "refreshing" : "15s polling"} />
      </div>
    </div>
  );
}
