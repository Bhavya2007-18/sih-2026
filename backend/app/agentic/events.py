"""Typed execution events emitted by the async simulation job runner."""

from typing import Literal

from pydantic import Field

from app.agentic.contracts import Contract


class ExecutionEvent(Contract):
    event: Literal[
        "simulation_queued",
        "simulation_started",
        "route_completed",
        "readiness_completed",
        "forecast_completed",
        "uncertainty_completed",
        "reconciliation_completed",
        "warning",
        "result_ready",
        "simulation_failed",
    ]
    at: str
    status: Literal["QUEUED", "RUNNING", "SUCCESS", "DEGRADED", "FAILED"]
    progress: int = Field(ge=0, le=100)
    tool_name: str | None = None
    message: str | None = None


EVENT_TOOL_MAP = {
    "route_completed": "route_simulator",
    "readiness_completed": "readiness_predictor",
    "forecast_completed": "stock_forecaster",
    "uncertainty_completed": "uncertainty_engine",
}
