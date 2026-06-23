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
  alerts?: {
    active?: AlertRecord[];
    counts?: Record<string, number>;
    recent?: AlertRecord[];
  };
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
