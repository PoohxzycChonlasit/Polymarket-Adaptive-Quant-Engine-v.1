import type { Gate } from "../types";
import { TrafficLight } from "./TrafficLight";

interface GateCardProps {
  gate: Gate;
}

export function GateCard({ gate }: GateCardProps) {
  const percent = Math.min(100, Math.round((gate.current / gate.target) * 100));

  return (
    <article className="card gate-card">
      <div className="card-topline">
        <h3>{gate.label}</h3>
        <TrafficLight state={gate.state} />
      </div>
      <p className="metric-value">
        {gate.current}/{gate.target}
      </p>
      <div className="progress-track" aria-label={`${gate.label} gate ${percent}%`}>
        <span className={`progress-fill progress-${gate.state}`} style={{ width: `${percent}%` }} />
      </div>
      <p className="metric-detail">{gate.note}</p>
    </article>
  );
}
