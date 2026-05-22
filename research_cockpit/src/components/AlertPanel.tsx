import type { CockpitAlert } from "../types";
import { TrafficLight } from "./TrafficLight";

interface AlertPanelProps {
  alerts: CockpitAlert[];
}

export function AlertPanel({ alerts }: AlertPanelProps) {
  return (
    <aside className="alert-panel" aria-label="Alerts">
      <div className="section-heading">
        <p className="eyebrow">Alerts</p>
        <h2>Operator attention</h2>
      </div>
      <div className="alert-list">
        {alerts.map((alert) => (
          <article className="alert-row" key={alert.label}>
            <TrafficLight state={alert.severity} label={alert.label} />
            <p>{alert.detail}</p>
          </article>
        ))}
      </div>
    </aside>
  );
}
