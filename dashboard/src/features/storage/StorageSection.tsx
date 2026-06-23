import { BloombergMetricRow } from "../../components/cards/MetricCard";
import { StorageByCategoryChart } from "../../components/charts/StorageByCategoryChart";
import { DataTable } from "../../components/common/DataTable";
import { SectionPanel } from "../../components/common/SectionPanel";
import type { DashboardState } from "../../types/dashboard";
import { formatNumber } from "../../utils/formatters";
import { getValue } from "../../utils/guards";

export function StorageSection({ state, compact = false }: { state?: DashboardState; compact?: boolean }) {
  const storage = state?.storage;
  const compression = storage?.compression as Record<string, unknown> | undefined;

  const quantDataTotal = getValue(storage, ["quant_data_total_mb"]);
  const runtimeTotal = getValue(storage, ["runtime_total_mb"]);
  const candidateCount = getValue(compression, ["candidate_count"]);
  const expectedReclaimBytes = getValue(compression, ["expected_reclaim_bytes"]);
  const algorithm = getValue(compression, ["algorithm"]) ?? "n/a";
  const ageDays = getValue(compression, ["age_days"]);
  const dryRunManifest = getValue(compression, ["dry_run_manifest"]) ?? "n/a";
  const compressVerify = getValue(compression, ["latest_compress_verification_status"]) ?? "n/a";
  const restoreVerify = getValue(compression, ["latest_restore_verification_status"]) ?? "n/a";

  const formatGb = (bytesVal: unknown) => {
    const num = Number(bytesVal);
    if (isNaN(num) || num === 0) return "n/a";
    return `${(num / 1024 / 1024 / 1024).toFixed(2)} GB`;
  };

  const tableRows = Object.entries(state?.storage?.categories ?? {}).map(([name, details]) => ({
    name,
    size: details && typeof details === "object" && "size_mb" in details ? `${formatNumber(details.size_mb, 1)} MB` : "n/a",
    jsonl_count: String(getValue(details, ["jsonl_count"]) ?? "n/a"),
    gz_count: String(getValue(details, ["gz_count"]) ?? "n/a"),
    latest_file: details && typeof details === "object" && "latest_file" in details ? String(details.latest_file).split("\\").pop() || "n/a" : "n/a",
  }));

  if (compact) {
    return (
      <SectionPanel title="Storage Footprint">
        <div className="flex flex-col">
          <BloombergMetricRow label="Quant data total" value={`${formatNumber(quantDataTotal, 1)} MB`} />
          <BloombergMetricRow label="Archive candidates" value={formatNumber(candidateCount, 0)} />
          <BloombergMetricRow label="Expected reclaim" value={formatGb(expectedReclaimBytes)} tone={Number(expectedReclaimBytes ?? 0) > 0 ? "good" : "neutral"} />
        </div>
      </SectionPanel>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Overview stats panel */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionPanel title="Data Volume & Registry">
          <div className="flex flex-col h-full justify-between">
            <BloombergMetricRow label="Quant data total" value={`${formatNumber(quantDataTotal, 2)} MB`} />
            <BloombergMetricRow label="Runtime total" value={`${formatNumber(runtimeTotal, 2)} MB`} />
            <BloombergMetricRow label="Last checked" value={state?.storage?.last_refreshed_utc ? String(state.storage.last_refreshed_utc).split("T")[1]?.slice(0, 8) || "n/a" : "n/a"} helper="utc" />
          </div>
        </SectionPanel>

        <SectionPanel title="Compression & Archival Telemetry">
          <div className="flex flex-col">
            <BloombergMetricRow label="Algorithm" value={String(algorithm).toUpperCase()} />
            <BloombergMetricRow label="Age threshold" value={`${ageDays} days`} />
            <BloombergMetricRow label="Candidate files" value={formatNumber(candidateCount, 0)} />
            <BloombergMetricRow label="Expected reclaim" value={formatGb(expectedReclaimBytes)} tone={Number(expectedReclaimBytes ?? 0) > 0 ? "good" : "neutral"} />
            <BloombergMetricRow label="Compress verification" value={String(compressVerify).toUpperCase()} tone={compressVerify === "PASS" ? "good" : compressVerify === "FAIL" ? "bad" : "neutral"} />
            <BloombergMetricRow label="Restore verification" value={String(restoreVerify).toUpperCase()} tone={restoreVerify === "PASS" ? "good" : restoreVerify === "FAIL" ? "bad" : "neutral"} />
          </div>
        </SectionPanel>
      </div>

      {/* Manifest registry path info */}
      <div className="p-3 px-4 border border-[#d9d9d9] bg-white rounded-lg font-mono text-[12px] text-[#404040] shadow-sm">
        <strong className="text-black block mb-1 uppercase">Dry Run Manifest Registry:</strong>
        <span className="select-all">{String(dryRunManifest)}</span>
      </div>

      {/* Category breakdown visual and table */}
      <div className="grid grid-cols-1 min-[1600px]:grid-cols-3 gap-4">
        <div className="min-[1600px]:col-span-1 bg-white border border-[#d9d9d9] p-4 rounded-lg flex flex-col justify-between shadow-sm">
          <h3 className="text-[14px] font-bold text-black uppercase tracking-wider mb-3 border-b border-[#d9d9d9] pb-2">Storage By Category</h3>
          <div className="my-auto">
            <StorageByCategoryChart state={state} />
          </div>
        </div>
        <div className="min-[1600px]:col-span-2">
          <SectionPanel title="Registry Category Details">
            <DataTable
              rows={tableRows}
              columns={[
                { key: "name", label: "Category" },
                { key: "size", label: "Size" },
                { key: "jsonl_count", label: "JSONL" },
                { key: "gz_count", label: "GZ" },
                { key: "latest_file", label: "Latest file" },
              ]}
              empty="No storage category details available."
            />
          </SectionPanel>
        </div>
      </div>
    </div>
  );
}
