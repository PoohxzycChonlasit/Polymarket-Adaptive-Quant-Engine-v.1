"""Tests for Ghost Position Sentinel: run_sentinel_checks(), ghost_positions(), and metadata injection."""
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from utils.position_tracker import PositionTracker


def _settings(paper=True, max_age=3600, quarantine=True):
    return SimpleNamespace(
        paper_trading=paper,
        account_balance=100.0,
        max_open_positions=10,
        max_total_exposure=1.0,
        max_daily_drawdown=0.10,
        ghost_position_max_age=max_age,
        ghost_position_quarantine_enabled=quarantine,
    )


def _tracker(paper=True, max_age=3600, quarantine=True):
    return PositionTracker(settings=_settings(paper, max_age, quarantine))


def _active_owner(run_id="run-A", started_utc=None):
    started = started_utc or (datetime.now(tz=UTC) - timedelta(minutes=10))
    return {
        "run_id": run_id,
        "status": "active",
        "started_utc": started.isoformat().replace("+00:00", "Z"),
    }


def _open_no_paper(tracker, symbol="pm-5m-btc", metadata=None):
    """Open a position without paper-mode auto-injection (paper=False tracker)."""
    return tracker.open_position(
        symbol=symbol,
        source="polymarket",
        side="BUY",
        entry_price=0.50,
        size=5.0,
        stop_loss=0.40,
        take_profit=0.60,
        order_id="test-order",
        metadata=metadata or {},
    )


def _clean_meta(run_id="run-A"):
    """Metadata that passes all 8 sentinel criteria (except PID_DEAD, which is skipped when owner_pid absent)."""
    return {"runtime_session_id": run_id, "lifecycle_phase": "ENTRY"}


