import type { CockpitData } from "../types";
import { MetricCard } from "../components/MetricCard";

interface ExecutionRealityProps {
  data: CockpitData;
}

export function ExecutionReality({ data }: ExecutionRealityProps) {
  const execution = data.executionReality;

  return (
    <section className="page-section" id="execution-reality">
      <div className="section-heading">
        <p className="eyebrow">Execution Reality</p>
        <h2>Paired evidence coverage</h2>
      </div>
      <div className="card-grid seven-up">
        <MetricCard title="paired" value={execution.paired} detail="confirmed paired trades" state="yellow" />
        <MetricCard title="BTC" value={execution.btc} detail="confirmed BTC pairs" state="yellow" />
        <MetricCard title="ETH" value={execution.eth} detail="confirmed ETH pairs" state="green" />
        <MetricCard title="TP" value={execution.tp} detail="trade_result TP" state="yellow" />
        <MetricCard title="SL" value={execution.sl} detail="trade_result SL" state="green" />
        <MetricCard title="WIN" value={execution.win} detail="pnl_usdc positive" state="yellow" />
        <MetricCard title="LOSS" value={execution.loss} detail="pnl_usdc negative" state="green" />
      </div>
    </section>
  );
}
