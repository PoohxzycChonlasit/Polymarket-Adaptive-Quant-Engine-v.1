import type { CockpitData } from "../types";
import { AlertPanel } from "../components/AlertPanel";

interface AlertsProps {
  data: CockpitData;
}

export function Alerts({ data }: AlertsProps) {
  return (
    <section className="page-section" id="alerts">
      <AlertPanel alerts={data.alerts} />
    </section>
  );
}
