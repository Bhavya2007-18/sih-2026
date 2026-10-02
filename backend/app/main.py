"""MAYA local API: scenario persistence, simulation and inspectable sync records."""

import copy
import hashlib
import json
from typing import Any, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from app.agentic.jobs import SimulationJob, SimulationJobRequest, create_job, process_simulation_job
from app.agentic.tool_registry import DEFAULT_REGISTRY, ToolSpec
from app.core.comparison import compare_runs
from app.core.simulation import run_simulation
from app.models import Event, Scenario, SimulationResult
from app.storage import add_receipt, get, has_receipt, init_db, new_id, now, put


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunRequest(StrictRequest):
    scenario_id: str
    samples: int = Field(default=200, ge=1, le=1000)


class CloneRequest(StrictRequest):
    id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str | None = Field(default=None, max_length=150)


class EventRequest(StrictRequest):
    expected_version: int = Field(ge=1)
    event: Event


class CompareRequest(StrictRequest):
    baseline_id: str


Scalar = str | int | bool | None


class DataRecordRequest(StrictRequest):
    id: str = Field(min_length=1, max_length=160)
    scenario_id: str
    kind: Literal[
        "manifest", "inventory_update", "delivery_status", "resource_status", "scenario_event"
    ]
    payload: dict[str, Scalar]


class Update(StrictRequest):
    event_id: str
    record_id: str
    device_id: str
    base_version: int = Field(ge=1)
    base_payload: dict[str, Scalar]
    patch: dict[str, Scalar]
    payload_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: str


class ReconcileRequest(StrictRequest):
    updates: list[Update] = Field(max_length=100)


class DecisionRequest(StrictRequest):
    run_id: str
    route_id: str
    note: str = Field(min_length=1, max_length=1000)


