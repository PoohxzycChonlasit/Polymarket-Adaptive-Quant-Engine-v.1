import { SectionPanel } from "../../components/common/SectionPanel";

const researchRoadmap = [
  {
    title: "Replay Analytics",
    description: "Closed-trade replay, attribution review, lifecycle truth checks, and replay-key coverage.",
    status: "read-only planned",
  },
  {
    title: "Session Analytics",
    description: "Paper-session health, entry funnel movement, runtime stability, and trade-count progression.",
    status: "read-only planned",
  },
  {
    title: "Regime Analytics",
    description: "Market regime breakdowns, signal performance by regime, and volatility-state comparisons.",
    status: "read-only planned",
  },
  {
    title: "Expectancy Analytics",
    description: "Entry EV, realized PnL, win rate, signal reason, and candidate-instance comparisons.",
    status: "read-only planned",
  },
  {
    title: "Backtesting Workbench",
    description: "Offline backtest summaries and parameter evidence. No runtime or live controls.",
    status: "read-only planned",
  },
  {
    title: "Monte Carlo Lab",
    description: "Risk-of-ruin, drawdown path simulation, bankroll survivability, and sample-size planning.",
    status: "read-only planned",
  },
];

export function ResearchPage() {
  return (
    <SectionPanel title="Research Terminal" subtitle="Roadmap placeholders for future offline analytics surfaces.">
      <div className="grid grid-cols-1 min-[1200px]:grid-cols-2 gap-4">
        {researchRoadmap.map((item) => (
          <div key={item.title} className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
            <div className="flex items-start justify-between gap-3 mb-3">
              <h3 className="m-0 text-[15px] font-bold text-black">{item.title}</h3>
              <span className="shrink-0 text-[11px] font-mono font-semibold uppercase text-[#666666] border border-[#d9d9d9] bg-[#f7f7f7] rounded px-2 py-1">
                {item.status}
              </span>
            </div>
            <p className="m-0 text-[13px] leading-relaxed text-[#404040]">{item.description}</p>
          </div>
        ))}
      </div>
    </SectionPanel>
  );
}
