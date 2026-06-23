import { MetricCard } from "../../components/cards/MetricCard";
import { StorageByCategoryChart } from "../../components/charts/StorageByCategoryChart";
import { DataTable } from "../../components/common/DataTable";
import { SectionPanel } from "../../components/common/SectionPanel";
import type { DashboardState } from "../../types/dashboard";
import { formatNumber } from "../../utils/formatters";
import { getValue } from "../../utils/guards";

export function StorageSection({ state }: { state?: DashboardState }) {
  const tableRows = Object.entries(state?.storage?.categories ?? {}).map(([name, details]) => ({
    name,
    size: String(getValue(details, ["size_mb", "total_size_mb", "size_bytes"]) ?? "n/a"),
    jsonl_count: String(getValue(details, ["jsonl_count"]) ?? "n/a"),
    gz_count: String(getValue(details, ["gz_count"]) ?? "n/a"),
    latest_file: String(getValue(details, ["latest_file"]) ?? "n/a"),
  }));

  return (
    <SectionPanel title="Storage" subtitle="Runtime storage footprint and compression evidence.">
      <div className="metric-grid">
        <MetricCard label="Runtime total" value={formatNumber(getValue(state?.storage, ["runtime_total_mb", "total_size_mb"]), 2)} helper="MB if provided by state" />
        <MetricCard label="Compression candidates" value={formatNumber(getValue(state?.storage, ["compression_candidate_count", "candidate_count"]), 0)} />
        <MetricCard label="Expected reclaim" value={formatNumber(getValue(state?.storage, ["expected_reclaim_mb", "expected_reclaim_gb"]), 2)} />
      </div>
      <div className="chart-card">
        <h3>Storage By Category</h3>
        <StorageByCategoryChart state={state} />
      </div>
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
  );
}
