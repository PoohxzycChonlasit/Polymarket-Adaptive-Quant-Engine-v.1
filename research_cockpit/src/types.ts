export type TrafficState = "green" | "yellow" | "red" | "blue" | "gray";

export type TrendDirection = "up" | "down" | "flat";

export interface Metric {
  label: string;
  value: string | number;
  detail?: string;
  state?: TrafficState;
}

export interface Gate {
  label: string;
  current: number;
  target: number;
  state: TrafficState;
  note: string;
}

export interface TrendMetric {
  label: string;
  previous: string | number;
  current: string | number;
  direction: TrendDirection;
  delta: string;
}

export interface QuoteBucket {
  bucket: string;
  fills: number;
  trades: number;
  tp: number;
  sl: number;
  meanPnl: string;
  state: TrafficState;
}

export interface CockpitAlert {
  label: string;
  severity: TrafficState;
  detail: string;
}

export interface CockpitData {
  run: {
    runId: string;
    mode: string;
    gitStatus: string;
    source: string;
  };
  readiness: {
    percent: number;
    recommendation: string;
    status: string;
  };
  executionReality: {
    paired: number;
    btc: number;
    eth: number;
    tp: number;
    sl: number;
    win: number;
    loss: number;
  };
  quoteAge: {
    meanSubmitMs: number;
    meanFillMs: number;
    buckets: QuoteBucket[];
  };
  outcomeTruth: {
    tp: number;
    sl: number;
    pnlUsdc: number;
    win: number;
    loss: number;
  };
  trend: TrendMetric[];
  gates: Gate[];
  alerts: CockpitAlert[];
}
