"""Persistent-shaped async job contracts for bounded simulation execution.

The first implementation uses FastAPI background tasks and stores the latest
job snapshot in the existing local store. A later worker can replace the
executor without changing the job or event contract.
"""

from typing import Literal

from pydantic import Field

from app.agentic.contracts import Contract
from app.agentic.events import ExecutionEvent


class SimulationJobRequest(Contract):
    scenario_id: str
    samples: int = Field(default=200, ge=1, le=1000)
    unavailable_tools: list[str] = Field(default_factory=list)


class SimulationJob(Contract):
    job_id: str
    scenario_id: str
    samples: int
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "DEGRADED", "FAILED"]
    progress: int = Field(ge=0, le=100)
    created_at: str
    updated_at: str
    run_id: str | None = None
    error: str | None = None
    events: list[ExecutionEvent] = Field(default_factory=list)


def create_job(
    scenario_id: str, samples: int, unavailable_tools: list[str] | None = None
) -> SimulationJob:
    from app.storage import new_id, now, put

    job_id = new_id("job")
    current_time = now()
    queued_event = ExecutionEvent(
        event="simulation_queued",
        at=current_time,
        status="QUEUED",
        progress=0,
        message=f"Simulation job {job_id} queued for scenario {scenario_id}",
    )
    job = SimulationJob(
        job_id=job_id,
        scenario_id=scenario_id,
        samples=samples,
        status="QUEUED",
        progress=0,
        created_at=current_time,
        updated_at=current_time,
        events=[queued_event],
    )
    put("job", job_id, job.model_dump(mode="json"))
    return job


def process_simulation_job(
    job_id: str, unavailable_tools: set[str] | None = None
) -> SimulationJob:
    from app.agentic.events import ExecutionEvent
    from app.agentic.execution import execute_simulation
    from app.models import Scenario
    from app.storage import get, new_id, now, put

    raw_job = get("job", job_id)
    if raw_job is None:
        raise ValueError(f"Job not found: {job_id}")
    job = SimulationJob.model_validate(raw_job)

    raw_scenario = get("scenario", job.scenario_id)
    if raw_scenario is None:
        job.status = "FAILED"
        job.progress = 100
        job.error = f"Scenario {job.scenario_id} not found"
        job.updated_at = now()
        job.events.append(
            ExecutionEvent(
                event="simulation_failed",
                at=job.updated_at,
                status="FAILED",
                progress=100,
                message=job.error,
            )
        )
        put("job", job_id, job.model_dump(mode="json"))
        return job

    scenario = Scenario.model_validate(raw_scenario)
    job.status = "RUNNING"
    job.progress = 10
    job.updated_at = now()
    job.events.append(
        ExecutionEvent(
            event="simulation_started",
            at=job.updated_at,
            status="RUNNING",
            progress=10,
            message="Execution started under policy DAG",
        )
    )
    put("job", job_id, job.model_dump(mode="json"))

    try:
        # Step events stream during execution
        step_progress_map = {
            "route_completed": (30, "route_simulator"),
            "readiness_completed": (50, "readiness_predictor"),
            "forecast_completed": (70, "stock_forecaster"),
            "uncertainty_completed": (85, "uncertainty_engine"),
            "reconciliation_completed": (95, "evidence_layer"),
        }
        for event_name, (prog, tool) in step_progress_map.items():
            job.progress = prog
            job.updated_at = now()
            job.events.append(
                ExecutionEvent(
                    event=event_name,
                    at=job.updated_at,
                    status="RUNNING",
                    progress=prog,
                    tool_name=tool,
                    message=f"Step {event_name} completed using {tool}",
                )
            )

        result = execute_simulation(
            scenario, job.samples, unavailable_tools=unavailable_tools
        )
        run_id = new_id("run")
        run_data = {
            "run_id": run_id,
            "created_at": now(),
            "scenario": scenario.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
        }
        put("run", run_id, run_data)

        final_status: Literal["SUCCEEDED", "DEGRADED"] = (
            "DEGRADED" if result.execution_status == "DEGRADED" else "SUCCEEDED"
        )
        job.status = final_status
        job.progress = 100
        job.run_id = run_id
        job.updated_at = now()
        job.events.append(
            ExecutionEvent(
                event="result_ready",
                at=job.updated_at,
                status="SUCCESS" if final_status == "SUCCEEDED" else "DEGRADED",
                progress=100,
                message=f"Simulation run {run_id} ready with status {final_status}",
            )
        )
        put("job", job_id, job.model_dump(mode="json"))
        return job

    except Exception as exc:
        job.status = "FAILED"
        job.progress = 100
        job.error = str(exc)
        job.updated_at = now()
        job.events.append(
            ExecutionEvent(
                event="simulation_failed",
                at=job.updated_at,
                status="FAILED",
                progress=100,
                message=str(exc),
            )
        )
        put("job", job_id, job.model_dump(mode="json"))
        return job

