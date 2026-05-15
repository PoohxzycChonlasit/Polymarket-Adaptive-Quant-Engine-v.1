"""
Market Readiness Admission Probe Tool v1.

Offline aggregation of admission pipeline diagnostics from decision_log JSONL.
Answers the question: are markets truly not ready, or does the system have early
executable readiness that fails to reach the model/EV gate before cutoff?

Usage:
    python -m tools.market_readiness_admission_probe --date 2026-05-15
    python -m tools.market_readiness_admission_probe --date 2026-05-15 --write-report
    python -m tools.market_readiness_admission_probe --date 2026-05-15 --run-id <id>
    python -m tools.market_readiness_admission_probe --date 2026-05-15 --asset BTC

Output:
    Console summary + optional runtime/reports/market_readiness_admission_probe_YYYY-MM-DD.json

This tool is offline-only. It does not change runtime, strategy, risk,
execution, or paper/live separation.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    _repo_root = Path(__file__).resolve().parents[1]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

from utils.admission_probe_classifier import classify_admission_probe

DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")


# ---------------------------------------------------------------------------
# JSONL I/O
# ---------------------------------------------------------------------------

def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return events


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    p = event.get("payload") or {}
    return p if isinstance(p, dict) else {}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_decision_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
    asset_filter: str | None = None,
) -> list[dict[str, Any]]:
    path = quant_data_dir / "decision_log" / f"{date_str}.jsonl"
    events = _read_jsonl(path)
    if run_id:
        events = [e for e in events if e.get("run_id") == run_id]
    if asset_filter:
        af = asset_filter.upper()
        events = [
            e for e in events
            if str(_payload(e).get("asset") or _payload(e).get("ticker") or "").upper() == af
        ]
    return events


def _check_hybrid_phase_enabled(
    date_str: str,
    quant_data_dir: Path,
    run_id: str | None,
) -> bool:
    """Return True if any lifecycle_milestone events are present in research_log."""
    path = quant_data_dir / "research_log" / f"{date_str}.jsonl"
    events = _read_jsonl(path)
    if run_id:
        events = [e for e in events if e.get("run_id") == run_id]
    return any(
        _payload(e).get("event_subtype") == "lifecycle_milestone"
        for e in events
    )


# ---------------------------------------------------------------------------
# Record extraction
# ---------------------------------------------------------------------------

def extract_record(event: dict[str, Any]) -> dict[str, Any]:
    """
    Build a probe record from a decision event.
    Uses pre-emitted probe fields if present (runtime wrote them),
    otherwise classifies offline. Does not mutate the input event.
    """
    p = _payload(event)
    asset = str(p.get("asset") or p.get("ticker") or "UNKNOWN").upper()
    lifecycle_phase = str(p.get("lifecycle_phase") or "UNKNOWN")
    skip_reason_cat = str(p.get("skip_reason_category") or "")
    skip_reason_pri = str(p.get("skip_reason_primary") or "")
    normalized_skip = str(p.get("normalized_skip_reason") or "")
    seconds_remaining = p.get("seconds_remaining")
    entry_cutoff = p.get("entry_cutoff_seconds")
    effective_cutoff = p.get("effective_cutoff_seconds")
    first_tradable_sec = p.get("first_tradable_seconds_remaining")

    # Use runtime-emitted probe fields if available; else classify offline
    if p.get("admission_probe_state") and p.get("admission_probe_state") != "UNKNOWN":
        probe = {
            "readiness_before_cutoff": bool(p.get("readiness_before_cutoff")),
            "first_executable_before_cutoff": bool(p.get("first_executable_before_cutoff")),
            "admission_probe_state": str(p.get("admission_probe_state")),
            "admission_probe_reason": str(p.get("admission_probe_reason") or ""),
            "admission_block_stage": str(p.get("admission_block_stage") or ""),
            "model_gate_reached": bool(p.get("model_gate_reached")),
            "ev_gate_reached": bool(p.get("ev_gate_reached")),
            "risk_gate_reached": bool(p.get("risk_gate_reached")),
            "candidate_seen_before_cutoff": bool(p.get("candidate_seen_before_cutoff")),
            "candidate_evaluable_before_cutoff": bool(p.get("candidate_evaluable_before_cutoff")),
            "cutoff_policy_state": str(p.get("cutoff_policy_state") or ""),
            "effective_cutoff_seconds": int(p.get("effective_cutoff_seconds") or 0),
        }
    else:
        probe = classify_admission_probe(p)

    return {
        "asset": asset,
        "lifecycle_phase": lifecycle_phase,
        "skip_reason_category": skip_reason_cat,
        "skip_reason_primary": skip_reason_pri,
        "normalized_skip_reason": normalized_skip,
        "seconds_remaining": seconds_remaining,
        "entry_cutoff_seconds": entry_cutoff,
        "first_tradable_seconds_remaining": first_tradable_sec,
        **probe,
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"total_events": 0, "guardrail": "no data"}

    total = len(records)

    # --- probe state distribution ---
    probe_state_counts: Counter[str] = Counter(r["admission_probe_state"] for r in records)
    block_stage_counts: Counter[str] = Counter(r["admission_block_stage"] for r in records)
    cutoff_policy_counts: Counter[str] = Counter(r["cutoff_policy_state"] for r in records)

    # --- key aggregate metrics ---
    exec_before_cutoff = sum(1 for r in records if r["first_executable_before_cutoff"])
    exec_before_cutoff_no_model = sum(
        1 for r in records
        if r["first_executable_before_cutoff"] and not r["model_gate_reached"]
    )
    exec_before_cutoff_no_ev = sum(
        1 for r in records
        if r["first_executable_before_cutoff"] and r["model_gate_reached"] and not r["ev_gate_reached"]
    )
    exec_evaluated = sum(
        1 for r in records
        if r["first_executable_before_cutoff"] and r["ev_gate_reached"]
    )

    token_ready_not_exec = sum(
        1 for r in records if r["admission_probe_state"] == "TOKEN_READY_NOT_EXECUTABLE"
    )
    late_discovery = sum(
        1 for r in records if r["admission_probe_state"] == "LATE_DISCOVERY"
    )

    model_gate_reached_count = sum(1 for r in records if r["model_gate_reached"])
    ev_gate_reached_count = sum(1 for r in records if r["ev_gate_reached"])
    risk_gate_reached_count = sum(1 for r in records if r["risk_gate_reached"])

    readiness_before_cutoff_count = sum(1 for r in records if r["readiness_before_cutoff"])

    # --- first_executable_timing distribution ---
    exec_timings = [
        r["first_tradable_seconds_remaining"]
        for r in records
        if r["first_executable_before_cutoff"]
        and r["first_tradable_seconds_remaining"] is not None
    ]
    exec_timing_dist: dict[str, Any] = {}
    if exec_timings:
        s = sorted(exec_timings)
        n = len(s)
        exec_timing_dist = {
            "count": n,
            "min": s[0],
            "p50": s[n // 2],
            "p90": s[min(int(n * 0.9), n - 1)],
            "max": s[-1],
            "mean": round(sum(s) / n, 1),
        }

    # --- cutoff_passed correlation ---
    cutoff_passed = [r for r in records if "time_unsafe" in r.get("normalized_skip_reason", "")
                     or r.get("skip_reason_primary") == "cutoff_passed"
                     or r.get("skip_reason_category") == "timing"]
    cutoff_probe_states: Counter[str] = Counter(
        r["admission_probe_state"] for r in cutoff_passed
    )
    cutoff_exec_before = sum(1 for r in cutoff_passed if r["first_executable_before_cutoff"])

    # --- asset breakdown ---
    asset_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        asset_records[r["asset"]].append(r)

    asset_breakdown: dict[str, dict[str, Any]] = {}
    for asset, arecs in sorted(asset_records.items()):
        n = len(arecs)
        asset_breakdown[asset] = {
            "total_events": n,
            "exec_before_cutoff": sum(1 for r in arecs if r["first_executable_before_cutoff"]),
            "exec_before_cutoff_pct": _pct(
                sum(1 for r in arecs if r["first_executable_before_cutoff"]), n
            ),
            "exec_before_cutoff_no_model": sum(
                1 for r in arecs
                if r["first_executable_before_cutoff"] and not r["model_gate_reached"]
            ),
            "model_gate_reached_pct": _pct(
                sum(1 for r in arecs if r["model_gate_reached"]), n
            ),
            "probe_state_distribution": dict(
                Counter(r["admission_probe_state"] for r in arecs).most_common()
            ),
        }

    # --- lifecycle phase breakdown ---
    phase_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for r in records:
        phase_counts[r["lifecycle_phase"]][r["admission_probe_state"]] += 1

    # --- gate progression funnel ---
    gate_funnel = {
        "total": total,
        "executable_before_cutoff": exec_before_cutoff,
        "executable_before_cutoff_pct": _pct(exec_before_cutoff, total),
        "model_gate_reached": model_gate_reached_count,
        "model_gate_reached_pct": _pct(model_gate_reached_count, total),
        "ev_gate_reached": ev_gate_reached_count,
        "ev_gate_reached_pct": _pct(ev_gate_reached_count, total),
        "risk_gate_reached": risk_gate_reached_count,
        "risk_gate_reached_pct": _pct(risk_gate_reached_count, total),
        "exec_before_cutoff_no_model": exec_before_cutoff_no_model,
        "exec_before_cutoff_no_ev": exec_before_cutoff_no_ev,
        "exec_evaluated": exec_evaluated,
    }

    return {
        "total_events": total,
        "readiness_before_cutoff_count": readiness_before_cutoff_count,
        "readiness_before_cutoff_pct": _pct(readiness_before_cutoff_count, total),
        "exec_before_cutoff_count": exec_before_cutoff,
        "exec_before_cutoff_pct": _pct(exec_before_cutoff, total),
        "exec_before_cutoff_no_model_count": exec_before_cutoff_no_model,
        "exec_before_cutoff_no_model_pct": _pct(exec_before_cutoff_no_model, total),
        "exec_before_cutoff_no_ev_count": exec_before_cutoff_no_ev,
        "token_ready_not_exec_count": token_ready_not_exec,
        "late_discovery_count": late_discovery,
        "admission_probe_state_distribution": dict(probe_state_counts.most_common()),
        "admission_block_stage_distribution": dict(block_stage_counts.most_common()),
        "cutoff_policy_distribution": dict(cutoff_policy_counts.most_common()),
        "first_executable_timing_seconds_remaining": exec_timing_dist,
        "cutoff_passed_correlation": {
            "total_cutoff_events": len(cutoff_passed),
            "exec_before_cutoff_in_cutoff_events": cutoff_exec_before,
            "exec_before_cutoff_pct": _pct(cutoff_exec_before, len(cutoff_passed)),
            "probe_state_breakdown": dict(cutoff_probe_states.most_common()),
        },
        "gate_funnel": gate_funnel,
        "asset_breakdown": asset_breakdown,
        "lifecycle_phase_probe_distribution": {
            phase: dict(counts.most_common())
            for phase, counts in sorted(phase_counts.items())
        },
    }


# ---------------------------------------------------------------------------
# Console rendering
# ---------------------------------------------------------------------------

def render_console(summary: dict[str, Any], date_str: str, hybrid_flag: bool) -> None:
    total = summary.get("total_events", 0)
    if not total:
        print(f"\nNo decision events found for {date_str}.")
        return

    print(f"\n{'='*68}")
    print(f"  Market Readiness Admission Probe v1  |  {date_str}")
    print(f"{'='*68}")
    print(f"  Total events                    : {total}")
    print(f"  hybrid_phase_v1_enabled visible : {'YES' if hybrid_flag else 'NO (lifecycle milestones not detected)'}")
    print(f"  Readiness before cutoff         : {summary['readiness_before_cutoff_count']}  ({summary['readiness_before_cutoff_pct']:.1f}%)")
    print(f"  Executable before cutoff        : {summary['exec_before_cutoff_count']}  ({summary['exec_before_cutoff_pct']:.1f}%)")
    print()

    print("  -- Gate Funnel --")
    gf = summary["gate_funnel"]
    rows = [
        ("executable_before_cutoff", gf["executable_before_cutoff"], gf["executable_before_cutoff_pct"]),
        ("model_gate_reached",       gf["model_gate_reached"],       gf["model_gate_reached_pct"]),
        ("ev_gate_reached",          gf["ev_gate_reached"],          gf["ev_gate_reached_pct"]),
        ("risk_gate_reached",        gf["risk_gate_reached"],        gf["risk_gate_reached_pct"]),
    ]
    for label, count, pct in rows:
        bar = "#" * int(pct / 5)
        print(f"    {label:<35} {count:>5}  ({pct:>5.1f}%)  {bar}")

    print()
    print("  ** Key finding: exec_before_cutoff but no model gate **")
    no_model = summary["exec_before_cutoff_no_model_count"]
    print(f"    {no_model} events ({_pct(no_model, total):.1f}%) had executable book before cutoff "
          f"but model gate was NOT reached")

    print()
    print("  -- Admission Probe State Distribution --")
    for state, count in summary["admission_probe_state_distribution"].items():
        pct = _pct(count, total)
        print(f"    {state:<40} {count:>5}  ({pct:.1f}%)")

    print()
    print("  -- Admission Block Stage --")
    for stage, count in summary["admission_block_stage_distribution"].items():
        pct = _pct(count, total)
        print(f"    {stage:<25} {count:>5}  ({pct:.1f}%)")

    print()
    et = summary.get("first_executable_timing_seconds_remaining", {})
    if et.get("count"):
        print("  -- first_executable_book Timing (seconds remaining when reached) --")
        print(f"    count={et['count']}  min={et['min']}s  P50={et['p50']}s  "
              f"P90={et['p90']}s  max={et['max']}s  mean={et['mean']}s")
        entry_cutoff_ref = 90
        pct_above_cutoff = _pct(
            sum(1 for v in [et.get("min")] if v and v > entry_cutoff_ref), 1
        )
        print(f"    (entry_cutoff reference: {entry_cutoff_ref}s — "
              f"P50 {'BEFORE' if et['p50'] > entry_cutoff_ref else 'AFTER/AT'} cutoff)")

    print()
    print("  -- Cutoff-Passed Events: Admission Probe Breakdown --")
    cc = summary.get("cutoff_passed_correlation", {})
    print(f"    Total cutoff events: {cc.get('total_cutoff_events', 0)}  "
          f"exec_before_cutoff: {cc.get('exec_before_cutoff_in_cutoff_events', 0)} "
          f"({cc.get('exec_before_cutoff_pct', 0.0):.1f}%)")
    for state, count in cc.get("probe_state_breakdown", {}).items():
        print(f"      {state:<40} {count:>5}")

    print()
    print("  -- BTC vs ETH --")
    for asset, ab in summary.get("asset_breakdown", {}).items():
        print(f"    {asset}: N={ab['total_events']}  "
              f"exec_before_cutoff={ab['exec_before_cutoff']} ({ab['exec_before_cutoff_pct']:.1f}%)  "
              f"model_reached={ab['model_gate_reached_pct']:.1f}%  "
              f"exec_no_model={ab['exec_before_cutoff_no_model']}")

    print()
    print("  -- Lifecycle Phase Probe Distribution --")
    for phase, states in summary.get("lifecycle_phase_probe_distribution", {}).items():
        total_phase = sum(states.values())
        top = list(states.items())[:3]
        print(f"    {phase:<30} N={total_phase}  {top}")
    print()


def _pct(n: int, d: int) -> float:  # module-level helper for render_console
    return round(n / d * 100, 1) if d else 0.0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Market Readiness Admission Probe v1")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--asset", default=None, help="BTC or ETH")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args(argv)

    date_str = args.date
    quant_data_dir = Path(args.quant_data_dir)
    report_dir = Path(args.report_dir)

    print(f"Loading decision_log for {date_str} ...")
    events = load_decision_events(date_str, quant_data_dir, args.run_id, args.asset)
    print(f"  decision events: {len(events)}")

    hybrid_flag = _check_hybrid_phase_enabled(date_str, quant_data_dir, args.run_id)
    print(f"  hybrid_phase_v1_enabled (lifecycle milestones detected): {hybrid_flag}")

    if not events:
        print("No events found. Nothing to probe.")
        return

    records = [extract_record(e) for e in events]
    summary = aggregate(records)
    summary["date"] = date_str
    summary["asset_filter"] = args.asset or "all"
    summary["run_id_filter"] = args.run_id or "all"
    summary["hybrid_phase_v1_enabled_detected"] = hybrid_flag
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    summary["source"] = "market_readiness_admission_probe_v1"
    summary["guardrail"] = (
        "Offline observability only. Does not change runtime, strategy, "
        "risk, execution, or paper/live separation."
    )

    render_console(summary, date_str, hybrid_flag)

    if args.write_report:
        report_dir.mkdir(parents=True, exist_ok=True)
        out_path = report_dir / f"market_readiness_admission_probe_{date_str}.json"
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, default=str)
        print(f"  Report written to: {out_path}")


if __name__ == "__main__":
    main()
