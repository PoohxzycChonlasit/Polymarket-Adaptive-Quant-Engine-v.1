import type { TrendMetric } from "../types";

const arrowByDirection = {
  up: "↑",
  down: "↓",
  flat: "→",
};

interface TrendCardProps {
  trend: TrendMetric;
}

export function TrendCard({ trend }: TrendCardProps) {
  return (
    <article className="card trend-card">
      <h3>{trend.label}</h3>
      <p className={`trend-arrow trend-${trend.direction}`}>{arrowByDirection[trend.direction]}</p>
      <p className="metric-detail">
        {trend.previous} to {trend.current} ({trend.delta})
      </p>
    </article>
  );
}
