import { DataTable } from "../../components/common/DataTable";
import { SectionPanel } from "../../components/common/SectionPanel";
import { AlertsSection } from "../../features/alerts/AlertsSection";
import type { AlertRecord, DashboardState } from "../../types/dashboard";

export function AlertsPage({ alerts, state }: { alerts?: AlertRecord[]; state?: DashboardState }) {
  const healthRows = Object.entries(state?.health?.freshness ?? {}).map(([name, value]) => ({
    name,
    value: String(value ?? "n/a"),
  }));

  return (
    <>
      <AlertsSection alerts={alerts} />
      <SectionPanel title="Health Issues" subtitle="Freshness and health details surfaced by dashboard state.">
        <DataTable
          rows={healthRows}
          columns={[
            { key: "name", label: "Metric" },
            { key: "value", label: "Value" },
          ]}
          empty="No health freshness details available."
        />
      </SectionPanel>
    </>
  );
}
