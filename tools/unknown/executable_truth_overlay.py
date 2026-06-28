"""
Executable Truth Overlay — Stage B Phase 1 MVP
===============================================

Offline read-only tool. Classifies closed paper trades from trade_journal as
SIGNAL_ONLY / DUST_ZONE / EXECUTABLE_MIN_REJECT using assumed MOS thresholds.

Produces no executable PnL claims. Executable PnL is permanently BLOCKED_N_A
until fill/cancel/partial-fill truth and authoritative exchange MOS exist.

Usage:
    python tools/executable_truth_overlay.py --date 2026-06-01
    python tools/executable_truth_overlay.py --date-from 2026-05-18 --date-to 2026-06-01
    python tools/executable_truth_overlay.py --date 2026-06-01 --write-report

Safety:
    - Never imports runtime modules (polymarket.*, utils.risk_manager, etc.)
    - Never writes to runtime/quant_data/
    - Never sets executable_pnl to a non-null value
    - Never claims Growth Mode readiness
    - Always outputs hermes_ingest_status = BLOCKER_EVIDENCE_ONLY

Runtime behavior changed: No
Live behavior changed:    No
JSONL schema changed:     No
Strategy/risk changed:    No
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "executable_truth_overlay_v1"
DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")
DEFAULT_MOS_ASSUMPTIONS = (1, 3, 5)
MAX_REAL_PNL_ABS = 0.50           # trades with |pnl| > this are test artifacts
EXECUTABLE_PNL_STATUS = "BLOCKED_N_A"
MOS_SOURCE = "research_assumption"
HERMES_INGEST_STATUS = "BLOCKER_EVIDENCE_ONLY"
HERMES_VERDICT = {
    "signal_mode": "ACTIVE",
    "executable_pnl": "BLOCKED",
    "growth_mode": "BLOCKED",
    "truth_level": "SIGNAL_MODE_PAPER_SIMULATED",
    "hermes_ingest_status": HERMES_INGEST_STATUS,
}

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Safety guards — checked at startup
# ---------------------------------------------------------------------------

_FORBIDDEN_WRITES = (
    "runtime/quant_data",
    "polymarket",
    "utils",
    "config",
    "tests",
)


def _safety_check_output_path(path: Path, allowed_dir: Path | None = None) -> None:
    """
    Abort if path is outside the allowed report directory.
    allowed_dir defaults to DEFAULT_REPORT_DIR but can be overridden for testing.
    """
    resolved = path.resolve()
    allowed = (allowed_dir or DEFAULT_REPORT_DIR).resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise RuntimeError(
            f"[SAFETY] Attempted write to forbidden path: {path}\n"
            f"All writes must be inside {allowed}"
        ) from exc
    for forbidden in _FORBIDDEN_WRITES:
        if forbidden in str(resolved):
            raise RuntimeError(
                f"[SAFETY] Forbidden path component '{forbidden}' in output: {resolved}"
            )


def _safety_check_no_live_mode() -> None:
    """Log a critical warning if running outside paper context."""
    # We cannot import config here (no runtime imports), so we check env vars
    import os
    paper_env = os.environ.get("PAPER_TRADING", "").lower()
    mode_env = os.environ.get("TRADING_MODE", "").lower()
    if paper_env in ("false", "0", "no") or mode_env == "live":
        LOGGER.critical(
            "[SAFETY] executable_truth_overlay detected non-paper environment. "
            "This tool is for offline research only. Proceeding as read-only; "
            "no trades will be affected."
        )
    # Do NOT abort — the tool is always safe (read-only). Just warn.


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TradeRow:
    """Classified record for one closed paper trade."""
    run_id: str
    timestamp_utc: str
    paper_trade_replay_key: str | None
    asset: str
    side: str
    entry_price: float
    size: float                          # shares
    notional: float                      # entry_price × size
    signal_pnl: float                    # = pnl_usdc
    trade_result: str                    # TP / SL / EXPIRY / UNKNOWN
    exit_reason: str
    session_hour_utc: int | None
    price_bucket: str
    # Classification
    dust_zone: bool
    mos_fail: dict[int, bool]            # {1: True, 3: True, 5: True}
    executable_minimum_met: bool
    # Constants
    executable_pnl: None = None
    executable_pnl_status: str = EXECUTABLE_PNL_STATUS
    mos_source: str = MOS_SOURCE
    hermes_ingest_status: str = HERMES_INGEST_STATUS
    row_status: str = "SIGNAL_ONLY"


@dataclass
class Aggregate:
    """Aggregate counts for one report run."""
    rows_total: int = 0
    rows_skipped_missing_fields: int = 0
    rows_skipped_test_artifact: int = 0
    signal_pnl_sum: float = 0.0
    rows_dust_zone: int = 0
    rows_above_mos: dict[int, int] = field(default_factory=dict)
    rows_executable_candidate: int = 0
    rows_executable_pnl_approved: int = 0


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

def _as_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _derive_session_hour(timestamp_utc: str) -> int | None:
    if not timestamp_utc:
        return None
    try:
        dt = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
        return dt.hour
    except (ValueError, AttributeError):
        return None


def _derive_price_bucket(entry_price: float) -> str:
    """Map entry_price to a 0.10-wide bucket label."""
    buckets = [
        (0.00, 0.10, "0.00-0.10"),
        (0.10, 0.20, "0.10-0.20"),
        (0.20, 0.30, "0.20-0.30"),
        (0.30, 0.40, "0.30-0.40"),
        (0.40, 0.50, "0.40-0.50"),
        (0.50, 0.60, "0.50-0.60"),
        (0.60, 0.70, "0.60-0.70"),
        (0.70, 0.80, "0.70-0.80"),
        (0.80, 0.90, "0.80-0.90"),
        (0.90, 1.00, "0.90-1.00"),
    ]
    for lo, hi, label in buckets:
        if lo <= entry_price < hi:
            return label
    return "OTHER"


def _resolve_trade_result(trade_result: Any, exit_reason: Any, pnl: float) -> str:
    """Return a normalised trade result string."""
    tr = str(trade_result or "").upper().strip()
    if tr in ("TP", "WIN", "TAKE_PROFIT"):
        return "TP"
    if tr in ("SL", "LOSS", "STOP_LOSS"):
        return "SL"
    # Fallback via exit_reason
    er = str(exit_reason or "").lower()
    if "take_profit" in er or "tp" in er:
        return "TP"
    if "stop_loss" in er or "sl" in er:
        return "SL"
    if "expir" in er or "forced" in er or "time" in er:
        return "EXPIRY"
    # Final fallback: PnL sign
    if pnl > 0:
        return "TP"
    if pnl < 0:
        return "SL"
    return "UNKNOWN"


def extract_fields(
    event: dict[str, Any],
    mos_assumptions: tuple[int, ...],
) -> TradeRow | None:
    """
    Extract and classify one trade_close event.
    Returns None if the row should be skipped.
    """
    if event.get("event_type") != "trade_close":
        return None

    run_id = str(event.get("run_id") or "UNKNOWN")
    timestamp_utc = str(event.get("timestamp_utc") or "")
    payload = event.get("payload") or {}

    # --- Required fields: skip if missing ---
    pnl_raw = payload.get("pnl") if payload.get("pnl") is not None else payload.get("pnl_usdc")
    size_raw = payload.get("size") if payload.get("size") is not None else payload.get("filled_size")
    entry_price_raw = payload.get("entry_price") if payload.get("entry_price") is not None else payload.get("market_price")

    pnl = _as_float(pnl_raw)
    size = _as_float(size_raw)
    entry_price = _as_float(entry_price_raw)

    if pnl is None or size is None or entry_price is None:
        LOGGER.debug("Skipping row (missing required fields): pnl=%s size=%s entry=%s run=%s",
                     pnl_raw, size_raw, entry_price_raw, run_id)
        return None

    # --- Test artifact guards ---
    reason = str(payload.get("reason") or "").lower().strip()
    if reason == "test":
        return None
    if abs(pnl) > MAX_REAL_PNL_ABS:
        LOGGER.debug("Skipping test artifact: |pnl|=%.4f > %.2f run=%s", abs(pnl), MAX_REAL_PNL_ABS, run_id)
        return None

    # --- Verification-session artifact guard (epoch_start_ts == 0) ---
    # Real production paper trades are always anchored to a valid market epoch
    # (non-zero UNIX timestamp set from ptb_info.epoch_start_ts at trade open).
    # Verification sessions use epoch=0 as a sentinel for synthetic orders.
    # Belt-and-suspenders: also flag rows with no paper_trade_replay_key when epoch=0.
    epoch_ts_raw = payload.get("epoch_start_ts")
    _epoch_is_zero = False
    if epoch_ts_raw is not None:
        try:
            _epoch_is_zero = int(float(str(epoch_ts_raw))) == 0
        except (ValueError, TypeError):
            pass  # fail-open: unparseable epoch does not auto-skip
    _replay_key_absent = not payload.get("paper_trade_replay_key")
    if _epoch_is_zero and _replay_key_absent:
        LOGGER.debug(
            "Skipping verification artifact: epoch_start_ts=0 and no replay_key run=%s", run_id
        )
        return None

    # --- Zero-value guard ---
    if entry_price == 0.0 or size == 0.0:
        LOGGER.debug("Skipping zero-value row: entry_price=%s size=%s run=%s", entry_price, size, run_id)
        return None

    # --- Optional fields with fallbacks ---
    asset = str(payload.get("asset") or "UNKNOWN").upper()
    side  = str(payload.get("side")  or "UNKNOWN").upper()
    paper_trade_replay_key = payload.get("paper_trade_replay_key") or None
    exit_reason  = str(payload.get("exit_reason") or payload.get("reason") or "")
    trade_result = payload.get("trade_result")

    # --- Derived fields ---
    notional       = round(entry_price * size, 8)
    session_hour   = _derive_session_hour(timestamp_utc)
    price_bucket   = _derive_price_bucket(entry_price)
    resolved_result = _resolve_trade_result(trade_result, exit_reason, pnl)

    # --- Classification ---
    dust_zone = size < 1.0
    mos_fail  = {m: (size < m) for m in mos_assumptions}
    executable_minimum_met = not any(mos_fail.values())

    return TradeRow(
        run_id=run_id,
        timestamp_utc=timestamp_utc,
        paper_trade_replay_key=paper_trade_replay_key,
        asset=asset,
        side=side,
        entry_price=entry_price,
        size=size,
        notional=notional,
        signal_pnl=pnl,
        trade_result=resolved_result,
        exit_reason=exit_reason,
        session_hour_utc=session_hour,
        price_bucket=price_bucket,
        dust_zone=dust_zone,
        mos_fail=mos_fail,
        executable_minimum_met=executable_minimum_met,
    )


# ---------------------------------------------------------------------------
# JSONL loading
# ---------------------------------------------------------------------------

def load_trade_closes(
    path: Path,
    run_id_filter: str | None,
    mos_assumptions: tuple[int, ...],
) -> tuple[list[TradeRow], int, int]:
    """
    Load and classify all trade_close rows from a single JSONL file.
    Returns (rows, n_skipped_missing, n_skipped_artifact).
    """
    rows: list[TradeRow] = []
    n_missing = 0
    n_artifact = 0
    n_malformed = 0

    if not path.exists():
        LOGGER.warning("trade_journal not found: %s", path)
        return rows, 0, 0

    for line_num, raw_line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            n_malformed += 1
            LOGGER.debug("Malformed JSON on line %d of %s — skipped", line_num, path.name)
            continue

        if event.get("event_type") != "trade_close":
            continue

        # Run ID filter
        if run_id_filter and event.get("run_id", "") != run_id_filter:
            continue

        payload = event.get("payload") or {}
        pnl_raw = payload.get("pnl") if payload.get("pnl") is not None else payload.get("pnl_usdc")
        size_raw = payload.get("size") if payload.get("size") is not None else payload.get("filled_size")
        entry_raw = payload.get("entry_price") if payload.get("entry_price") is not None else payload.get("market_price")

        # Pre-check for test artifact (to count correctly)
        pnl_val = _as_float(pnl_raw)
        reason = str(payload.get("reason") or "").lower().strip()
        if reason == "test" or (pnl_val is not None and abs(pnl_val) > MAX_REAL_PNL_ABS):
            n_artifact += 1
            continue

        # Pre-check for verification-session artifact (epoch_start_ts == 0)
        epoch_ts_raw = payload.get("epoch_start_ts")
        _epoch_zero = False
        if epoch_ts_raw is not None:
            try:
                _epoch_zero = int(float(str(epoch_ts_raw))) == 0
            except (ValueError, TypeError):
                pass
        _no_replay = not payload.get("paper_trade_replay_key")
        if _epoch_zero and _no_replay:
            n_artifact += 1
            continue

        row = extract_fields(event, mos_assumptions)
        if row is None:
            # Missing required fields
            if _as_float(pnl_raw) is None or _as_float(size_raw) is None or _as_float(entry_raw) is None:
                n_missing += 1
            # (zero-value rows counted as missing for simplicity)
            continue

        rows.append(row)

    if n_malformed > 0:
        LOGGER.warning("%d malformed JSON lines in %s — skipped", n_malformed, path.name)

    return rows, n_missing, n_artifact


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def build_aggregate(
    rows: list[TradeRow],
    n_skipped_missing: int,
    n_skipped_artifact: int,
    mos_assumptions: tuple[int, ...],
) -> dict[str, Any]:
    """Build the aggregate report dict from classified rows."""
    signal_pnl_sum = sum(r.signal_pnl for r in rows)
    rows_dust = sum(1 for r in rows if r.dust_zone)
    rows_above_mos = {m: sum(1 for r in rows if not r.mos_fail[m]) for m in mos_assumptions}
    rows_exec_cand = sum(1 for r in rows if r.executable_minimum_met)

    mos_fail_counts = {m: sum(1 for r in rows if r.mos_fail[m]) for m in mos_assumptions}
    mos_clear_rates = {
        m: round(rows_above_mos[m] / len(rows), 6) if rows else 0.0
        for m in mos_assumptions
    }

    return {
        "rows_total": len(rows),
        "rows_skipped_missing_fields": n_skipped_missing,
        "rows_skipped_test_artifact": n_skipped_artifact,
        "signal_evidence": {
            "signal_pnl_sum": round(signal_pnl_sum, 8),
            "signal_pnl_mean": round(signal_pnl_sum / len(rows), 8) if rows else 0.0,
        },
        "dust_classification": {
            "rows_dust_zone": rows_dust,
            "dust_zone_rate": round(rows_dust / len(rows), 6) if rows else 0.0,
            **{f"rows_above_mos{m}": rows_above_mos[m] for m in mos_assumptions},
            **{f"mos{m}_clear_rate": mos_clear_rates[m] for m in mos_assumptions},
            **{f"rows_mos{m}_fail": mos_fail_counts[m] for m in mos_assumptions},
        },
        "executable_status": {
            "rows_executable_candidate": rows_exec_cand,
            "rows_executable_pnl_approved": 0,
            "executable_pnl_status": EXECUTABLE_PNL_STATUS,
        },
        "blocker_summary": {
            "minimum_size_fail": mos_fail_counts.get(min(mos_assumptions), len(rows)),
            "mos_assumption_not_authoritative": len(rows),
            "fill_truth_missing": len(rows),
            "cancel_truth_missing": len(rows),
            "partial_fill_truth_missing": len(rows),
        },
        "hermes_verdict": dict(HERMES_VERDICT),
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_summary(
    agg: dict[str, Any],
    date_range: dict[str, str],
    mos_assumptions: tuple[int, ...],
) -> None:
    """Print a human-readable summary to stdout."""
    n = agg["rows_total"]
    dust = agg["dust_classification"]["rows_dust_zone"]
    spnl = agg["signal_evidence"]["signal_pnl_sum"]
    verdict = agg["hermes_verdict"]

    lines = [
        "",
        f"{'='*60}",
        f" Executable Truth Overlay — {date_range['from']} to {date_range['to']}",
        f"{'='*60}",
        f" Schema:       {SCHEMA_VERSION}",
        f" MOS source:   {MOS_SOURCE}",
        "",
        f" SIGNAL EVIDENCE",
        f"   rows_total:        {n}",
        f"   rows_skipped:      {agg['rows_skipped_missing_fields']} (missing fields) "
        f"+ {agg['rows_skipped_test_artifact']} (test artifacts)",
        f"   signal_pnl_sum:    ${spnl:.6f}",
        "",
        f" DUST CLASSIFICATION",
        f"   rows_dust_zone:    {dust}  ({100*dust/n:.1f}%)" if n else "   rows_dust_zone:    0  (N/A)",
    ]
    for m in mos_assumptions:
        fail = agg["dust_classification"][f"rows_mos{m}_fail"]
        above = agg["dust_classification"][f"rows_above_mos{m}"]
        rate  = agg["dust_classification"][f"mos{m}_clear_rate"]
        lines.append(f"   MOS={m}: fail={fail}  clear={above}  clear_rate={rate:.1%}")
    lines += [
        "",
        f" EXECUTABLE STATUS",
        f"   executable_candidate:    {agg['executable_status']['rows_executable_candidate']}",
        f"   executable_pnl_approved: {agg['executable_status']['rows_executable_pnl_approved']}",
        f"   executable_pnl_status:   {agg['executable_status']['executable_pnl_status']}",
        "",
        f" HERMES VERDICT",
        f"   signal_mode:    {verdict['signal_mode']}",
        f"   executable_pnl: {verdict['executable_pnl']}",
        f"   growth_mode:    {verdict['growth_mode']}",
        f"   truth_level:    {verdict['truth_level']}",
        f"{'='*60}",
        "",
    ]
    print("\n".join(lines))


def build_report(
    agg: dict[str, Any],
    date_range: dict[str, str],
    mos_assumptions: tuple[int, ...],
    run_id_filter: str | None,
) -> dict[str, Any]:
    """Build the full JSON report dict."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "date_range": date_range,
        "run_id_filter": run_id_filter,
        "mos_assumptions": list(mos_assumptions),
        "mos_source": MOS_SOURCE,
        **agg,
    }


