import type { CockpitData } from "../types";
import { GateCard } from "../components/GateCard";
import { MetricCard } from "../components/MetricCard";

interface ReadinessProps {
  data: CockpitData;
}

export function Readiness({ data }: ReadinessProps) {
  return (
    <section className="page-section" id="readiness">
      <div className="section-heading">
        <p className="eyebrow">Readiness</p>
        <h2>Phase 6 gate cards</h2>
      </div>
      <div className="readiness-banner">
        <MetricCard title="Phase 6" value={data.readiness.status} detail={data.readiness.recommendation} state="yellow" />
        <MetricCard title="Readiness %" value={`${data.readiness.percent}%`} detail="paired, BTC, TP still blocking" state="yellow" />
      </div>
      <div className="card-grid five-up">
        {data.gates.map((gate) => (
          <GateCard key={gate.label} gate={gate} />
        ))}
      </div>
    </section>
  );
}
