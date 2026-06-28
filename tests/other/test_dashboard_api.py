import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.dashboard_api import create_app


def _client(path: Path) -> TestClient:
    return TestClient(create_app(dashboard_state_path=path))


def test_dashboard_state_endpoint_success(tmp_path: Path) -> None:
    dashboard_state = {
        "meta": {"schema_version": "dashboard_state.v0", "state_status": "OK"},
        "runtime": {"execution_mode": "PAPER ONLY"},
        "alerts": {"active": []},
    }
    state_path = tmp_path / "dashboard_state.json"
    state_path.write_text(json.dumps(dashboard_state), encoding="utf-8")

    response = _client(state_path).get("/api/dashboard/state")

    assert response.status_code == 200
    assert response.json() == dashboard_state


def test_dashboard_state_endpoint_missing_file(tmp_path: Path) -> None:
    response = _client(tmp_path / "missing_dashboard_state.json").get("/api/dashboard/state")

    assert response.status_code == 503
    assert response.json() == {"status": "missing_dashboard_state"}


def test_dashboard_health_endpoint(tmp_path: Path) -> None:
    state_path = tmp_path / "dashboard_state.json"
    state_path.write_text(
        json.dumps({"meta": {"state_status": "PARTIAL"}, "runtime": {}, "alerts": {}}),
        encoding="utf-8",
    )

    response = _client(state_path).get("/api/dashboard/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "dashboard_state_exists": True,
        "state_status": "PARTIAL",
    }


def test_invalid_json_handling(tmp_path: Path) -> None:
    state_path = tmp_path / "dashboard_state.json"
    state_path.write_text("{not-json", encoding="utf-8")

    state_response = _client(state_path).get("/api/dashboard/state")
    health_response = _client(state_path).get("/api/dashboard/health")

    assert state_response.status_code == 503
    assert state_response.json() == {"status": "invalid_dashboard_state"}
    assert health_response.status_code == 200
    assert health_response.json() == {
        "status": "ok",
        "dashboard_state_exists": True,
        "state_status": "ERROR",
    }