def write_report(
    report: dict[str, Any],
    date_range: dict[str, str],
    run_id_filter: str | None,
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> Path:
    """Write the JSON report to runtime/reports/. Returns the path written."""
    date_tag = date_range["from"].replace("-", "")
    if date_range["from"] != date_range["to"]:
        date_tag += f"_to_{date_range['to'].replace('-', '')}"
    run_tag = (run_id_filter[:20] if run_id_filter else "all")
    filename = f"executable_truth_overlay_{date_tag}_{run_tag}.json"
    path = report_dir / filename
    _safety_check_output_path(path, allowed_dir=report_dir)

    report_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    LOGGER.info("Report written: %s", path)
    return path


# ---------------------------------------------------------------------------
# Date range helpers
# ---------------------------------------------------------------------------

def _iter_dates(date_from: str, date_to: str) -> list[str]:
    """Return list of YYYY-MM-DD strings from date_from to date_to inclusive."""
    from datetime import date as date_type, timedelta
    try:
        start = date_type.fromisoformat(date_from)
        end   = date_type.fromisoformat(date_to)
    except ValueError as exc:
        raise ValueError(f"Invalid date format (expected YYYY-MM-DD): {exc}") from exc
    if start > end:
        raise ValueError(f"date_from ({date_from}) must be <= date_to ({date_to})")
    dates = []
    current = start
    while current <= end:
        dates.append(str(current))
        current += timedelta(days=1)
    return dates


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def run(
    date_from: str,
    date_to: str,
    run_id_filter: str | None = None,
    mos_assumptions: tuple[int, ...] = DEFAULT_MOS_ASSUMPTIONS,
    write_report_flag: bool = False,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    """
    Core execution function. Returns the final report dict.
    Can be called programmatically (e.g., from tests).
    """
    _safety_check_no_live_mode()

    dates = _iter_dates(date_from, date_to)
    all_rows: list[TradeRow] = []
    total_missing = 0
    total_artifact = 0

    for date in dates:
        path = quant_data_dir / "trade_journal" / f"{date}.jsonl"
        rows, n_miss, n_art = load_trade_closes(path, run_id_filter, mos_assumptions)
        all_rows.extend(rows)
        total_missing += n_miss
        total_artifact += n_art
        LOGGER.debug(
            "Date %s: %d rows loaded, %d skipped-missing, %d skipped-artifact",
            date, len(rows), n_miss, n_art
        )

    date_range = {"from": date_from, "to": date_to}
    agg    = build_aggregate(all_rows, total_missing, total_artifact, mos_assumptions)
    report = build_report(agg, date_range, mos_assumptions, run_id_filter)

    print_summary(agg, date_range, mos_assumptions)

    if write_report_flag:
        written = write_report(report, date_range, run_id_filter, report_dir)
        print(f"[report] Written: {written}\n")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="executable_truth_overlay",
        description=(
            "Stage B offline executable truth overlay. "
            "Classifies paper trades as SIGNAL_ONLY / DUST_ZONE. "
            "Never approves executable PnL. Read-only."
        ),
    )
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument("--date", metavar="YYYY-MM-DD",
                            help="Single date to analyse")
    date_group.add_argument("--date-from", metavar="YYYY-MM-DD",
                            help="Start of date range (use with --date-to)")
    parser.add_argument("--date-to", metavar="YYYY-MM-DD",
                        help="End of date range (default: same as --date-from)")
    parser.add_argument("--run-id", metavar="RUN_ID", default=None,
                        help="Filter to a specific run_id")
    parser.add_argument("--mos", nargs="+", type=int, default=list(DEFAULT_MOS_ASSUMPTIONS),
                        metavar="N", help="MOS thresholds in shares (default: 1 3 5)")
    parser.add_argument("--write-report", action="store_true",
                        help="Write JSON report to runtime/reports/")
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR),
                        metavar="DIR", help="Path to runtime/quant_data/")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR),
                        metavar="DIR", help="Path to runtime/reports/")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable DEBUG logging")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    if args.date:
        date_from = args.date
        date_to   = args.date
    else:
        date_from = args.date_from
        date_to   = args.date_to or args.date_from

    mos_assumptions = tuple(sorted(set(args.mos)))
    if not mos_assumptions:
        LOGGER.error("--mos must provide at least one value")
        return 1

    try:
        run(
            date_from=date_from,
            date_to=date_to,
            run_id_filter=args.run_id,
            mos_assumptions=mos_assumptions,
            write_report_flag=args.write_report,
            quant_data_dir=Path(args.quant_data_dir),
            report_dir=Path(args.report_dir),
        )
    except (ValueError, RuntimeError) as exc:
        LOGGER.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