class SentinelDetectionTests(unittest.TestCase):
    """Tests for run_sentinel_checks() detection criteria and quarantine behavior."""

    def test_stale_position_is_detected(self):
        """Criterion 7: position older than ghost_position_max_age is quarantined."""
        tracker = _tracker(paper=False, max_age=10)
        pos = _open_no_paper(tracker, metadata=_clean_meta("run-A"))
        # Back-date entry_time to 20 seconds ago (> max_age=10)
        pos.entry_time = (datetime.now(tz=UTC) - timedelta(seconds=20)).isoformat().replace("+00:00", "Z")

        owner = _active_owner("run-A", started_utc=datetime.now(tz=UTC) - timedelta(seconds=30))
        tracker.run_sentinel_checks("run-A", active_owner=owner)

        self.assertEqual(pos.status, "ghost")
        self.assertEqual(pos.metadata.get("ghost_reason"), "STALE_POSITION")
        self.assertTrue(pos.metadata.get("quarantined"))

    def test_fresh_position_is_not_detected(self):
        """Clean position passing all 8 criteria is never quarantined."""
        tracker = _tracker(paper=False, max_age=3600)
        pos = _open_no_paper(tracker, metadata=_clean_meta("run-A"))
        events = []
        tracker.run_sentinel_checks(
            "run-A",
            active_owner=_active_owner("run-A"),
            telemetry_emit=lambda m, p: events.append((m, p)),
        )

        self.assertEqual(pos.status, "open")
        self.assertFalse(pos.metadata.get("quarantined", False))
        ghost_events = [e for e in events if e[0] == "log_ghost_position_detected"]
        self.assertEqual(len(ghost_events), 0)

    def test_max_age_boundary_not_stale(self):
        """Criterion 7 uses strict >: age == max_age is NOT stale."""
        tracker = _tracker(paper=False, max_age=10)
        pos = _open_no_paper(tracker, metadata=_clean_meta("run-A"))
        # Back-date to exactly max_age seconds
        pos.entry_time = (datetime.now(tz=UTC) - timedelta(seconds=10)).isoformat().replace("+00:00", "Z")

        owner = _active_owner("run-A", started_utc=datetime.now(tz=UTC) - timedelta(seconds=30))
        tracker.run_sentinel_checks("run-A", active_owner=owner)

        self.assertEqual(pos.status, "open")
        self.assertFalse(pos.metadata.get("quarantined", False))

    def test_quarantine_enabled_sets_ghost_status_and_metadata(self):
        """quarantine_enabled=True: OWNER_MISSING position gets status='ghost' and metadata marked."""
        tracker = _tracker(paper=False, quarantine=True)
        pos = _open_no_paper(tracker, metadata={})  # no runtime_session_id → OWNER_MISSING

        tracker.run_sentinel_checks("run-A")

        self.assertEqual(pos.status, "ghost")
        self.assertTrue(pos.metadata.get("quarantined"))
        self.assertEqual(pos.metadata.get("ghost_reason"), "OWNER_MISSING")
        self.assertIn("ghost_detected_at", pos.metadata)

    def test_quarantine_disabled_does_not_mutate_position(self):
        """quarantine_enabled=False: ghost detected but status and metadata unchanged."""
        tracker = _tracker(paper=False, quarantine=False)
        pos = _open_no_paper(tracker, metadata={})  # no runtime_session_id → OWNER_MISSING

        tracker.run_sentinel_checks("run-A")

        self.assertEqual(pos.status, "open")
        self.assertNotIn("quarantined", pos.metadata)
        self.assertNotIn("ghost_reason", pos.metadata)

    def test_missing_timestamp_does_not_cause_false_positive(self):
        """Corrupted entry_time: fromisoformat() fails, age defaults to 0. STALE_POSITION never fires."""
        tracker = _tracker(paper=False, max_age=10)
        pos = _open_no_paper(tracker, metadata=_clean_meta("run-A"))
        # Corrupt entry_time — parse will fail, age_seconds defaults to 0.0
        pos.entry_time = "INVALID_TIMESTAMP"

        owner = _active_owner("run-A")
        tracker.run_sentinel_checks("run-A", active_owner=owner)

        self.assertEqual(pos.status, "open")
        self.assertFalse(pos.metadata.get("quarantined", False))

    def test_multiple_ghost_positions_each_quarantined_independently(self):
        """Two OWNER_MISSING positions are both quarantined; clean position is untouched."""
        tracker = _tracker(paper=False)
        ghost1 = _open_no_paper(tracker, symbol="pm-5m-btc", metadata={})
        ghost2 = _open_no_paper(tracker, symbol="pm-5m-eth", metadata={})
        clean = _open_no_paper(tracker, symbol="pm-5m-sol", metadata=_clean_meta("run-A"))

        owner = _active_owner("run-A")
        tracker.run_sentinel_checks("run-A", active_owner=owner)

        self.assertEqual(ghost1.status, "ghost")
        self.assertEqual(ghost2.status, "ghost")
        self.assertEqual(clean.status, "open")
        self.assertFalse(clean.metadata.get("quarantined", False))

    def test_telemetry_payload_contains_required_fields(self):
        """Ghost detection emits log_ghost_position_detected with all required payload keys."""
        tracker = _tracker(paper=False)
        pos = _open_no_paper(tracker, metadata={})  # OWNER_MISSING
        events = []
        tracker.run_sentinel_checks(
            "run-A",
            telemetry_emit=lambda method, payload: events.append((method, payload)),
        )

        ghost_events = [p for m, p in events if m == "log_ghost_position_detected"]
        self.assertEqual(len(ghost_events), 1)
        payload = ghost_events[0]
        for key in ("position_id", "ghost_reason", "quarantined", "age_seconds", "telemetry_scope", "action_taken"):
            self.assertIn(key, payload, msg=f"Missing key: {key}")
        self.assertEqual(payload["telemetry_scope"], "sentinel")
        self.assertEqual(payload["ghost_reason"], "OWNER_MISSING")
        self.assertEqual(payload["action_taken"], "quarantined")

    def test_ghost_position_max_age_setting_is_consumed(self):
        """ghost_position_max_age drives STALE_POSITION threshold: small age stale on tight setting, not on loose."""
        old_time = (datetime.now(tz=UTC) - timedelta(seconds=6)).isoformat().replace("+00:00", "Z")
        owner = _active_owner("run-A", started_utc=datetime.now(tz=UTC) - timedelta(seconds=30))

        # max_age=5: 6-second-old position IS stale
        tracker_tight = _tracker(paper=False, max_age=5)
        pos_tight = _open_no_paper(tracker_tight, metadata=_clean_meta("run-A"))
        pos_tight.entry_time = old_time
        tracker_tight.run_sentinel_checks("run-A", active_owner=owner)
        self.assertEqual(pos_tight.status, "ghost", "Expected STALE_POSITION with max_age=5")

        # max_age=3600: same 6-second-old position is NOT stale
        tracker_loose = _tracker(paper=False, max_age=3600)
        pos_loose = _open_no_paper(tracker_loose, metadata=_clean_meta("run-A"))
        pos_loose.entry_time = old_time
        tracker_loose.run_sentinel_checks("run-A", active_owner=_active_owner("run-A", started_utc=datetime.now(tz=UTC) - timedelta(seconds=30)))
        self.assertEqual(pos_loose.status, "open", "Expected no ghost with max_age=3600")

    def test_no_false_positive_when_no_positions_exist(self):
        """Sentinel on empty tracker emits health metric with ghost_positions_found=0 and returns."""
        tracker = _tracker(paper=False)
        events = []
        tracker.run_sentinel_checks(
            "run-A",
            telemetry_emit=lambda m, p: events.append((m, p)),
        )

        ghost_events = [e for e in events if e[0] == "log_ghost_position_detected"]
        health_events = [p for m, p in events if m == "log_system_health"]
        self.assertEqual(len(ghost_events), 0)
        self.assertGreaterEqual(len(health_events), 1)
        self.assertEqual(health_events[0]["ghost_positions_found"], 0)


