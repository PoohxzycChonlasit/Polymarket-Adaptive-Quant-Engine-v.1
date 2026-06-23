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
    <div className="topbar">
      <div>
        <p className="eyebrow">Local operator console</p>
        <strong>Read-only dashboard pages</strong>
      </div>
      <div className="topbar-badges">
        <StatusBadge label={`State ${stateStatus ?? "UNKNOWN"}`} tone={getStateTone(stateStatus)} />
        <StatusBadge label={`API ${apiStatus ?? "unknown"}`} tone={apiStatus === "ok" ? "good" : "warn"} />
        <StatusBadge label={isFetching ? "refreshing" : "15s polling"} />
      </div>
    </div>
  );
}
