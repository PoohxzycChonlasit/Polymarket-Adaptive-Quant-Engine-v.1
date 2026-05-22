import type { CockpitData } from "../types";
import { TrendCard } from "../components/TrendCard";

interface TrendProps {
  data: CockpitData;
}

export function Trend({ data }: TrendProps) {
  return (
    <section className="page-section" id="trend">
      <div className="section-heading">
        <p className="eyebrow">Trend</p>
        <h2>Daily delta arrows</h2>
      </div>
      <div className="card-grid four-up">
        {data.trend.map((trend) => (
          <TrendCard key={trend.label} trend={trend} />
        ))}
      </div>
    </section>
  );
}
