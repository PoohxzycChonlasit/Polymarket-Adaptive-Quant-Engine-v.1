from __future__ import annotations

import logging
import sys
import types
from types import SimpleNamespace

import pytest


def _import_main(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", types.SimpleNamespace(main=lambda: 0))
    monkeypatch.setitem(sys.modules, "polymarket.signal", types.SimpleNamespace(BACKTEST_WIN_RATE=0.5))
    import main

    return main


def test_runtime_loop_exception_emits_system_health_fail_soft(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _import_main(monkeypatch)
    events: list[dict] = []

    class QuantEvents:
        run_id = "run-exception"

        def log_system_health(self, payload: dict) -> bool:
            events.append(payload)
            return True

    trader = SimpleNamespace(quant_events=QuantEvents())

    main._emit_runtime_loop_exception(trader=trader, cycle_num=7, exc=RuntimeError("boom"))

    assert events == [
        {
            "health_event": "runtime_loop_exception",
            "exception_type": "RuntimeError",
            "exception_message": "boom",
            "cycle_num": 7,
            "run_id": "run-exception",
            "recovery_action": "cycle_skipped_continue",
            "telemetry_scope": "runtime_loop",
            "runtime_behavior_changed": "exception_observability_only",
            "strategy_risk_execution_changed": False,
            "replay_lineage_semantics_changed": False,
        }
    ]


def test_runtime_loop_exception_telemetry_failure_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _import_main(monkeypatch)

    class QuantEvents:
        run_id = "run-exception"

        def log_system_health(self, _payload: dict) -> bool:
            raise PermissionError("locked")

    trader = SimpleNamespace(quant_events=QuantEvents())

    main._emit_runtime_loop_exception(trader=trader, cycle_num=8, exc=ValueError("bad"))


def test_paper_runtime_owner_release_is_part_of_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _import_main(monkeypatch)
    calls: list[str] = []
    root_log = logging.getLogger()

    class Owner:
        def mark_stopping(self) -> bool:
            calls.append("owner.stopping")
            return True

        def release(self) -> bool:
            calls.append("owner.release")
            return True

    class Trader:
        def shutdown(self, *, join_timeout: float = 5.0) -> None:
            calls.append(f"trader.shutdown:{join_timeout}")

        def log_paper_session_summary(self, *, include_runtime_evaluation: bool = True) -> None:
            calls.append(f"trader.summary:{include_runtime_evaluation}")

    class RealtimeLogger:
        def force_save_summary(self) -> None:
            calls.append("realtime.summary")

    monkeypatch.setattr(main, "quiet_http_client_loggers_for_shutdown", lambda: calls.append("quiet_http_logs"))

    main._shutdown_realtime_resources(
        trader=Trader(),
        rl_logger=RealtimeLogger(),
        console_handlers=[],
        root_log=root_log,
        shutdown_requested=True,
        cycle_num=1,
        stop_scheduler=lambda *, join_timeout: calls.append(f"stop_scheduler:{join_timeout}"),
        runtime_owner=Owner(),
    )

    assert calls == [
        "owner.stopping",
        "quiet_http_logs",
        "trader.shutdown:1.0",
        "trader.summary:False",
        "realtime.summary",
        "stop_scheduler:1.0",
        "owner.release",
    ]


def test_duplicate_paper_owner_blocks_before_runtime_work(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _import_main(monkeypatch)
    calls: list[str] = []

    class Trader:
        quant_events = SimpleNamespace(run_id="run-blocked")

        def set_runtime_cadence_observability(self, **_kwargs) -> None:
            calls.append("cadence")

        def _ensure_connected(self) -> None:
            calls.append("connected")

        def shutdown(self, *, join_timeout: float = 5.0) -> None:
            calls.append(f"shutdown:{join_timeout}")

    class RealtimeLogger:
        pass

    class Display:
        pass

    monkeypatch.setattr(main, "get_settings", lambda: SimpleNamespace(paper_trading=True, dry_run=True))
    monkeypatch.setattr(main, "_log_paper_mode_banner", lambda _settings: None)
    monkeypatch.setattr(main, "_validate_dependencies_for_mode", lambda _mode: True)
    monkeypatch.setitem(sys.modules, "polymarket.trader", SimpleNamespace(PolymarketTrader=Trader))
    monkeypatch.setitem(
        sys.modules,
        "polymarket.observability.realtime_logger",
        SimpleNamespace(RealtimeLogger=RealtimeLogger, ScanRecord=object),
    )
    monkeypatch.setitem(sys.modules, "utils.display", SimpleNamespace(PolymarketRealtimeDisplay=Display))
    monkeypatch.setattr(main, "_acquire_paper_runtime_owner", lambda **_kwargs: None)

    assert main.run_polymarket_realtime(interval=10, force_paper=True) == 1
    assert calls == ["cadence", "shutdown:1.0"]


def test_parser_and_main_forward_duplicate_override(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _import_main(monkeypatch)
    parsed = main.build_parser().parse_args(["--mode", "paper", "--allow-duplicate-paper-runtime"])
    assert parsed.allow_duplicate_paper_runtime is True

    called: dict[str, object] = {}

    def fake_paper(interval: int = 15, *, ui_mode: str = "auto", fps_mode: str = "medium", allow_duplicate_paper_runtime: bool = False) -> int:
        called.update(
            {
                "interval": interval,
                "ui_mode": ui_mode,
                "fps_mode": fps_mode,
                "allow_duplicate_paper_runtime": allow_duplicate_paper_runtime,
            }
        )
        return 0

    monkeypatch.setattr("sys.argv", ["main.py", "--mode", "paper", "--allow-duplicate-paper-runtime"])
    monkeypatch.setattr(main, "setup_logger", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main, "run_polymarket_paper", fake_paper)

    assert main.main() == 0
    assert called == {
        "interval": 60,
        "ui_mode": "auto",
        "fps_mode": "medium",
        "allow_duplicate_paper_runtime": True,
    }
