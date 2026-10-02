"""Tests for imported SatQuery-AI architectural patterns in Maya:
- Policy DAG & Declarative Tool Registry
- FactSheet / Evidence Layer
- Audit Trace
- Confidence & Uncertainty Control
- Graceful Fallback / Degraded Execution
- Async Job Architecture & Execution Event Stream
- Structured Tool Outputs
"""

from pathlib import Path

from fastapi.testclient import TestClient  # noqa: E402

from app.agentic.contracts import StructuredToolOutput  # noqa: E402
from app.agentic.execution import execute_simulation  # noqa: E402
from app.agentic.policy_engine import MAYA_SIMULATION_POLICY  # noqa: E402
from app.agentic.tool_registry import DEFAULT_REGISTRY  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Scenario  # noqa: E402


def demo_scenario() -> Scenario:
    path = Path(__file__).resolve().parents[2] / "data" / "demo_scenario.json"
    return Scenario.model_validate_json(path.read_text())


def test_declarative_tool_registry() -> None:
    tools = DEFAULT_REGISTRY.describe()
    tool_names = [t.name for t in tools]
    assert "route_simulator" in tool_names
    assert "stock_forecaster" in tool_names
    assert "readiness_predictor" in tool_names
    assert "uncertainty_engine" in tool_names
    assert "evidence_layer" in tool_names
    assert "confidence_engine" in tool_names
    assert "deterministic_baseline" in tool_names

    spec = DEFAULT_REGISTRY.get("route_simulator")
    assert spec.category == "simulation"
    assert spec.availability == "AVAILABLE"
    assert spec.fallback == "deterministic_baseline"
    assert spec.version == "1.0.0"


def test_policy_dag_execution() -> None:
    steps = [step.id for step in MAYA_SIMULATION_POLICY.steps]
    assert steps == ["route", "readiness", "supply", "uncertainty", "evidence", "confidence"]


def test_factsheet_and_audit_trace() -> None:
    scenario = demo_scenario()
    result = execute_simulation(scenario, samples=50)

    # FactSheet
    metadata = result.model_dump(mode="json")
    assert "fact_sheet" in metadata
    facts = metadata["fact_sheet"]["facts"]
    assert "route.eta_p50_hours" in facts
    assert "route.eta_p90_hours" in facts
    assert "route.arrival_probability" in facts
    assert "stock.current_stock" in facts
    assert "stock.projected_stock" in facts
    assert "stock.critical_threshold" in facts
    assert "readiness.minimum_score" in facts

    # Audit trace
    assert "audit_trace" in metadata
    trace = metadata["audit_trace"]
    assert trace["policy_id"] == "maya.synthetic.simulation"
    events = [entry["event"] for entry in trace["entries"]]
    assert "simulation_started" in events
    assert "route_completed" in events
    assert "result_ready" in events


def test_confidence_assessment() -> None:
    scenario = demo_scenario()
    result = execute_simulation(scenario, samples=1000)
    metadata = result.model_dump(mode="json")
    confidence = metadata["confidence"]
    assert 0 <= confidence["score"] <= 1
    assert "factors" in confidence
    assert "input_completeness" in confidence["factors"]
    assert "simulation_stability" in confidence["factors"]


def test_graceful_fallback_degraded_execution() -> None:
    scenario = demo_scenario()
    # Mark stock_forecaster unavailable
    result = execute_simulation(scenario, samples=20, unavailable_tools={"stock_forecaster"})
    metadata = result.model_dump(mode="json")

    assert metadata["execution_status"] == "DEGRADED"
    tool_execs = {item["tool_name"]: item for item in metadata["tool_executions"]}
    assert tool_execs["deterministic_baseline"]["status"] == "DEGRADED"
    assert tool_execs["deterministic_baseline"]["fallback_used"] is True


def test_structured_tool_output_contract() -> None:
    output = StructuredToolOutput(
        status="degraded",
        data={"metric": 42},
        warnings=["Fallback activated"],
        assumptions=["Synthetic baseline"],
        confidence={"score": 0.35},
        execution_time_ms=12.5,
    )
    assert output.status == "degraded"
    assert output.data["metric"] == 42
    assert output.execution_time_ms == 12.5


def test_async_job_and_events_api() -> None:
    db = Path("maya.db")
    if db.exists():
        db.unlink()
    with TestClient(app) as client:
        # Tool registry endpoints
        tools_resp = client.get("/api/tools")
        assert tools_resp.status_code == 200
        assert len(tools_resp.json()) >= 7

        single_tool = client.get("/api/tools/route_simulator")
        assert single_tool.status_code == 200
        assert single_tool.json()["name"] == "route_simulator"

        scenario = client.get("/api/demo-scenario").json()
        assert client.post("/api/scenarios", json=scenario).status_code == 201

        # Post simulation job
        job_resp = client.post(
            "/api/simulations/jobs",
            json={"scenario_id": scenario["id"], "samples": 50},
        )
        assert job_resp.status_code == 202
        job = job_resp.json()
        job_id = job["job_id"]
        assert job["status"] in ("QUEUED", "RUNNING", "SUCCEEDED")

        # Read job
        read_job = client.get(f"/api/simulations/jobs/{job_id}")
        assert read_job.status_code == 200
        assert read_job.json()["job_id"] == job_id

        # Read job events
        events_resp = client.get(f"/api/simulations/jobs/{job_id}/events")
        assert events_resp.status_code == 200
        events_data = events_resp.json()
        assert events_data["job_id"] == job_id
        assert len(events_data["events"]) >= 1