def canonical(value: Any) -> str:
    """Canonical JSON matching the documented browser checksum protocol."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def payload_hash(update: Update) -> str:
    envelope = {
        "event_id": update.event_id,
        "record_id": update.record_id,
        "device_id": update.device_id,
        "base_version": update.base_version,
        "base_payload": update.base_payload,
        "patch": update.patch,
        "created_at": update.created_at,
    }
    return hashlib.sha256(canonical(envelope).encode("utf-8")).hexdigest()


def scenario_or_404(identifier: str) -> Scenario:
    raw = get("scenario", identifier)
    if raw is None:
        raise HTTPException(404, "Scenario not found")
    return Scenario.model_validate(raw)


def run_or_404(identifier: str) -> dict[str, Any]:
    raw = get("run", identifier)
    if raw is None:
        raise HTTPException(404, "Simulation run not found")
    return raw


def validate_record_payload(kind: str, payload: dict[str, Scalar]) -> None:
    required = {
        "manifest": {"shipment_id", "quantity"},
        "inventory_update": {"node_id", "stock"},
        "delivery_status": {"shipment_id", "status"},
        "resource_status": {"resource_id", "readiness"},
        "scenario_event": {"event_id", "type"},
    }[kind]
    missing = sorted(required - payload.keys())
    if missing:
        raise HTTPException(422, {"missing_fields": missing})


app = FastAPI(title="MAYA Synthetic Logistics Simulator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "scope": "synthetic simulation only", "time": now()}


@app.get("/api/demo-scenario")
def demo_scenario() -> Scenario:
    from pathlib import Path

    path = Path(__file__).parents[2] / "data/demo_scenario.json"
    return Scenario.model_validate_json(path.read_text())


@app.post("/api/scenarios", status_code=status.HTTP_201_CREATED)
def create_scenario(scenario: Scenario) -> Scenario:
    if get("scenario", scenario.id) is not None:
        raise HTTPException(409, "Scenario ID already exists")
    put("scenario", scenario.id, scenario.model_dump(mode="json"))
    return scenario


@app.get("/api/scenarios/{scenario_id}")
def read_scenario(scenario_id: str) -> Scenario:
    return scenario_or_404(scenario_id)


@app.put("/api/scenarios/{scenario_id}")
def update_scenario(scenario_id: str, scenario: Scenario) -> Scenario:
    current = scenario_or_404(scenario_id)
    if scenario.id != scenario_id or scenario.version != current.version:
        raise HTTPException(409, "Scenario ID/version does not match current server snapshot")
    updated = scenario.model_copy(update={"version": current.version + 1})
    put("scenario", scenario_id, updated.model_dump(mode="json"))
    return updated


@app.post("/api/scenarios/{scenario_id}/clone", status_code=status.HTTP_201_CREATED)
def clone_scenario(scenario_id: str, request: CloneRequest) -> Scenario:
    source = scenario_or_404(scenario_id)
    if get("scenario", request.id) is not None:
        raise HTTPException(409, "Clone ID already exists")
    clone = source.model_copy(
        deep=True,
        update={"id": request.id, "name": request.name or source.name, "version": 1},
    )
    put("scenario", clone.id, clone.model_dump(mode="json"))
    return clone


@app.post("/api/scenarios/{scenario_id}/events")
def append_event(scenario_id: str, request: EventRequest) -> Scenario:
    current = scenario_or_404(scenario_id)
    if request.expected_version != current.version:
        raise HTTPException(409, "Scenario version is stale")
    updated = current.model_copy(
        deep=True,
        update={"version": current.version + 1, "events": [*current.events, request.event]},
    )
    put("scenario", scenario_id, updated.model_dump(mode="json"))
    return updated


@app.get("/api/scenarios/{scenario_id}/map")
def get_scenario_map(scenario_id: str) -> dict[str, Any]:
    """Return central map model geometry and synthetic overlays for MapLibre GL JS."""
    return {
        "scenario_id": scenario_id,
        "scope": "synthetic scenario",
        "origin": {
            "id": "orig-1",
            "name": "Leh Supply Depot",
            "lat": 34.1526,
            "lng": 77.5771,
        },
        "destination": {
            "id": "dest-1",
            "name": "Karakoram Forward Post",
            "lat": 35.1378,
            "lng": 78.1345,
        },
        "nodes": [
            {"id": "node-1", "name": "Kharu Staging Post", "lat": 33.9500, "lng": 77.7200, "status": "OPERATIONAL"},
            {"id": "node-2", "name": "Tangtse Checkpoint", "lat": 34.0200, "lng": 78.1800, "status": "DEGRADED"},
            {"id": "node-3", "name": "Saser Pass Relay", "lat": 34.7500, "lng": 77.8500, "status": "OPERATIONAL"},
        ],
        "routes": [
            {
                "id": "route-a",
                "name": "Route A (Primary Axis)",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [77.5771, 34.1526],
                        [77.7200, 33.9500],
                        [77.9500, 34.2500],
                        [78.1800, 34.0200],
                        [78.1345, 35.1378],
                    ],
                },
                "eta": {"hours": 6.8, "formatted": "6.8 h"},
                "resilience": 0.74,
                "risk_level": "MEDIUM",
            },
            {
                "id": "route-b",
                "name": "Route B (High Pass Bypass)",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [77.5771, 34.1526],
                        [77.8500, 34.7500],
                        [78.0000, 34.9000],
                        [78.1345, 35.1378],
                    ],
                },
                "eta": {"hours": 7.4, "formatted": "7.4 h"},
                "resilience": 0.81,
                "risk_level": "LOW",
            },
            {
                "id": "route-c",
                "name": "Route C (Direct Valley Express)",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [77.5771, 34.1526],
                        [77.6800, 34.4500],
                        [77.9200, 34.8000],
                        [78.1345, 35.1378],
                    ],
                },
                "eta": {"hours": 5.9, "formatted": "5.9 h"},
                "resilience": 0.61,
                "risk_level": "HIGH",
            },
        ],
        "events": [
            {
                "id": "evt-disrupt-1",
                "name": "Landslide Blockade",
                "type": "DISRUPTION",
                "lat": 34.4500,
                "lng": 77.6800,
                "severity": "CRITICAL",
                "details": "Active pass obstruction reported",
            }
        ],
    }


@app.get("/api/tools")
def list_tools() -> list[ToolSpec]:
    """Expose Declarative Tool Registry for Maya modules."""
    return DEFAULT_REGISTRY.describe()


@app.get("/api/tools/{tool_name}")
def get_tool(tool_name: str) -> ToolSpec:
    """Return tool spec for a specific Maya simulation module."""
    try:
        return DEFAULT_REGISTRY.get(tool_name)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/simulations", status_code=status.HTTP_201_CREATED)
def create_simulation(request: RunRequest) -> dict[str, Any]:
    scenario = scenario_or_404(request.scenario_id)
    result = run_simulation(scenario, request.samples)
    run_id = new_id("run")
    run = {
        "run_id": run_id,
        "created_at": now(),
        "scenario": scenario.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
    }
    put("run", run_id, run)
    return run


@app.post("/api/simulations/jobs", status_code=status.HTTP_202_ACCEPTED)
def create_simulation_job(
    request: SimulationJobRequest, background_tasks: BackgroundTasks
) -> SimulationJob:
    """Async job creation endpoint emitting execution event stream."""
    scenario_or_404(request.scenario_id)
    job = create_job(
        request.scenario_id, request.samples, unavailable_tools=request.unavailable_tools
    )
    unavailable_set = set(request.unavailable_tools) if request.unavailable_tools else None
    background_tasks.add_task(process_simulation_job, job.job_id, unavailable_tools=unavailable_set)
    return job


@app.get("/api/simulations/jobs/{job_id}")
def read_simulation_job(job_id: str) -> SimulationJob:
    raw_job = get("job", job_id)
    if raw_job is None:
        raise HTTPException(404, "Job not found")
    return SimulationJob.model_validate(raw_job)


@app.get("/api/simulations/jobs/{job_id}/events")
def read_job_events(job_id: str) -> dict[str, Any]:
    job = read_simulation_job(job_id)
    return {"job_id": job.job_id, "status": job.status, "events": job.events}


@app.get("/api/simulations/{run_id}")
def read_simulation(run_id: str) -> dict[str, Any]:
    return run_or_404(run_id)


@app.post("/api/simulations/{run_id}/compare")
def compare_simulation(run_id: str, request: CompareRequest) -> dict[str, Any]:
    what_if = run_or_404(run_id)
    baseline = run_or_404(request.baseline_id)
    if baseline["scenario"]["id"] == what_if["scenario"]["id"]:
        raise HTTPException(422, "Comparison requires distinct baseline and what-if scenarios")
    comparison = compare_runs(
        # Re-validate stored JSON so persistence is also a contract boundary.
        SimulationResult.model_validate(baseline["result"]),
        SimulationResult.model_validate(what_if["result"]),
    )
    return {"baseline_id": request.baseline_id, "what_if_id": run_id, **comparison}


@app.post("/api/records", status_code=status.HTTP_201_CREATED)
def create_record(request: DataRecordRequest) -> dict[str, Any]:
    validate_record_payload(request.kind, request.payload)
    existing = get("record", request.id)
    if existing is not None:
        raise HTTPException(409, "Record ID already exists")
    record = {
        "id": request.id,
        "scenario_id": request.scenario_id,
        "kind": request.kind,
        "version": 1,
        "payload": request.payload,
        "updated_at": now(),
    }
    put("record", request.id, record)
    return record


@app.get("/api/records/{record_id}")
def read_record(record_id: str) -> dict[str, Any]:
    record = get("record", record_id)
    if record is None:
        raise HTTPException(404, "Record not found")
    return record


def outcome(
    update: Update,
    status_name: str,
    record: dict[str, Any] | None = None,
    *,
    conflicts: list[str] | None = None,
    missing: list[str] | None = None,
    message: str = "",
) -> dict[str, Any]:
    return {
        "event_id": update.event_id,
        "status": status_name,
        "record": record,
        "conflicting_fields": conflicts or [],
        "missing_fields": missing or [],
        "message": message,
    }


@app.post("/api/sync/reconcile")
def reconcile(request: ReconcileRequest) -> dict[str, list[dict[str, Any]]]:
    receipts: list[dict[str, Any]] = []
    for update in request.updates:
        if payload_hash(update) != update.payload_hash:
            receipts.append(outcome(update, "INVALID", message="SHA-256 payload checksum failed"))
            continue
        previous = has_receipt(update.event_id)
        if previous is not None:
            if previous.payload_hash != update.payload_hash:
                receipts.append(
                    outcome(update, "INVALID", message="Event ID was reused with different bytes")
                )
            else:
                receipts.append(
                    outcome(
                        update,
                        previous.status,
                        read_record(update.record_id),
                        message="Idempotent receipt already recorded",
                    )
                )
            continue
        current = get("record", update.record_id)
        if current is None:
            receipts.append(
                outcome(update, "INVALID", missing=["record"], message="Record base does not exist")
            )
            add_receipt(update.event_id, update.payload_hash, "INVALID", update.record_id)
            continue
        if current["version"] != update.base_version:
            base = update.base_payload
            conflicts = sorted(
                key for key in update.patch if current["payload"].get(key) != base.get(key)
            )
            missing = sorted(
                key for key in update.patch if key not in current["payload"] and key not in base
            )
            if conflicts or missing:
                record = copy.deepcopy(current)
                receipts.append(
                    outcome(
                        update,
                        "CONFLICT",
                        record,
                        conflicts=conflicts,
                        missing=missing,
                        message="Version conflict; planner must inspect and explicitly rebase. "
                        "No winner was chosen.",
                    )
                )
                add_receipt(update.event_id, update.payload_hash, "CONFLICT", update.record_id)
                continue
        merged = copy.deepcopy(current)
        merged["payload"] = {**current["payload"], **update.patch}
        validate_record_payload(merged["kind"], merged["payload"])
        merged["version"] = current["version"] + 1
        merged["updated_at"] = now()
        put("record", merged["id"], merged)
        add_receipt(update.event_id, update.payload_hash, "ACCEPTED", update.record_id)
        receipts.append(
            outcome(
                update,
                "ACCEPTED",
                merged,
                message="Patch merged after version and checksum checks",
            )
        )
    return {"outcomes": receipts}


@app.post("/api/decisions", status_code=status.HTTP_201_CREATED)
def create_decision(request: DecisionRequest) -> dict[str, str]:
    run = run_or_404(request.run_id)
    feasible = {
        option["route"]["route_id"]
        for option in run["result"]["options"]
        if option["route"]["feasible"]
    }
    if request.route_id not in feasible:
        raise HTTPException(422, "Planner decisions must reference a feasible simulated option")
    decision = {
        "id": new_id("decision"),
        "run_id": request.run_id,
        "route_id": request.route_id,
        "note": request.note,
        "created_at": now(),
    }
    put("decision", decision["id"], decision)
    return decision


@app.get("/api/decisions/{decision_id}")
def read_decision(decision_id: str) -> dict[str, Any]:
    decision = get("decision", decision_id)
    if decision is None:
        raise HTTPException(404, "Decision not found")
    return decision
