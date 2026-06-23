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

export interface NoEntryAnalytics {
  status?: "OK" | "PARTIAL" | "MISSING" | string;
  summary?: {
    total_candidates?: number;
    entries?: number;
    entry_rate?: number;
  };
  root_causes?: [string, number][];
  blocker_categories?: [string, number][];
  timing_cutoff?: {
    count_time_unsafe?: number;
    avg_seconds_remaining?: number;
    closest_seconds_remaining?: number | null;
    timing_buckets?: Record<string, number>;
  };
  risk_zero?: {
    count_risk_plan_zero?: number;
    bankroll_tier_name?: string;
    bankroll_mode?: string;
    micro_position_size?: number;
    micro_survival_active?: boolean;
  };
  liquidity?: {
    count_orderbook_unavailable_or_stale?: number;
    average_orderbook_age_ms?: number;
    token_mapping_warning_count?: number;
  };
  ev_missing?: {
    no_probability_model_output?: number;
    no_market_price?: number;
  };
  clob_errors?: Record<string, number>;
  recommended_investigation?: string[];
}

export interface SessionLeaderboardRow {
  date: string;
  trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  net_pnl: number;
  profit_factor: number;
  entry_rate: number;
  risk_rejects: number;
  expectancy: number;
  primary_bottleneck: string;
  verdict: string;
}

export interface SessionRecommendationRow {
  date: string;
  reason: string;
}

export interface SessionAnalytics {
  status?: "OK" | "PARTIAL" | "MISSING" | string;
  summary?: {
    best_session?: string;
    worst_session?: string;
    highest_entry_rate_session?: string;
    highest_no_entry_session?: string;
  };
  leaderboard?: SessionLeaderboardRow[];
  entry_rate?: { date: string; entry_rate: number }[];
  no_entry_rate?: { date: string; no_entry_rate: number }[];
  risk_reject_rate?: { date: string; risk_reject_rate: number }[];
  expectancy?: { date: string; expectancy: number }[];
  recommended_sessions?: SessionRecommendationRow[];
  sessions_to_avoid?: SessionRecommendationRow[];
}

export interface LifecycleFunnelRow {
  stage: string;
  count: number;
  yield: number;
}

export interface LifecycleLossRow {
  stage: string;
  lost: number;
}

export interface LifecycleKillReasonRow {
  reason: string;
  count: number;
}

export interface LifecycleOpportunityRow {
  reason: string;
  lost_candidates: number;
}

export interface LifecycleLeaderboardRow {
  date: string;
  scanned: number;
  entries: number;
  throughput_rate: number;
  dominant_blocker: string;
}

export interface LifecycleAnalytics {
  status?: "OK" | "PARTIAL" | "MISSING" | string;
  summary?: {
    candidate_count?: number;
    signal_pass_count?: number;
    ev_pass_count?: number;
    risk_pass_count?: number;
    execution_pass_count?: number;
    entry_count?: number;
    exit_count?: number;
  };
  funnel?: LifecycleFunnelRow[];
  stage_losses?: LifecycleLossRow[];
  top_kill_reasons?: LifecycleKillReasonRow[];
  opportunity_cost?: LifecycleOpportunityRow[];
  leaderboard?: LifecycleLeaderboardRow[];
  alerts?: Record<string, unknown>[];
}

export interface RegimeLeaderboardRow {
  regime: string;
  scanned: number;
  entries: number;
  entry_rate: number;
  no_entries: number;
  no_entry_rate: number;
  risk_rejections: number;
  risk_rejection_rate: number;
  net_pnl: number;
  expectancy: number;
  win_rate: number;
  profit_factor: number;
  verdict: string;
}

export interface RegimeEntryRateRow {
  regime: string;
  entry_rate: number;
  entries: number;
  scanned: number;
}

export interface RegimeNoEntryRow {
  regime: string;
  no_entry_rate: number;
  no_entries: number;
  scanned: number;
}

export interface RegimeRiskRejectRow {
  regime: string;
  risk_rejection_rate: number;
  rejections: number;
  skipped: number;
}

export interface RegimeExpectancyRow {
  regime: string;
  expectancy: number;
  net_pnl: number;
}

export interface RegimeCandidateLossRow {
  regime: string;
  stage: string;
  lost: number;
}

export interface RegimeRecommendationRow {
  regime: string;
  reason: string;
}

export interface RegimeAnalytics {
  status?: "OK" | "PARTIAL" | "MISSING" | string;
  summary?: {
    best_regime?: string;
    worst_regime?: string;
    highest_entry_rate_regime?: string;
    highest_no_entry_regime?: string;
    highest_risk_reject_regime?: string;
  };
  leaderboard?: RegimeLeaderboardRow[];
  entry_rate?: RegimeEntryRateRow[];
  no_entry_rate?: RegimeNoEntryRow[];
  risk_reject_rate?: RegimeRiskRejectRow[];
  expectancy?: RegimeExpectancyRow[];
  candidate_loss?: RegimeCandidateLossRow[];
  recommended_regimes?: RegimeRecommendationRow[];
  avoid_regimes?: RegimeRecommendationRow[];
  alerts?: Record<string, unknown>[];
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
  no_entry_analytics?: NoEntryAnalytics;
  session_analytics?: SessionAnalytics;
  lifecycle_analytics?: LifecycleAnalytics;
  regime_analytics?: RegimeAnalytics;
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