class SentinelFilterTests(unittest.TestCase):
    """Tests for open_positions() and ghost_positions() filter behavior."""

    def test_ghost_status_excluded_from_open_positions(self):
        """Position with status='ghost' is excluded from open_positions()."""
        tracker = _tracker(paper=False)
        pos = _open_no_paper(tracker)
        pos.status = "ghost"
        self.assertNotIn(pos, tracker.open_positions())

    def test_quarantined_metadata_excluded_from_open_positions(self):
        """Position with metadata['quarantined']=True is excluded from open_positions()."""
        tracker = _tracker(paper=False)
        pos = _open_no_paper(tracker)
        pos.metadata["quarantined"] = True
        self.assertNotIn(pos, tracker.open_positions())

    def test_ghost_positions_returns_sentinel_quarantined(self):
        """ghost_positions() returns positions quarantined by sentinel run."""
        tracker = _tracker(paper=False)
        pos = _open_no_paper(tracker, metadata={})  # OWNER_MISSING → quarantined
        tracker.run_sentinel_checks("run-A")
        self.assertIn(pos, tracker.ghost_positions())
        self.assertNotIn(pos, tracker.open_positions())


class SentinelMetadataTests(unittest.TestCase):
    """Tests for set_runtime_session_id() and open_position() paper-mode metadata injection."""

    def test_set_runtime_session_id_stores_value(self):
        """set_runtime_session_id() writes to tracker.runtime_session_id."""
        tracker = _tracker()
        tracker.set_runtime_session_id("run-xyz-001")
        self.assertEqual(tracker.runtime_session_id, "run-xyz-001")

    def test_paper_mode_injects_session_id_into_metadata(self):
        """In paper mode, open_position() injects tracker.runtime_session_id into position metadata."""
        tracker = _tracker(paper=True)
        tracker.set_runtime_session_id("run-abc")
        pos = tracker.open_position("pm-5m-btc", "polymarket", "BUY", 0.50, 5.0, 0.40, 0.60)
        self.assertEqual(pos.metadata.get("runtime_session_id"), "run-abc")

    def test_live_mode_does_not_inject_sentinel_metadata(self):
        """In live mode, open_position() does not inject runtime_session_id or owner_pid."""
        tracker = _tracker(paper=False)
        tracker.set_runtime_session_id("run-abc")
        pos = tracker.open_position("pm-5m-btc", "polymarket", "BUY", 0.50, 5.0, 0.40, 0.60)
        self.assertNotIn("runtime_session_id", pos.metadata)
        self.assertNotIn("owner_pid", pos.metadata)


if __name__ == "__main__":
    unittest.main()
