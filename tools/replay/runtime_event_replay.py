#!/usr/bin/env python3
"""Runtime Event Replay — reads event stream JSONL files from runtime/event_stream/.

Usage:
  python tools/runtime_event_replay.py [OPTIONS]

Options:
  --date YYYY-MM-DD      Filter to files for this UTC date (default: today)
  --session-id ID        Filter by runtime_session_id
  --event-type TYPE      Filter by event_type (exact match)
  --seq N                Skip events with session_sequence < N
  --limit N              Stop after printing N matching events
  --tail N               Print only the last N matching events
  --follow / -f          Tail-follow: poll for new events after EOF (100 ms interval)
  --summary              Print event count by type instead of raw events
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


EVENT_STREAM_DIR = Path("runtime/event_stream")


# ──────────────────────────────────────────────────────────────────────────────
# File discovery
# ──────────────────────────────────────────────────────────────────────────────

def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _find_files(date: str, stream_dir: Path) -> list[Path]:
    """Return sorted JSONL files matching runtime_events_<date>_*.jsonl."""
    pattern = f"runtime_events_{date}_*.jsonl"
    return sorted(stream_dir.glob(pattern))


# ──────────────────────────────────────────────────────────────────────────────
# Parsing and filtering
# ──────────────────────────────────────────────────────────────────────────────

def _parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _matches(event: dict, session_id: str | None, event_type: str | None, seq: int | None) -> bool:
    if session_id and event.get("runtime_session_id") != session_id:
        return False
    if event_type and event.get("event_type") != event_type:
        return False
    if seq is not None and event.get("session_sequence", 0) < seq:
        return False
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Core reader
# ──────────────────────────────────────────────────────────────────────────────

def _read_events(
    files: list[Path],
    session_id: str | None,
    event_type: str | None,
    seq: int | None,
    limit: int | None,
    follow: bool,
) -> list[dict]:
    """Read and filter events from a list of JSONL files."""
    results: list[dict] = []
    count = 0

    for path in files:
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    event = _parse_line(line)
                    if event is None:
                        continue
                    if not _matches(event, session_id, event_type, seq):
                        continue
                    results.append(event)
                    count += 1
                    if limit is not None and count >= limit:
                        return results
        except OSError as exc:
            print(f"[replay] Warning: could not read {path}: {exc}", file=sys.stderr)

    # Follow mode: keep polling the last file for new lines
    if follow and files:
        last_file = files[-1]
        _follow_file(last_file, results, session_id, event_type, seq, limit)

    return results


def _follow_file(
    path: Path,
    results: list[dict],
    session_id: str | None,
    event_type: str | None,
    seq: int | None,
    limit: int | None,
) -> None:
    """Tail-follow a single file, printing new lines as they appear."""
    try:
        fh = open(path, "r", encoding="utf-8")
        fh.seek(0, 2)  # Seek to end
    except OSError as exc:
        print(f"[replay] Cannot open {path} for follow: {exc}", file=sys.stderr)
        return

    print(f"[replay] Following {path} — press Ctrl-C to stop", file=sys.stderr)
    try:
        while True:
            line = fh.readline()
            if not line:
                time.sleep(0.1)
                # Re-open if file was rotated
                try:
                    new_size = path.stat().st_size
                    current_pos = fh.tell()
                    if new_size < current_pos:
                        fh.close()
                        fh = open(path, "r", encoding="utf-8")
                except OSError:
                    pass
                continue
            event = _parse_line(line)
            if event is None:
                continue
            if not _matches(event, session_id, event_type, seq):
                continue
            _print_event(event)
            results.append(event)
            if limit is not None and len(results) >= limit:
                break
    except KeyboardInterrupt:
        pass
    finally:
        fh.close()


# ──────────────────────────────────────────────────────────────────────────────
# Output formatters
# ──────────────────────────────────────────────────────────────────────────────

def _print_event(event: dict) -> None:
    print(json.dumps(event, sort_keys=True, default=str))


def _print_summary(events: list[dict]) -> None:
    counts: dict[str, int] = defaultdict(int)
    for e in events:
        counts[e.get("event_type", "unknown")] += 1
    print(f"{'event_type':<50} {'count':>8}")
    print("-" * 60)
    for etype, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"{etype:<50} {cnt:>8}")
    print("-" * 60)
    print(f"{'TOTAL':<50} {sum(counts.values()):>8}")


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay runtime event stream JSONL files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--date",
        default=None,
        help="UTC date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--session-id",
        dest="session_id",
        default=None,
        help="Filter by runtime_session_id",
    )
    parser.add_argument(
        "--event-type",
        dest="event_type",
        default=None,
        help="Filter by event_type (exact match)",
    )
    parser.add_argument(
        "--seq",
        type=int,
        default=None,
        help="Skip events with session_sequence < N",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after N matching events",
    )
    parser.add_argument(
        "--tail",
        type=int,
        default=None,
        help="Show last N matching events",
    )
    parser.add_argument(
        "--follow",
        "-f",
        action="store_true",
        help="Poll for new events after EOF (tail -f style)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print event count summary by type",
    )
    parser.add_argument(
        "--dir",
        dest="stream_dir",
        default=str(EVENT_STREAM_DIR),
        help=f"Event stream directory (default: {EVENT_STREAM_DIR})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    date = args.date or _today_utc()
    stream_dir = Path(args.stream_dir)

    if not stream_dir.exists():
        print(f"[replay] Stream directory not found: {stream_dir}", file=sys.stderr)
        sys.exit(1)

    files = _find_files(date, stream_dir)
    if not files:
        print(f"[replay] No event files found for date={date} in {stream_dir}", file=sys.stderr)
        if not args.follow:
            sys.exit(0)
        # In follow mode, wait for a file to appear
        print(f"[replay] Waiting for event files to appear...", file=sys.stderr)
        while not files:
            time.sleep(1.0)
            files = _find_files(date, stream_dir)

    events = _read_events(
        files,
        session_id=args.session_id,
        event_type=args.event_type,
        seq=args.seq,
        limit=args.limit if not args.tail else None,
        follow=args.follow,
    )

    # Apply --tail after collection (unless follow mode, where events were streamed live)
    if args.tail and not args.follow:
        events = events[-args.tail :]

    if args.summary:
        _print_summary(events)
    elif not args.follow:
        for event in events:
            _print_event(event)


if __name__ == "__main__":
    main()
