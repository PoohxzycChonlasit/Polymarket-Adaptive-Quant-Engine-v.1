import type { CockpitData } from "../types";
import { MetricCard } from "../components/MetricCard";

interface OverviewProps {
  data: CockpitData;
}

export function Overview({ data }: OverviewProps) {
  return (
    <section className="page-section" id="overview">
      <div className="section-heading">
        <p className="eyebrow">Overview</p>
        <h2>Phase 6 monitor snapshot</h2>
      </div>
      <div className="card-grid four-up">
        <MetricCard title="Run ID" value={data.run.runId} detail="Mock artifact run scope" state="blue" />
        <MetricCard title="Readiness %" value={`${data.readiness.percent}%`} detail={data.readiness.recommendation} state="yellow" />
        <MetricCard title="Git status" value={data.run.gitStatus} detail="Mock dashboard field" state="blue" />
        <MetricCard title="Mode" value={data.run.mode.toUpperCase()} detail={data.run.source} state="green" />
      </div>
    </section>
  );
}
