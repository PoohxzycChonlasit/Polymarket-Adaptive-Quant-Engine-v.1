export type Tone = "good" | "warn" | "bad" | "neutral";

export type CountRecord = Record<string, number | string | null | undefined>;

export interface ChartRow {
  name: string;
  value: number;
}

export interface DashboardState {
  meta?: {
    generated_at_utc?: string;
    source_date_utc?: string;
    state_status?: string;
    state_status_reason?: string;
    schema_version?: string;
    warnings?: string[];
  };
  runtime?: Record<string, unknown>;
  safety?: Record<string, unknown>;
  portfolio?: Record<string, unknown>;
  signals?: {
    assets?: Record<string, Record<string, unknown>>;
  };
  trades?: {
    today?: Record<string, unknown>;
    latest_report?: Record<string, unknown>;
    recent?: Record<string, unknown>[];
  };
  risk?: Record<string, unknown>;
  health?: {
    freshness?: Record<string, unknown>;
    telegram?: Record<string, unknown>;
    [key: string]: unknown;
  };
  storage?: {
    categories?: Record<string, Record<string, unknown>>;
    [key: string]: unknown;
  };
  phase_b?: {
    candidate_funnel_today?: {
      asset_counts?: CountRecord;
      decision_count?: number;
      signal_name_counts?: CountRecord;
      skip_reason_counts?: CountRecord;
      [key: string]: unknown;
    };
  };
  research_analytics?: ResearchAnalytics;
  alerts?: {
    active?: AlertRecord[];
    counts?: Record<string, number>;
    recent?: AlertRecord[];
  };
}

export interface ResearchReasonRow {
  name?: string;
  count?: number | null;
}

export interface ReplayTradeRow {
  timestamp_utc?: string;
  asset?: string;
  side?: string;
  signal?: string;
  holding_seconds?: number | null;
  outcome?: string;
  pnl?: number;
}

export interface ReplayAnalytics {
  status?: "OK" | "PARTIAL" | "MISSING" | string;
  summary?: {
    trades?: number;
    wins?: number;
    losses?: number;
    breakeven?: number;
    win_rate?: number;
    net_pnl?: number;
    profit_factor?: number;
  };
  opportunity_cost?: {
    timing_decay?: Record<string, unknown>;
    top_skip_reasons?: [string, number][];
  };
  lifecycle_funnel?: {
    candidates?: number;
    signals?: number;
    risk_pass?: number;
    entries?: number;
  };
  session_breakdown?: {
    date?: string;
    verdict?: string;
    trades?: string;
    pnl?: number;
    bottleneck?: string;
  }[];
  top_winners?: ReplayTradeRow[];
  top_losers?: ReplayTradeRow[];
  evidence_table?: ReplayTradeRow[];
}

export interface ResearchAnalytics {
  status?: "OK" | "PARTIAL" | "MISSING" | string;
  generated_at?: string;
  latest_research_state?: {
    latest_run_id?: string | null;
    replay_truth_maturity?: string | null;
    direct_field_maturity?: string | null;
    latest_replay_confidence?: string | null;
    direct_field_rate?: number | null;
    proxy_field_rate?: number | null;
    unknown_lifecycle_rate?: number | null;
    recommended_next_step?: string | null;
    blind_spots?: string[];
  };
  candidate_loss_reasons?: ResearchReasonRow[];
  lifecycle_bottlenecks?: ResearchReasonRow[];
  ev_null_reasons?: ResearchReasonRow[];
  reports?: {
    replay?: Record<string, unknown>;
    no_entry?: Record<string, unknown>;
    session_runtime?: Record<string, unknown>;
    data_quality?: Record<string, unknown>;
  };
  replay_analytics?: ReplayAnalytics;
  alerts?: AlertRecord[];
}

export interface AlertRecord {
  code?: string;
  message?: string;
  severity?: string;
  source?: string;
  first_seen_utc?: string;
  last_seen_utc?: string;
}

export interface DashboardHealth {
  status?: string;
  dashboard_state_exists?: boolean;
  state_status?: string;
}
