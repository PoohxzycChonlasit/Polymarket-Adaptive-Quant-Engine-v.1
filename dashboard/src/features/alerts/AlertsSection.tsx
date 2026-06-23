import { DataTable } from "../../components/common/DataTable";
import { SectionPanel } from "../../components/common/SectionPanel";
import type { AlertRecord } from "../../types/dashboard";

export function AlertsSection({ alerts }: { alerts?: AlertRecord[] }) {
  const rows = (alerts ?? []).map((alert) => ({
    severity: alert.severity ?? "unknown",
    code: alert.code ?? "unknown",
    message: alert.message ?? "n/a",
    source: alert.source ?? "n/a",
  }));

  return (
    <SectionPanel title="Alerts" subtitle="Recent and active observability warnings from dashboard state.">
      <DataTable
        rows={rows}
        columns={[
          { key: "severity", label: "Severity" },
          { key: "code", label: "Code" },
          { key: "message", label: "Message" },
          { key: "source", label: "Source" },
        ]}
        empty="No active alerts reported."
      />
    </SectionPanel>
  );
}
