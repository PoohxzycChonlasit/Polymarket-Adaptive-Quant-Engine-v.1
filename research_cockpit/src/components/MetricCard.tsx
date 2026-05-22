import type { TrafficState } from "../types";
import { TrafficLight } from "./TrafficLight";

interface MetricCardProps {
  title: string;
  value: string | number;
  detail?: string;
  state?: TrafficState;
}

export function MetricCard({ title, value, detail, state = "blue" }: MetricCardProps) {
  return (
    <article className="card metric-card">
      <div className="card-topline">
        <h3>{title}</h3>
        <TrafficLight state={state} />
      </div>
      <p className="metric-value">{value}</p>
      {detail ? <p className="metric-detail">{detail}</p> : null}
    </article>
  );
}
