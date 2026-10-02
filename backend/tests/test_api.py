"""API integration proof for the single MAYA what-if loop."""

import os
from pathlib import Path

os.chdir(Path(__file__).parents[1])

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app, payload_hash  # noqa: E402


def test_scenario_simulation_event_and_comparison() -> None:
    db = Path("maya.db")
    if db.exists():
        db.unlink()
    with TestClient(app) as client:
        scenario = client.get("/api/demo-scenario").json()
        assert client.post("/api/scenarios", json=scenario).status_code == 201
        baseline_response = client.post(
            "/api/simulations", json={"scenario_id": scenario["id"], "samples": 100}
        )
        assert baseline_response.status_code == 201, baseline_response.text
        baseline = baseline_response.json()

        clone = client.post(
            f"/api/scenarios/{scenario['id']}/clone",
            json={"id": "maya-what-if", "name": "MAYA what-if"},
        ).json()
        changed = client.post(
            f"/api/scenarios/{clone['id']}/events",
            json={
                "expected_version": clone["version"],
                "event": {
                    "id": "event-close-a",
                    "type": "ROUTE_UNAVAILABLE",
                    "target": "route-a",
                    "magnitude": 0,
                    "start_hour": 0,
                },
            },
        )
        assert changed.status_code == 200, changed.text
        what_if = client.post(
            "/api/simulations", json={"scenario_id": clone["id"], "samples": 100}
        )
        assert what_if.status_code == 201, what_if.text
        comparison = client.post(
            f"/api/simulations/{what_if.json()['run_id']}/compare",
            json={"baseline_id": baseline["run_id"]},
        )
        assert comparison.status_code == 200, comparison.text
        assert any(change["metric"] == "route" for change in comparison.json()["changes"])


def test_reconciliation_accepts_duplicate_and_flags_conflict() -> None:
    db = Path("maya.db")
    if db.exists():
        db.unlink()
    with TestClient(app) as client:
        scenario = client.get("/api/demo-scenario").json()
        assert client.post("/api/scenarios", json=scenario).status_code == 201
        record = client.post(
            "/api/records",
            json={
                "id": "inventory-demo",
                "scenario_id": scenario["id"],
                "kind": "inventory_update",
                "payload": {"node_id": "lake", "stock": 50},
            },
        ).json()
        update = {
            "event_id": "update-a",
            "record_id": record["id"],
            "device_id": "device-a",
            "base_version": 1,
            "base_payload": record["payload"],
            "patch": {"stock": 42},
            "created_at": "2026-10-02T00:00:00+00:00",
        }
        update["payload_hash"] = payload_hash(type("UpdateObject", (), update)())
        first = client.post("/api/sync/reconcile", json={"updates": [update]}).json()["outcomes"][0]
        assert first["status"] == "ACCEPTED"
        duplicate_res = client.post("/api/sync/reconcile", json={"updates": [update]}).json()
        assert duplicate_res["outcomes"][0]["status"] == "ACCEPTED"

        conflict = dict(update)
        conflict["event_id"] = "update-b"
        conflict["base_version"] = 1
        conflict["patch"] = {"stock": 39}
        conflict["payload_hash"] = payload_hash(type("UpdateObject", (), conflict)())
        conflict_res = client.post("/api/sync/reconcile", json={"updates": [conflict]}).json()
        result = conflict_res["outcomes"][0]
        assert result["status"] == "CONFLICT"
        assert result["conflicting_fields"] == ["stock"]
