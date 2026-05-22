import type { CockpitData } from "../types";
import { MetricCard } from "../components/MetricCard";

interface OutcomeTruthProps {
  data: CockpitData;
}

export function OutcomeTruth({ data }: OutcomeTruthProps) {
  const outcome = data.outcomeTruth;

  return (
    <section className="page-section" id="outcome-truth">
      <div className="section-heading">
        <p className="eyebrow">Outcome Truth</p>
        <h2>Ground-truth result fields</h2>
      </div>
      <div className="card-grid five-up">
        <MetricCard title="TP / SL" value={`${outcome.tp} / ${outcome.sl}`} detail="trade_result counts" state="yellow" />
        <MetricCard title="PnL" value={outcome.pnlUsdc.toFixed(6)} detail="mean pnl_usdc" state="yellow" />
        <MetricCard title="WIN LOSS" value={`${outcome.win} / ${outcome.loss}`} detail="pnl_usdc sign split" state="yellow" />
        <MetricCard title="TP" value={outcome.tp} detail="target 5" state="yellow" />
        <MetricCard title="SL" value={outcome.sl} detail="target met" state="green" />
      </div>
    </section>
  );
}
