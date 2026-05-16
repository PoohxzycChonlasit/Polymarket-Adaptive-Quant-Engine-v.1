import { readdir, readFile, stat } from "fs/promises";
import type { CSSProperties, ReactNode } from "react";
import path from "path";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export const metadata = {
  title: "Offline Quant Reports | PolyTrade",
  description: "Read-only local viewer for generated offline quant reports.",
};

type JsonObject = Record<string, unknown>;

type ProfitStrategyResult = {
  name: string;
  realizedProxyPnl: number;
  pnlUpliftVsBaseline: number;
  maxDrawdown: number;
  winRate: number;
  runnerContribution: number;
  forcedDeriskCount: number;
  lateWindowDecayAvoided: number;
  btcContribution: number;
  ethContribution: number;
  verdict: string;
};

type ExitConvergenceSummary = {
  hasReport: boolean;
  realizedProxyPnl: number;
  upliftVsPolicyD: number;
  maxDrawdown: number;
  convergenceExitCount: number;
  averageExitSr: number;
  convergenceStabilityScore: number;
  falseConvergenceExits: number;
  lateReversalCount: number;
  btcBehavior: string;
  ethBehavior: string;
  uncertaintyCollapseWindowEstimate: string;
  verdict: string;
};

type ReportSummary = {
  date: string;
  runId: string;
  hasRunId: boolean;
  sortTimestampUtc: string;
  continuity: {
    status: string;
    trustworthyForReplay: boolean;
    timestampOrdering: string;
    chainGaps: number;
    eventsChecked: number;
  };
  rootCause: {
    primary: string;
    secondary: string;
    counts: Record<string, number>;
    executionStageAttempts: number;
  };
  timeUnsafeCount: number;
  riskPlanZeroCount: number;
  lifecycleDistribution: Record<string, number>;
  evVisibility: {
    status: string;
    valueEvents: number;
    nullEvents: number;
    nullReasonCoverageRate: number;
    topNullReasons: Record<string, number>;
  };
  liquidityOrderbook: {
    status: string;
    readinessStatus: string;
    orderbookUnavailableCount: number;
    emptyBookCount: number;
    staleBookCount: number;
    spreadNormalizationRate: number;
    liquidityStates: Record<string, number>;
  };
  badJson: {
    warning: boolean;
    selectedRunBadLines: number;
    totalScannedBadLines: number;
    affectsSelectedRun: boolean;
    status: string;
  };
  lifecycleTiming: {
    hasReport: boolean;
    cutoffSurvivalRate: number;
    cutoffStarvationRate: number;
    executableAgeBeforeSkipP50: number;
    revisitDelayP50: number;
    revisitDelayP90: number;
    executableToDecisionP50: number;
    executableToDecisionP90: number;
    timeToFinalDeriskP50: number;
  };
  plainSummary: {
    dataClean: string;
    botTradedPaper: string;
    pnl: string;
    whySkipped: string;
    executionFailures: string;
    liveReadiness: string;
  };
  profitManagement: {
    hasReport: boolean;
    strategies: ProfitStrategyResult[];
    verdict: string;
  };
  exitConvergence: ExitConvergenceSummary;
  timelineCards: Array<{
    title: string;
    items: Record<string, string | number>;
  }>;
  sourceFiles: string[];
};

const reportPatterns: Array<[string, RegExp]> = [
  ["quant_data_quality", /^quant_data_quality_(\d{4}-\d{2}-\d{2})(?:_run_(.+))?\.json$/],
  ["no_entry", /^no_entry_report_(\d{4}-\d{2}-\d{2})(?:_run_(.+))?\.json$/],
  ["session_runtime", /^session_runtime_evaluation_(\d{4}-\d{2}-\d{2})(?:_run_(.+))?\.json$/],
  ["replay", /^replay_report_(\d{4}-\d{2}-\d{2})(?:_run_(.+))?\.json$/],
  ["compact_run_summary", /^compact_run_summary_(\d{4}-\d{2}-\d{2})\.json$/],
  ["market_readiness_probe", /^market_readiness_admission_probe_(\d{4}-\d{2}-\d{2})\.json$/],
  ["silent_zone_probe", /^silent_zone_selection_probe_(\d{4}-\d{2}-\d{2})(?:_.+)?\.json$/],
  ["no_entry_root_cause", /^no_entry_root_cause_(\d{4}-\d{2}-\d{2})\.json$/],
  ["decision_cycle_timing_probe", /^decision_cycle_timing_probe_(\d{4}-\d{2}-\d{2})\.json$/],
  ["candidate_continuity", /^candidate_continuity_(\d{4}-\d{2}-\d{2})(?:_run_(.+))?\.json$/],
  ["candidate_path_observability", /^candidate_path_observability_(\d{4}-\d{2}-\d{2})(?:_run_(.+))?\.json$/],
  ["lifecycle_timing", /^lifecycle_timing_report_(\d{4}-\d{2}-\d{2})(?:_run_(.+))?\.json$/],
  ["lifecycle_profit_management", /^lifecycle_profit_management_replay_(\d{4}-\d{2}-\d{2})(?:_run_(.+))?\.json$/],
  ["exit_convergence", /^exit_convergence_intelligence_replay_(\d{4}-\d{2}-\d{2})(?:_run_(.+))?\.json$/],
];

const reportDir = path.resolve(process.cwd(), "..", "runtime", "reports");
const profitManagementStrategyNames = [
  "baseline_hold_to_settlement",
  "partial_reduce_50pct_at_2x",
  "partial_reduce_50pct_at_3x",
  "dynamic_derisk_before_close",
  "hold_winners_cut_late_decay",
];

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getValue(source: unknown, keys: string[]): unknown {
  let current = source;
  for (const key of keys) {
    if (!isObject(current) || !(key in current)) return undefined;
    current = current[key];
  }
  return current;
}

