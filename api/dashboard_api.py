"""Read-only FastAPI surface for Quant Dashboard V0 state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse


DEFAULT_DASHBOARD_STATE_PATH = Path("runtime/dashboard_state.json")


def _read_dashboard_state(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return None, "missing_dashboard_state"
    except json.JSONDecodeError:
        return None, "invalid_dashboard_state"
    except OSError:
        return None, "unreadable_dashboard_state"
    if not isinstance(payload, dict):
        return None, "invalid_dashboard_state"
    return payload, None


def create_app(dashboard_state_path: str | Path = DEFAULT_DASHBOARD_STATE_PATH) -> FastAPI:
    """Create the read-only dashboard API app."""

    state_path = Path(dashboard_state_path)
    app = FastAPI(title="Quant Dashboard API V0")

    @app.get("/api/dashboard/state", response_model=None)
    def dashboard_state() -> Any:
        state, error = _read_dashboard_state(state_path)
        if error:
            return JSONResponse(status_code=503, content={"status": error})
        return state

    @app.get("/api/dashboard/health")
    def dashboard_health() -> dict[str, Any]:
        state, error = _read_dashboard_state(state_path)
        if error == "missing_dashboard_state":
            exists = False
            state_status = "ERROR"
        elif error:
            exists = True
            state_status = "ERROR"
        else:
            exists = True
            meta = state.get("meta") if isinstance(state, dict) else {}
            state_status = str(meta.get("state_status") or "ERROR") if isinstance(meta, dict) else "ERROR"
        return {
            "status": "ok",
            "dashboard_state_exists": exists,
            "state_status": state_status,
        }

    return app


app = create_app()