function firstString(values: unknown[], fallback = "UNKNOWN"): string {
  for (const value of values) {
    if (typeof value === "string" && value.length > 0) return value;
    if (typeof value === "number") return String(value);
  }
  return fallback;
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function firstNumber(values: unknown[]): number {
  for (const value of values) {
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return 0;
}

function countMap(value: unknown): Record<string, number> {
  if (isObject(value)) {
    return Object.fromEntries(
      Object.entries(value).filter((entry): entry is [string, number] => typeof entry[1] === "number"),
    );
  }
  if (Array.isArray(value)) {
    const output: Record<string, number> = {};
    for (const row of value) {
      if (Array.isArray(row) && typeof row[0] === "string" && typeof row[1] === "number") {
        output[row[0]] = row[1];
      }
    }
    return output;
  }
  return {};
}

function dominantKey(value: unknown): string | undefined {
  const counts = Object.entries(countMap(value));
  if (!counts.length) return undefined;
  return counts.sort((a, b) => b[1] - a[1])[0][0];
}

function rootProbeLabel(report?: JsonObject): string | undefined {
  if (!report) return undefined;
  const category = dominantKey(report.category_counts);
  const reason = dominantKey(report.primary_reason_counts);
  if (category && reason) return `${category}/${reason}`;
  return category ?? reason;
}

function detectReport(fileName: string): { kind: string; date: string; runId?: string } | undefined {
  for (const [kind, pattern] of reportPatterns) {
    const match = pattern.exec(fileName);
    if (match?.[1]) {
      return { kind, date: match[1], runId: match[2] };
    }
  }
  return undefined;
}

function reportRunId(report: JsonObject, fileRunId?: string): string {
  return firstString(
    [
      report.run_id,
      report.run_id_filter,
      report.run_id_scope,
      getValue(report, ["replay_continuity", "run_id_scope"]),
      fileRunId,
    ],
    "unscoped",
  );
}

function lifecycleDistribution(reports: Record<string, JsonObject>): Record<string, number> {
  return (
    firstNonEmptyMap([
      countMap(getValue(reports.no_entry_root_cause, ["lifecycle_phase_distribution"])),
      countMap(getValue(reports.market_readiness_probe, ["lifecycle_phase_probe_distribution"])),
      countMap(getValue(reports.decision_cycle_timing_probe, ["lifecycle_phase_distribution"])),
      countMap(getValue(reports.compact_run_summary, ["candidate_timing_diagnostics", "lifecycle_phase_counts"])),
      countMap(getValue(reports.session_runtime, ["scanner_lifecycle", "lifecycle_phase_counts"])),
    ]) ?? {}
  );
}

function firstNonEmptyMap(maps: Array<Record<string, number>>): Record<string, number> | undefined {
  return maps.find((item) => Object.keys(item).length > 0);
}

function namedObjectFromReport(report: JsonObject | undefined, name: string): JsonObject {
  if (!report) return {};
  const containers = [
    report,
    getValue(report, ["strategies"]),
    getValue(report, ["strategy_results"]),
    getValue(report, ["results"]),
    getValue(report, ["scenario_results"]),
    getValue(report, ["comparison"]),
  ];
  for (const container of containers) {
    if (isObject(container) && isObject(container[name])) return container[name];
    if (Array.isArray(container)) {
      const found = container.find(
        (item) =>
          isObject(item) &&
          firstString([item.strategy, item.strategy_name, item.scenario, item.name], "") === name,
      );
      if (isObject(found)) return found;
    }
  }
  return {};
}

function buildProfitManagementRows(report: JsonObject | undefined): ProfitStrategyResult[] {
  return profitManagementStrategyNames.map((name) => {
    const result = namedObjectFromReport(report, name);
    return {
      name,
      realizedProxyPnl: firstNumber([
        getValue(result, ["realized_proxy_pnl"]),
        getValue(result, ["realized_pnl_proxy"]),
        getValue(result, ["proxy_pnl"]),
        getValue(result, ["gross_pnl"]),
        getValue(result, ["realized_pnl"]),
      ]),
      pnlUpliftVsBaseline: firstNumber([
        getValue(result, ["pnl_uplift_vs_baseline"]),
        getValue(result, ["uplift_vs_baseline"]),
        getValue(result, ["pnl_delta_vs_baseline"]),
        getValue(result, ["uplift"]),
      ]),
      maxDrawdown: firstNumber([getValue(result, ["max_drawdown"]), getValue(result, ["max_dd"]), getValue(result, ["drawdown"])]),
      winRate: firstNumber([getValue(result, ["win_rate"]), getValue(result, ["winning_rate"])]),
      runnerContribution: firstNumber([
        getValue(result, ["runner_contribution"]),
        getValue(result, ["runner_pnl_contribution"]),
        getValue(result, ["runner_proxy_pnl"]),
        getValue(result, ["runner_pnl"]),
      ]),
      forcedDeriskCount: firstNumber([
        getValue(result, ["forced_derisk_count"]),
        getValue(result, ["forced_derisks"]),
        getValue(result, ["forced_derisk_events"]),
      ]),
      lateWindowDecayAvoided: firstNumber([
        getValue(result, ["late_window_decay_avoided"]),
        getValue(result, ["late_decay_avoided"]),
        getValue(result, ["decay_avoided"]),
      ]),
      btcContribution: firstNumber([
        getValue(result, ["btc_contribution"]),
        getValue(result, ["asset_contribution", "BTC"]),
        getValue(result, ["pnl_by_asset", "BTC"]),
      ]),
      ethContribution: firstNumber([
        getValue(result, ["eth_contribution"]),
        getValue(result, ["asset_contribution", "ETH"]),
        getValue(result, ["pnl_by_asset", "ETH"]),
      ]),
      verdict: firstString([getValue(result, ["verdict"]), getValue(result, ["status"]), getValue(result, ["recommendation"])], "AWAITING"),
    };
  });
}

function buildExitConvergenceSummary(report: JsonObject | undefined): ExitConvergenceSummary {
  const summary = firstObject([
    getValue(report, ["summary"]),
    getValue(report, ["exit_convergence_summary"]),
    getValue(report, ["policy_comparison"]),
    report,
  ]) ?? {};
  const btc = firstObject([
    getValue(summary, ["btc_convergence_behavior"]),
    getValue(summary, ["asset_convergence_behavior", "BTC"]),
    getValue(summary, ["btc"]),
    getValue(report, ["asset_convergence_behavior", "BTC"]),
  ]) ?? {};
  const eth = firstObject([
    getValue(summary, ["eth_convergence_behavior"]),
    getValue(summary, ["asset_convergence_behavior", "ETH"]),
    getValue(summary, ["eth"]),
    getValue(report, ["asset_convergence_behavior", "ETH"]),
  ]) ?? {};

  return {
    hasReport: Boolean(report),
    realizedProxyPnl: firstNumber([
      getValue(summary, ["realized_proxy_pnl"]),
      getValue(summary, ["realized_pnl_proxy"]),
      getValue(summary, ["proxy_pnl"]),
      getValue(summary, ["gross_pnl"]),
    ]),
    upliftVsPolicyD: firstNumber([
      getValue(summary, ["uplift_vs_policy_d"]),
      getValue(summary, ["pnl_uplift_vs_policy_d"]),
      getValue(summary, ["uplift_vs_Policy_D"]),
      getValue(summary, ["policy_d_uplift"]),
    ]),
    maxDrawdown: firstNumber([getValue(summary, ["max_drawdown"]), getValue(summary, ["max_dd"]), getValue(summary, ["drawdown"])]),
    convergenceExitCount: firstNumber([
      getValue(summary, ["convergence_exit_count"]),
      getValue(summary, ["convergence_exits"]),
      getValue(summary, ["dynamic_convergence_exit_count"]),
    ]),
    averageExitSr: firstNumber([
      getValue(summary, ["average_exit_sr"]),
      getValue(summary, ["avg_exit_sr"]),
      getValue(summary, ["mean_exit_sr"]),
      getValue(summary, ["average_exit_settlement_ratio"]),
    ]),
    convergenceStabilityScore: firstNumber([
      getValue(summary, ["convergence_stability_score"]),
      getValue(summary, ["stability_score"]),
      getValue(summary, ["convergence_quality_score"]),
    ]),
    falseConvergenceExits: firstNumber([
      getValue(summary, ["false_convergence_exits"]),
      getValue(summary, ["false_convergence_exit_count"]),
      getValue(summary, ["false_positive_convergence_exits"]),
    ]),
    lateReversalCount: firstNumber([
      getValue(summary, ["late_reversal_count"]),
      getValue(summary, ["late_reversals"]),
      getValue(summary, ["late_window_reversal_count"]),
    ]),
    btcBehavior: firstString([
      getValue(btc, ["behavior"]),
      getValue(btc, ["verdict"]),
      getValue(btc, ["summary"]),
      getValue(summary, ["btc_convergence_behavior"]),
    ], "AWAITING"),
    ethBehavior: firstString([
      getValue(eth, ["behavior"]),
      getValue(eth, ["verdict"]),
      getValue(eth, ["summary"]),
      getValue(summary, ["eth_convergence_behavior"]),
    ], "AWAITING"),
    uncertaintyCollapseWindowEstimate: firstString([
      getValue(summary, ["uncertainty_collapse_window_estimate"]),
      getValue(summary, ["uncertainty_collapse_window"]),
      getValue(summary, ["collapse_window_estimate"]),
      getValue(summary, ["estimated_collapse_window"]),
    ], "AWAITING"),
    verdict: firstString([
      getValue(summary, ["verdict"]),
      getValue(summary, ["recommendation"]),
      getValue(summary, ["status"]),
      getValue(report, ["verdict"]),
    ], report ? "REPORT_AVAILABLE" : "AWAITING_REPLAY_REPORT"),
  };
}

function sortTimestamp(reports: Record<string, JsonObject>, newestFileUtc: string): string {
  const runRows = getValue(reports.quant_data_quality, ["run_id_summary", "run_ids"]);
  if (Array.isArray(runRows) && isObject(runRows[0])) {
    const lastTimestamp = getValue(runRows[0], ["last_timestamp_utc"]);
    if (typeof lastTimestamp === "string") return lastTimestamp;
  }
  return firstString(
    [
      getValue(reports.compact_run_summary, ["time_range", "last_timestamp_utc"]),
      reports.session_runtime?.generated_at_utc,
      reports.replay?.generated_at_utc,
      newestFileUtc,
    ],
    newestFileUtc,
  );
}

function buildSummary(
  date: string,
  runId: string,
  reports: Record<string, JsonObject>,
  sourceFiles: string[],
  newestFileUtc: string,
): ReportSummary {
  const quality = reports.quant_data_quality;
  const noEntry = reports.no_entry;
  const session = reports.session_runtime;
  const replay = reports.replay;
  const rootProbe = reports.no_entry_root_cause;
  const lifecycleTiming = reports.lifecycle_timing;
  const profitManagementReport = reports.lifecycle_profit_management;
  const exitConvergenceReport = reports.exit_convergence;
  const profitManagementRows = buildProfitManagementRows(profitManagementReport);
  const exitConvergence = buildExitConvergenceSummary(exitConvergenceReport);
  const timingMetrics = firstObject([getValue(lifecycleTiming, ["timing_metrics"])]) ?? {};
  const continuity = getValue(quality, ["replay_continuity"]);
  const ordering = getValue(quality, ["timestamp_ordering"]);
  const continuityObject = isObject(continuity) ? continuity : {};
  const orderingObject = isObject(ordering) ? ordering : {};
  const coverage =
    firstObject([
      getValue(noEntry, ["phase2_coverage"]),
      getValue(session, ["phase2_coverage"]),
      getValue(replay, ["phase2_coverage"]),
      getValue(quality, ["phase2_coverage"]),
    ]) ?? {};
  const evField = firstObject([getValue(coverage, ["ev_null_reason_coverage", "fields", "ev_after_spread"])]) ?? {};
  const compactEv = firstObject([getValue(reports.compact_run_summary, ["ev_visibility"])]) ?? {};
  const spreadSummary =
    firstObject([
      getValue(session, ["spread_liquidity_readiness_summary"]),
      getValue(noEntry, ["spread_liquidity_readiness_summary"]),
      getValue(replay, ["spread_liquidity_readiness_summary"]),
    ]) ?? {};
  const marketReadiness = firstObject([getValue(session, ["market_readiness"])]) ?? {};
  const orderbook = firstObject([getValue(session, ["orderbook_readiness"])]) ?? {};
  const malformedImpact = firstObject([getValue(quality, ["malformed_json_impact"])]) ?? {};
  const rootCounts = firstNonEmptyMap([
    countMap(getValue(noEntry, ["root_cause_counts"])),
    countMap(getValue(rootProbe, ["category_counts"])),
  ]) ?? {};
  const timeUnsafe = firstNumber([
    getValue(noEntry, ["count_time_unsafe"]),
    getValue(session, ["skip_summary", "skip_reason_counts", "time_unsafe"]),
    getValue(session, ["cutoff_behavior", "time_unsafe_count"]),
    getValue(rootProbe, ["primary_reason_counts", "cutoff_passed"]),
    getValue(rootProbe, ["category_counts", "timing"]),
  ]);
  const riskPlanZero = firstNumber([
    getValue(noEntry, ["count_risk_plan_zero"]),
    getValue(session, ["skip_summary", "skip_reason_counts", "risk_plan_zero"]),
    getValue(session, ["risk_blocks", "risk_plan_zero_count"]),
    getValue(rootProbe, ["primary_reason_counts", "zero_size_plan"]),
    getValue(rootProbe, ["category_counts", "risk"]),
  ]);
  const selectedBadLines = firstNumber([
    getValue(malformedImpact, ["matching_run_id_malformed_json_lines"]),
    getValue(quality, ["bad_json_lines"]),
    getValue(noEntry, ["bad_json_lines"]),
    getValue(replay, ["bad_json_lines"]),
  ]);
  const unavailable = numberValue(getValue(orderbook, ["orderbook_unavailable_count"]));
  const empty = numberValue(getValue(marketReadiness, ["empty_book_count"]));
  const stale = numberValue(getValue(marketReadiness, ["stale_book_count"]));
  const hasLiquidityEvidence =
    Object.keys(marketReadiness).length > 0 || Object.keys(orderbook).length > 0 || Object.keys(spreadSummary).length > 0;
  const executionFailures = firstNumber([
    getValue(noEntry, ["execution_failure_count"]),
    getValue(session, ["execution_summary", "execution_failure_count"]),
    getValue(replay, ["execution_failure_count"]),
  ]);
  const tradeCount = firstNumber([
    getValue(replay, ["total_trades"]),
    getValue(session, ["paper_trade_summary", "entered"]),
    getValue(session, ["paper_trade_summary", "trade_count"]),
  ]);
  const paperFills = firstNumber([
    getValue(session, ["execution_summary", "paper_fill_count"]),
    getValue(session, ["paper_trade_summary", "paper_fills"]),
    getValue(noEntry, ["paper_fill_count"]),
  ]);
  const paperExits = firstNumber([
    getValue(session, ["paper_trade_summary", "paper_exits"]),
    getValue(replay, ["total_trades"]),
  ]);
  const grossPnl = firstNumber([
    getValue(session, ["paper_trade_summary", "gross_pnl"]),
    getValue(session, ["gross_pnl"]),
    getValue(replay, ["gross_pnl"]),
  ]);
  const liveReadinessClaim =
    getValue(session, ["live_readiness_claim"]) === true ||
    getValue(replay, ["live_readiness_claim"]) === true ||
    getValue(noEntry, ["live_readiness_claim"]) === true;
  const continuityStatus = firstString([continuityObject.status, orderingObject.status], "UNKNOWN");
  const malformedAffectsRun = getValue(malformedImpact, ["affects_selected_run"]) === true;
  const whySkippedText = [
    firstString([getValue(noEntry, ["root_cause_category"]), getValue(session, ["primary_bottleneck"]), rootProbeLabel(rootProbe)], "UNKNOWN"),
    firstString([getValue(session, ["secondary_bottleneck"])], "UNKNOWN"),
  ]
    .filter((value) => value !== "UNKNOWN")
    .join(" + ");

  return {
    date,
    runId,
    hasRunId: runId !== "unscoped" && runId !== "unknown",
    sortTimestampUtc: sortTimestamp(reports, newestFileUtc),
    continuity: {
      status: continuityStatus,
      trustworthyForReplay: continuityObject.trustworthy_for_replay === true,
      timestampOrdering: firstString([orderingObject.status], "UNKNOWN"),
      chainGaps: numberValue(continuityObject.run_chain_gap_count),
      eventsChecked: numberValue(continuityObject.events_checked),
    },
    rootCause: {
      primary: firstString(
        [getValue(noEntry, ["root_cause_category"]), getValue(session, ["primary_bottleneck"]), rootProbeLabel(rootProbe)],
        "UNKNOWN",
      ),
      secondary: firstString([getValue(session, ["secondary_bottleneck"])], "UNKNOWN"),
      counts: rootCounts,
      executionStageAttempts: firstNumber([
        getValue(noEntry, ["execution_stage_attempt_count"]),
        getValue(noEntry, ["order_submit_attempt_count"]),
        getValue(session, ["execution_summary", "order_submit_attempt_count"]),
      ]),
    },
    timeUnsafeCount: timeUnsafe,
    riskPlanZeroCount: riskPlanZero,
    lifecycleDistribution: lifecycleDistribution(reports),
    evVisibility: {
      status: firstString([getValue(compactEv, ["ev_visibility_status"])], "UNKNOWN"),
      valueEvents: numberValue(getValue(evField, ["value_events"])),
      nullEvents: numberValue(getValue(evField, ["null_events"])),
      nullReasonCoverageRate: numberValue(getValue(evField, ["null_reason_coverage_rate"])),
      topNullReasons: countMap(getValue(evField, ["null_reasons"])),
    },
    liquidityOrderbook: {
      status: hasLiquidityEvidence ? (unavailable + empty + stale === 0 ? "READY" : "ATTENTION") : "UNKNOWN",
      readinessStatus: firstString([getValue(spreadSummary, ["status"])], "UNKNOWN"),
      orderbookUnavailableCount: unavailable,
      emptyBookCount: empty,
      staleBookCount: stale,
      spreadNormalizationRate: numberValue(getValue(spreadSummary, ["spread_normalization_rate"])),
      liquidityStates: countMap(getValue(spreadSummary, ["liquidity_states"])),
    },
    badJson: {
      warning: selectedBadLines > 0 || getValue(malformedImpact, ["affects_selected_run"]) === true,
      selectedRunBadLines: selectedBadLines,
      totalScannedBadLines: firstNumber([
        getValue(malformedImpact, ["total_malformed_json_lines_in_scanned_files"]),
        getValue(quality, ["bad_lines_count"]),
      ]),
      affectsSelectedRun: getValue(malformedImpact, ["affects_selected_run"]) === true,
      status: firstString([getValue(malformedImpact, ["status"])], "UNKNOWN"),
    },
    lifecycleTiming: {
      hasReport: Boolean(lifecycleTiming),
      cutoffSurvivalRate: numberValue(getValue(timingMetrics, ["cutoff_survival_rate"])),
      cutoffStarvationRate: numberValue(getValue(timingMetrics, ["cutoff_starvation_rate"])),
      executableAgeBeforeSkipP50: numberValue(getValue(timingMetrics, ["executable_age_before_skip_seconds", "p50"])),
      revisitDelayP50: numberValue(getValue(timingMetrics, ["revisit_delay_distribution_seconds", "p50"])),
      revisitDelayP90: numberValue(getValue(timingMetrics, ["revisit_delay_distribution_seconds", "p90"])),
      executableToDecisionP50: numberValue(getValue(timingMetrics, ["executable_to_decision_seconds", "p50"])),
      executableToDecisionP90: numberValue(getValue(timingMetrics, ["executable_to_decision_seconds", "p90"])),
      timeToFinalDeriskP50: numberValue(getValue(timingMetrics, ["time_to_FINAL_DERISK_seconds", "p50"])),
    },
    plainSummary: {
      dataClean:
        continuityStatus.toUpperCase().includes("PASS") && !malformedAffectsRun
          ? "Yes, scoped run evidence is usable"
          : "Needs review",
      botTradedPaper: tradeCount > 0 || paperFills > 0 ? `Yes: ${tradeCount} trades, ${paperFills} fills, ${paperExits} exits` : "No paper trades found",
      pnl: `${grossPnl >= 0 ? "+" : ""}${grossPnl.toFixed(8)}`,
      whySkipped: whySkippedText || "UNKNOWN",
      executionFailures: executionFailures === 0 ? "0 failures" : `${executionFailures} failures`,
      liveReadiness: liveReadinessClaim ? "Unexpected live readiness claim present" : "No live readiness claim",
    },
    profitManagement: {
      hasReport: Boolean(profitManagementReport),
      strategies: profitManagementRows,
      verdict: firstString(
        [
          getValue(profitManagementReport, ["verdict"]),
          getValue(profitManagementReport, ["summary", "verdict"]),
          getValue(profitManagementReport, ["best_strategy"]),
        ],
        profitManagementReport ? "REPORT_AVAILABLE" : "AWAITING_REPLAY_REPORT",
      ),
    },
    exitConvergence,
    timelineCards: [
      {
        title: "Report Coverage",
        items: {
          source_files: sourceFiles.length,
          report_kinds: Object.keys(reports).length,
        },
      },
      {
        title: "Continuity Gate",
        items: {
          events_checked: numberValue(continuityObject.events_checked),
          chain_gaps: numberValue(continuityObject.run_chain_gap_count),
          timestamp_ordering: firstString([orderingObject.status], "UNKNOWN"),
        },
      },
      {
        title: "Replay Summary",
        items: {
          events_loaded: numberValue(getValue(replay, ["events_loaded"])),
          approved_decisions: firstNumber([
            getValue(replay, ["approved_decisions"]),
            getValue(session, ["execution_summary", "approved_decisions"]),
          ]),
          rejected_decisions: numberValue(getValue(session, ["execution_summary", "rejected_decisions"])),
          cutoff_blocks: firstNumber([
            getValue(replay, ["cutoff_block_count"]),
            getValue(session, ["cutoff_behavior", "cutoff_block_count"]),
          ]),
        },
      },
      {
        title: "Execution Evidence",
        items: {
          execution_events_loaded: firstNumber([
            getValue(noEntry, ["execution_events_loaded"]),
            getValue(session, ["execution_summary", "execution_events_loaded"]),
          ]),
          submit_attempts: firstNumber([
            getValue(noEntry, ["order_submit_attempt_count"]),
            getValue(session, ["execution_summary", "order_submit_attempt_count"]),
          ]),
          failures: executionFailures,
          paper_fills: paperFills,
        },
      },
      {
        title: "Lifecycle Timing",
        items: {
          cutoff_survival: formatPercent(numberValue(getValue(timingMetrics, ["cutoff_survival_rate"]))),
          cutoff_starvation: formatPercent(numberValue(getValue(timingMetrics, ["cutoff_starvation_rate"]))),
          executable_age_p50: formatSeconds(numberValue(getValue(timingMetrics, ["executable_age_before_skip_seconds", "p50"]))),
          revisit_p90: formatSeconds(numberValue(getValue(timingMetrics, ["revisit_delay_distribution_seconds", "p90"]))),
        },
      },
    ],
    sourceFiles: sourceFiles.sort(),
  };
}

function firstObject(values: unknown[]): JsonObject | undefined {
  for (const value of values) {
    if (isObject(value)) return value;
  }
  return undefined;
}

async function loadReports(): Promise<{ records: ReportSummary[]; latest?: ReportSummary; ignoredFiles: string[] }> {
  const groups = new Map<
    string,
    { date: string; runId: string; reports: Record<string, JsonObject>; sourceFiles: string[]; newestFileUtc: string }
  >();
  const ignoredFiles: string[] = [];
  let files: string[] = [];

  try {
    files = (await readdir(reportDir)).filter((fileName) => fileName.endsWith(".json"));
  } catch {
    return { records: [], ignoredFiles: [] };
  }

  for (const fileName of files.sort()) {
    const detected = detectReport(fileName);
    if (!detected) {
      ignoredFiles.push(fileName);
      continue;
    }
    const filePath = path.join(reportDir, fileName);
    let parsed: unknown;
    try {
      parsed = JSON.parse(await readFile(filePath, "utf8"));
    } catch {
      ignoredFiles.push(fileName);
      continue;
    }
    if (!isObject(parsed)) {
      ignoredFiles.push(fileName);
      continue;
    }
    const runId = reportRunId(parsed, detected.runId);
    const key = `${detected.date}::${runId}`;
    const current =
      groups.get(key) ??
      {
        date: detected.date,
        runId,
        reports: {},
        sourceFiles: [],
        newestFileUtc: "",
      };
    current.reports[detected.kind] = parsed;
    current.sourceFiles.push(fileName);
    const modified = (await stat(filePath)).mtime.toISOString();
    if (modified > current.newestFileUtc) current.newestFileUtc = modified;
    groups.set(key, current);
  }

  const records = Array.from(groups.values())
    .map((group) => buildSummary(group.date, group.runId, group.reports, group.sourceFiles, group.newestFileUtc))
    .sort((a, b) => {
      const runScore = Number(b.hasRunId) - Number(a.hasRunId);
      if (runScore !== 0) return runScore;
      return `${b.sortTimestampUtc}${b.runId}`.localeCompare(`${a.sortTimestampUtc}${a.runId}`);
    });
  return { records, latest: records.find((record) => record.hasRunId) ?? records[0], ignoredFiles };
}

function statusTone(status: string): string {
  const normalized = status.toUpperCase();
  if (normalized.includes("PASS") || normalized.includes("READY")) return "#4ade80";
  if (normalized.includes("FAIL") || normalized.includes("BAD")) return "#fb7185";
  if (normalized.includes("WARN") || normalized.includes("UNKNOWN") || normalized.includes("ATTENTION")) return "#fbbf24";
  return "#60a5fa";
}

function MetricCard({ label, value, detail, tone }: { label: string; value: ReactNode; detail?: ReactNode; tone?: string }) {
  return (
    <section style={styles.metricCard}>
      <div style={styles.metricLabel}>{label}</div>
      <div style={{ ...styles.metricValue, color: tone ?? "#f8fafc" }}>{value}</div>
      {detail ? <div style={styles.metricDetail}>{detail}</div> : null}
    </section>
  );
}

function SummaryCard({ question, answer, tone }: { question: string; answer: string; tone: string }) {
  return (
    <section style={styles.summaryCard}>
      <div style={styles.summaryQuestion}>{question}</div>
      <div style={{ ...styles.summaryAnswer, color: tone }}>{answer}</div>
    </section>
  );
}

function BarList({ data }: { data: Record<string, number> }) {
  const rows = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...rows.map(([, value]) => value), 1);
  if (!rows.length) return <p style={styles.muted}>No lifecycle distribution in selected reports.</p>;
  return (
    <div style={styles.barList}>
      {rows.map(([label, value]) => (
        <div key={label} style={styles.barRow}>
          <span style={styles.barLabel}>{label}</span>
          <span style={styles.barTrack}>
            <span style={{ ...styles.barFill, width: `${Math.max(2, (value / max) * 100)}%` }} />
          </span>
          <span style={styles.barCount}>{value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

function DetailList({ items }: { items: Record<string, ReactNode> }) {
  return (
    <dl style={styles.detailList}>
      {Object.entries(items).map(([key, value]) => (
        <div key={key} style={styles.detailRow}>
          <dt style={styles.detailTerm}>{key.replaceAll("_", " ")}</dt>
          <dd style={styles.detailDef}>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ProfitManagementTable({ rows, hasReport }: { rows: ProfitStrategyResult[]; hasReport: boolean }) {
  if (!hasReport) {
    return (
      <div style={styles.placeholder}>
        Awaiting <code>lifecycle_profit_management_replay_YYYY-MM-DD_run_RUN_ID.json</code>. This panel is read-only and will compare
        baseline hold, partial reductions, dynamic derisk, and late-decay cutting once the replay report exists.
      </div>
    );
  }
  return (
    <div style={styles.tableWrap}>
      <table style={styles.compactTable}>
        <thead>
          <tr>
            <th style={styles.th}>Strategy</th>
            <th style={styles.th}>Proxy PnL</th>
            <th style={styles.th}>Uplift</th>
            <th style={styles.th}>Max DD</th>
            <th style={styles.th}>Win</th>
            <th style={styles.th}>Runner</th>
            <th style={styles.th}>Forced</th>
            <th style={styles.th}>Decay</th>
            <th style={styles.th}>BTC/ETH</th>
            <th style={styles.th}>Verdict</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name}>
              <td style={styles.td}>{row.name}</td>
              <td style={styles.td}>{formatPnl(row.realizedProxyPnl)}</td>
              <td style={styles.td}>{formatPnl(row.pnlUpliftVsBaseline)}</td>
              <td style={styles.td}>{formatPnl(row.maxDrawdown)}</td>
              <td style={styles.td}>{formatPercent(row.winRate)}</td>
              <td style={styles.td}>{formatPnl(row.runnerContribution)}</td>
              <td style={styles.td}>{row.forcedDeriskCount.toLocaleString()}</td>
              <td style={styles.td}>{formatPnl(row.lateWindowDecayAvoided)}</td>
              <td style={styles.td}>
                {formatPnl(row.btcContribution)} / {formatPnl(row.ethContribution)}
              </td>
              <td style={styles.td}>{row.verdict}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExitConvergencePanel({ summary }: { summary: ExitConvergenceSummary }) {
  if (!summary.hasReport) {
    return (
      <div style={styles.placeholder}>
        Awaiting <code>exit_convergence_intelligence_replay_YYYY-MM-DD_run_RUN_ID.json</code>. This panel is read-only and
        will compare dynamic convergence exits against Policy D once the replay report exists.
      </div>
    );
  }
  return (
    <DetailList
      items={{
        realized_proxy_pnl: formatPnl(summary.realizedProxyPnl),
        uplift_vs_Policy_D: formatPnl(summary.upliftVsPolicyD),
        max_drawdown: formatPnl(summary.maxDrawdown),
        convergence_exit_count: summary.convergenceExitCount.toLocaleString(),
        average_exit_SR: formatRatio(summary.averageExitSr),
        convergence_stability_score: formatRatio(summary.convergenceStabilityScore),
        false_convergence_exits: summary.falseConvergenceExits.toLocaleString(),
        late_reversal_count: summary.lateReversalCount.toLocaleString(),
        BTC_convergence_behavior: summary.btcBehavior,
        ETH_convergence_behavior: summary.ethBehavior,
        uncertainty_collapse_window_estimate: summary.uncertaintyCollapseWindowEstimate,
        verdict: summary.verdict,
      }}
    />
  );
}

export default async function OfflineReportsPage() {
  const { records, latest, ignoredFiles } = await loadReports();
  const selected = latest;
  const telegramCommand = selected
    ? `python tools/offline_telegram_summary.py --date ${selected.date} --run-id ${selected.runId}`
    : "python tools/offline_telegram_summary.py --date YYYY-MM-DD --run-id RUN_ID";

  return (
    <main style={styles.page}>
      <section style={styles.header}>
        <div>
          <p style={styles.eyebrow}>Read-only local evidence viewer</p>
          <h1 style={styles.title}>Offline Quant Reports</h1>
          <p style={styles.subtitle}>Reads completed JSON reports from runtime/reports only. No live APIs, no runtime writes.</p>
        </div>
        <div style={styles.commandPanel}>
          <code style={styles.command}>python dashboard/offline_quant_report_dashboard.py --reports-dir runtime/reports --host 127.0.0.1 --port 8765</code>
          <code style={styles.command}>{telegramCommand}</code>
        </div>
      </section>

      {selected ? (
        <>
          <section style={styles.metricsGrid}>
            <MetricCard label="Latest run_id" value={selected.runId} detail={selected.sortTimestampUtc} tone="#93c5fd" />
            <MetricCard
              label="Continuity"
              value={selected.continuity.status}
              detail={`ordering ${selected.continuity.timestampOrdering}`}
              tone={statusTone(selected.continuity.status)}
            />
            <MetricCard
              label="Root cause"
              value={selected.rootCause.primary}
              detail={`secondary ${selected.rootCause.secondary}`}
              tone="#e2e8f0"
            />
            <MetricCard label="time_unsafe" value={selected.timeUnsafeCount.toLocaleString()} detail="cutoff/time blocks" tone="#fbbf24" />
            <MetricCard label="risk_plan_zero" value={selected.riskPlanZeroCount.toLocaleString()} detail="zero-size plans" tone="#fbbf24" />
          </section>

          <section style={styles.summaryGrid}>
            <SummaryCard question="Data clean?" answer={selected.plainSummary.dataClean} tone={statusTone(selected.continuity.status)} />
            <SummaryCard question="Bot traded in paper?" answer={selected.plainSummary.botTradedPaper} tone="#93c5fd" />
            <SummaryCard question="PnL?" answer={selected.plainSummary.pnl} tone={selected.plainSummary.pnl.startsWith("-") ? "#fb7185" : "#4ade80"} />
            <SummaryCard question="Why skipped?" answer={selected.plainSummary.whySkipped} tone="#fbbf24" />
            <SummaryCard question="Execution failures?" answer={selected.plainSummary.executionFailures} tone={selected.plainSummary.executionFailures === "0 failures" ? "#4ade80" : "#fb7185"} />
            <SummaryCard question="Live readiness?" answer={selected.plainSummary.liveReadiness} tone="#fbbf24" />
          </section>

          <section style={styles.twoColumn}>
            <Panel title="Lifecycle distribution">
              <BarList data={selected.lifecycleDistribution} />
            </Panel>
            <Panel title="EV / probability visibility">
              <DetailList
                items={{
                  status: selected.evVisibility.status,
                  ev_value_events: selected.evVisibility.valueEvents.toLocaleString(),
                  ev_null_events: selected.evVisibility.nullEvents.toLocaleString(),
                  null_reason_coverage_rate: selected.evVisibility.nullReasonCoverageRate,
                  top_null_reasons: formatCounts(selected.evVisibility.topNullReasons),
                }}
              />
            </Panel>
          </section>

          <section style={styles.twoColumn}>
            <Panel title="Liquidity / orderbook readiness">
              <DetailList
                items={{
                  status: selected.liquidityOrderbook.status,
                  readiness_status: selected.liquidityOrderbook.readinessStatus,
                  orderbook_unavailable: selected.liquidityOrderbook.orderbookUnavailableCount.toLocaleString(),
                  empty_book: selected.liquidityOrderbook.emptyBookCount.toLocaleString(),
                  stale_book: selected.liquidityOrderbook.staleBookCount.toLocaleString(),
                  spread_normalization_rate: selected.liquidityOrderbook.spreadNormalizationRate,
                  liquidity_states: formatCounts(selected.liquidityOrderbook.liquidityStates),
                }}
              />
            </Panel>
            <Panel title="Lifecycle timing pressure">
              <p style={styles.thaiExplanation}>ระบบเห็นโอกาสแล้ว แต่กลับมาดู/ตัดสินใจช้าเกินจนเข้าใกล้หมดเวลา</p>
              <DetailList
                items={{
                  report_status: selected.lifecycleTiming.hasReport ? "AVAILABLE" : "MISSING",
                  cutoff_survival_rate: formatPercent(selected.lifecycleTiming.cutoffSurvivalRate),
                  cutoff_starvation_rate: formatPercent(selected.lifecycleTiming.cutoffStarvationRate),
                  executable_age_before_skip_p50: formatSeconds(selected.lifecycleTiming.executableAgeBeforeSkipP50),
                  revisit_delay_p50: formatSeconds(selected.lifecycleTiming.revisitDelayP50),
                  revisit_delay_p90: formatSeconds(selected.lifecycleTiming.revisitDelayP90),
                  executable_to_decision_p50: formatSeconds(selected.lifecycleTiming.executableToDecisionP50),
                  executable_to_decision_p90: formatSeconds(selected.lifecycleTiming.executableToDecisionP90),
                  time_to_FINAL_DERISK_p50: formatSeconds(selected.lifecycleTiming.timeToFinalDeriskP50),
                }}
              />
            </Panel>
          </section>

          <section style={styles.twoColumn}>
            <Panel title="Bad JSON warning">
              <DetailList
                items={{
                  warning: selected.badJson.warning ? "YES" : "NO",
                  status: selected.badJson.status,
                  affects_selected_run: selected.badJson.affectsSelectedRun ? "YES" : "NO",
                  selected_run_bad_lines: selected.badJson.selectedRunBadLines.toLocaleString(),
                  total_scanned_bad_lines: selected.badJson.totalScannedBadLines.toLocaleString(),
                }}
              />
            </Panel>
            <Panel title="Lifecycle profit management replay">
              <ProfitManagementTable rows={selected.profitManagement.strategies} hasReport={selected.profitManagement.hasReport} />
              <p style={styles.footerNote}>Verdict: {selected.profitManagement.verdict}</p>
            </Panel>
          </section>

          <section style={styles.twoColumn}>
            <Panel title="Exit convergence intelligence replay">
              <p style={styles.thaiExplanation}>
                หน้านี้วัดว่า YES book เริ่ม converge เข้า settlement ก่อนหมดเวลาจริงไหม และ exit แบบ dynamic ดีกว่า SR&lt;60 คงที่หรือไม่
              </p>
              <ExitConvergencePanel summary={selected.exitConvergence} />
            </Panel>
          </section>

          <section style={styles.timelineGrid}>
            {selected.timelineCards.map((card) => (
              <Panel key={card.title} title={card.title}>
                <DetailList items={card.items} />
              </Panel>
            ))}
          </section>
        </>
      ) : (
        <section style={styles.emptyState}>No completed offline report JSON files found in runtime/reports.</section>
      )}

      <Panel title="Report records">
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Run ID</th>
                <th style={styles.th}>Date</th>
                <th style={styles.th}>Continuity</th>
                <th style={styles.th}>Root Cause</th>
                <th style={styles.th}>Blocks</th>
                <th style={styles.th}>Advanced / Debug</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={`${record.date}-${record.runId}`}>
                  <td style={styles.td}>{record.runId}</td>
                  <td style={styles.td}>{record.date}</td>
                  <td style={{ ...styles.td, color: statusTone(record.continuity.status) }}>{record.continuity.status}</td>
                  <td style={styles.td}>
                    {record.rootCause.primary}
                    <br />
                    <span style={styles.muted}>secondary {record.rootCause.secondary}</span>
                  </td>
                  <td style={styles.td}>
                    time_unsafe {record.timeUnsafeCount}
                    <br />
                    risk_plan_zero {record.riskPlanZeroCount}
                  </td>
                  <td style={styles.td}>
                    <details style={styles.debugDetails}>
                      <summary>{record.sourceFiles.length} source reports</summary>
                      <div style={styles.debugList}>{record.sourceFiles.join(", ")}</div>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {ignoredFiles.length ? (
          <details style={styles.debugDetails}>
            <summary style={styles.footerNote}>Advanced/debug: {ignoredFiles.length} unrecognized report files ignored</summary>
            <div style={styles.debugList}>{ignoredFiles.join(", ")}</div>
          </details>
        ) : null}
      </Panel>
    </main>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={styles.panel}>
      <h2 style={styles.panelTitle}>{title}</h2>
      {children}
    </section>
  );
}

function formatCounts(counts: Record<string, number>): string {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return "none";
  return entries.map(([key, value]) => `${key}: ${value}`).join(", ");
}

function formatPercent(value: number): string {
  if (!Number.isFinite(value)) return "0.00%";
  return `${(value * 100).toFixed(2)}%`;
}

function formatSeconds(value: number): string {
  if (!Number.isFinite(value)) return "0.000s";
  return `${value.toFixed(3)}s`;
}

function formatPnl(value: number): string {
  if (!Number.isFinite(value)) return "0.00000000";
  return `${value >= 0 ? "+" : ""}${value.toFixed(8)}`;
}

function formatRatio(value: number): string {
  if (!Number.isFinite(value)) return "0.0000";
  return value.toFixed(4);
}

const styles: Record<string, CSSProperties> = {
  page: {
    minHeight: "100vh",
    maxHeight: "100vh",
    overflowY: "auto",
    background: "#0b0f14",
    color: "#e5edf6",
    padding: "28px",
  },
  header: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1.2fr) minmax(320px, 0.8fr)",
    gap: 20,
    alignItems: "end",
    marginBottom: 18,
  },
  eyebrow: {
    color: "#67e8f9",
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: 0,
    textTransform: "uppercase",
    marginBottom: 8,
  },
  title: {
    fontSize: 34,
    lineHeight: 1.1,
    letterSpacing: 0,
    marginBottom: 8,
  },
  subtitle: {
    color: "#94a3b8",
    maxWidth: 760,
  },
  commandPanel: {
    border: "1px solid #263244",
    borderRadius: 8,
    background: "#111827",
    padding: 12,
    display: "grid",
    gap: 8,
  },
  command: {
    display: "block",
    color: "#c4b5fd",
    fontSize: 12,
    lineHeight: 1.45,
    overflowWrap: "anywhere",
  },
  metricsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
    gap: 12,
    marginBottom: 12,
  },
  summaryGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
    gap: 12,
    marginBottom: 12,
  },
  summaryCard: {
    border: "1px solid #263244",
    borderRadius: 8,
    background: "#0f1825",
    padding: 14,
    minWidth: 0,
  },
  summaryQuestion: {
    color: "#8ea0b8",
    fontSize: 12,
    fontWeight: 800,
    marginBottom: 8,
  },
  summaryAnswer: {
    fontSize: 16,
    fontWeight: 800,
    lineHeight: 1.3,
    overflowWrap: "anywhere",
  },
  metricCard: {
    border: "1px solid #263244",
    borderRadius: 8,
    background: "#101722",
    padding: 14,
    minWidth: 0,
  },
  metricLabel: {
    color: "#8ea0b8",
    fontSize: 12,
    fontWeight: 700,
    marginBottom: 8,
  },
  metricValue: {
    fontSize: 22,
    fontWeight: 800,
    lineHeight: 1.15,
    overflowWrap: "anywhere",
  },
  metricDetail: {
    color: "#7f8da3",
    fontSize: 12,
    marginTop: 8,
    overflowWrap: "anywhere",
  },
  twoColumn: {
    display: "grid",
    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    gap: 12,
    marginBottom: 12,
  },
  timelineGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
    gap: 12,
    marginBottom: 12,
  },
  panel: {
    border: "1px solid #263244",
    borderRadius: 8,
    background: "#101722",
    padding: 14,
    minWidth: 0,
  },
  panelTitle: {
    fontSize: 15,
    marginBottom: 12,
    color: "#f8fafc",
  },
  barList: {
    display: "grid",
    gap: 10,
  },
  barRow: {
    display: "grid",
    gridTemplateColumns: "190px 1fr 58px",
    gap: 10,
    alignItems: "center",
  },
  barLabel: {
    color: "#cbd5e1",
    fontSize: 12,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  barTrack: {
    height: 9,
    borderRadius: 999,
    background: "#1e293b",
    overflow: "hidden",
  },
  barFill: {
    display: "block",
    height: "100%",
    borderRadius: 999,
    background: "linear-gradient(90deg, #14b8a6, #60a5fa)",
  },
  barCount: {
    color: "#94a3b8",
    fontSize: 12,
    textAlign: "right",
  },
  detailList: {
    display: "grid",
    gap: 8,
  },
  detailRow: {
    display: "grid",
    gridTemplateColumns: "minmax(120px, 0.7fr) minmax(0, 1.3fr)",
    gap: 10,
  },
  detailTerm: {
    color: "#8ea0b8",
    fontSize: 12,
  },
  detailDef: {
    margin: 0,
    color: "#dbeafe",
    fontSize: 12,
    overflowWrap: "anywhere",
  },
  thaiExplanation: {
    color: "#f8fafc",
    background: "#172033",
    border: "1px solid #263244",
    borderRadius: 8,
    padding: "10px 12px",
    fontSize: 14,
    lineHeight: 1.5,
    marginBottom: 12,
  },
  tableWrap: {
    overflowX: "auto",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    tableLayout: "fixed",
  },
  compactTable: {
    width: "100%",
    borderCollapse: "collapse",
    tableLayout: "auto",
    minWidth: 980,
  },
  th: {
    color: "#8ea0b8",
    fontSize: 12,
    textAlign: "left",
    padding: "8px 6px",
    borderBottom: "1px solid #263244",
  },
  td: {
    color: "#dbeafe",
    fontSize: 12,
    verticalAlign: "top",
    padding: "9px 6px",
    borderBottom: "1px solid #1f2937",
    overflowWrap: "anywhere",
  },
  muted: {
    color: "#8ea0b8",
    fontSize: 12,
  },
  footerNote: {
    color: "#8ea0b8",
    fontSize: 12,
    marginTop: 12,
  },
  placeholder: {
    color: "#cbd5e1",
    background: "#172033",
    border: "1px solid #263244",
    borderRadius: 8,
    padding: 12,
    fontSize: 12,
    lineHeight: 1.5,
  },
  debugDetails: {
    color: "#8ea0b8",
    fontSize: 12,
  },
  debugList: {
    color: "#7f8da3",
    fontSize: 11,
    lineHeight: 1.5,
    marginTop: 8,
    overflowWrap: "anywhere",
  },
  emptyState: {
    border: "1px solid #263244",
    borderRadius: 8,
    background: "#101722",
    color: "#94a3b8",
    padding: 24,
    marginBottom: 12,
  },
};
