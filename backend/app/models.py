"""Shared domain contracts. Quantity is generic supply units; all durations are hours."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agentic.contracts import AuditTrace, ConfidenceAssessment, FactSheet, ToolExecution

Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Fraction = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Node(Contract):
    id: Identifier
    name: str = Field(min_length=1, max_length=100)


class Segment(Contract):
    id: Identifier
    distance_km: Positive
    nominal_hours: Positive
    available: bool = True
    time_variation_fraction: Fraction = 0
    disruption_probability: Fraction = 0
    disruption_delay_hours: Nonnegative = 0


class Route(Contract):
    id: Identifier
    origin: Identifier
    destination: Identifier
    segments: list[Segment] = Field(min_length=1, max_length=20)
    capacity: Positive
    environment_stress: Fraction = 0
    altitude_stress: Fraction = 0


class Resource(Contract):
    id: Identifier
    resource_type: str = Field(default="synthetic_transport", max_length=100)
    capacity: Positive
    load: Nonnegative
    operating_hours: Nonnegative = 0
    rest_hours: Nonnegative = 0
    base_readiness: Annotated[float, Field(ge=0, le=100)] = 100


class Inbound(Contract):
    id: Identifier
    quantity: Nonnegative
    departure_hour: Nonnegative = 0


class StockNode(Contract):
    node_id: Identifier
    stock: Nonnegative
    reserved_stock: Nonnegative = 0
    daily_consumption: Nonnegative
    demand_variation_fraction: Fraction = 0
    safety_threshold: Nonnegative
    critical_threshold: Nonnegative
    scheduled_inbound: list[Inbound] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def coherent_stock(self) -> Self:
        if self.reserved_stock > self.stock:
            raise ValueError("reserved_stock must not exceed physical stock")
        if self.critical_threshold > self.safety_threshold:
            raise ValueError("critical_threshold must not exceed safety_threshold")
        return self


class Summary(Contract):
    median: float
    p10: float
    p90: float


class ReadinessPoint(Contract):
    hour: float
    score: float


class ReadinessResult(Contract):
    resource_id: str
    score: float
    state: Literal["GREEN", "AMBER", "RED"]
    feasible: bool
    time_to_threshold_hours: float | None
    factor_contributions: dict[str, float]
    timeline: list[ReadinessPoint]


class StockPoint(Contract):
    hour: float
    stock: Summary
    days_of_supply: Summary | None


class StockForecast(Contract):
    node_id: str
    stock_timeline: list[StockPoint]
    minimum_stock: Summary
    shortage_quantity: Summary
    time_to_critical_hours: Summary | None
    critical_probability: Fraction
    critical_date: str | None
    time_to_stockout_hours: Summary | None
    stockout_probability: Fraction
    stockout_date: str | None
    safety_threshold: float
    critical_threshold: float
    notes: list[str]


class RouteResult(Contract):
    route_id: str
    distance_km: float
    nominal_hours: float
    eta_hours: Summary | None
    success_probability: Fraction
    resilience_score: float
    feasible: bool
    score: float
    drivers: list[str]


class Option(Contract):
    route: RouteResult
    readiness: list[ReadinessResult]
    supply_forecast: list[StockForecast]


class SimulationResult(Contract):
    scenario_id: str
    seed: int
    samples: int
    selected_route_id: str | None
    options: list[Option]
    route_results: list[RouteResult]
    readiness_results: list[ReadinessResult]
    supply_forecast: list[StockForecast]
    assumptions: list[str]
    uncertainty: dict[str, str]
    data_resilience: dict[str, str | bool]
    execution_status: Literal["SUCCESS", "DEGRADED", "FAILED"] = "SUCCESS"
    policy_id: str = "maya.synthetic.simulation"
    tool_executions: list[ToolExecution] = Field(default_factory=list)
    fact_sheet: FactSheet | None = None
    confidence: ConfidenceAssessment | None = None
    audit_trace: AuditTrace | None = None


class Event(Contract):
    id: Identifier
    type: Literal[
        "ROUTE_DELAY",
        "ROUTE_UNAVAILABLE",
        "DEMAND_CHANGE",
        "ENVIRONMENT_CHANGE",
        "LOAD_CHANGE",
        "REST_CHANGE",
        "CONNECTIVITY_LOSS",
        "CONNECTIVITY_RESTORE",
    ]
    target: Identifier
    magnitude: Nonnegative = 0
    start_hour: Literal[0] = 0


class ReadinessConfig(Contract):
    load_penalty: Nonnegative = 20
    duration_penalty_per_hour: Nonnegative = 0.5
    workload_penalty_per_hour: Nonnegative = 0.2
    rest_recovery_per_hour: Nonnegative = 1
    max_rest_recovery: Nonnegative = 10
    environment_penalty: Nonnegative = 15
    altitude_penalty: Nonnegative = 10
    green_threshold: Annotated[float, Field(ge=0, le=100)] = 80
    amber_threshold: Annotated[float, Field(ge=0, le=100)] = 50
    feasibility_threshold: Annotated[float, Field(ge=0, le=100)] = 40

    @model_validator(mode="after")
    def ordered_thresholds(self) -> Self:
        if not self.feasibility_threshold <= self.amber_threshold <= self.green_threshold:
            raise ValueError("readiness thresholds must be ordered")
        return self


class ScoringConfig(Contract):
    time_weight: Nonnegative = 1
    failure_weight: Nonnegative = 2
    critical_stock_weight: Nonnegative = 1


class Scenario(Contract):
    id: Identifier
    name: str = Field(min_length=1, max_length=150)
    version: int = Field(default=1, ge=1)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    start_time: str = "2026-10-02T00:00:00Z"
    horizon_hours: Annotated[float, Field(gt=0, le=336)] = 120
    step_hours: Annotated[float, Field(ge=1, le=24)] = 6
    origin: Identifier
    destination: Identifier
    nodes: list[Node] = Field(min_length=2, max_length=20)
    routes: list[Route] = Field(min_length=1, max_length=10)
    resources: list[Resource] = Field(min_length=1, max_length=5)
    stock_nodes: list[StockNode] = Field(min_length=1, max_length=10)
    events: list[Event] = Field(default_factory=list, max_length=30)
    assumptions: list[str] = Field(default_factory=list, max_length=30)
    connectivity_online: bool = True
    readiness_config: ReadinessConfig = Field(default_factory=ReadinessConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)

    @model_validator(mode="after")
    def references(self) -> Self:
        from datetime import datetime

        parsed = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("start_time must include timezone")
        for ids in (
            [item.id for item in self.nodes],
            [item.id for item in self.routes],
            [item.id for item in self.resources],
            [item.id for item in self.events],
        ):
            if len(ids) != len(set(ids)):
                raise ValueError("IDs must be unique within each entity type")
        nodes = {node.id for node in self.nodes}
        routes = {route.id for route in self.routes}
        resources = {resource.id for resource in self.resources}
        stocks = {stock.node_id for stock in self.stock_nodes}
        if len(stocks) != len(self.stock_nodes):
            raise ValueError("one stock state per node")
        if self.origin == self.destination or not {self.origin, self.destination} <= nodes:
            raise ValueError("origin/destination must be distinct defined nodes")
        if not stocks <= nodes or self.destination not in stocks:
            raise ValueError("stock nodes must exist and include destination")
        for route in self.routes:
            if (route.origin, route.destination) != (self.origin, self.destination):
                raise ValueError("candidate routes must share scenario origin/destination")
            ids = [segment.id for segment in route.segments]
            if len(ids) != len(set(ids)):
                raise ValueError("segment IDs must be unique within route")
        for stock in self.stock_nodes:
            ids = [inbound.id for inbound in stock.scheduled_inbound]
            if len(ids) != len(set(ids)):
                raise ValueError("inbound IDs must be unique within stock node")
            if stock.node_id != self.destination and stock.scheduled_inbound:
                raise ValueError("initial MVP inbound is supported only at destination")
        for event in self.events:
            if event.type.startswith("ROUTE_") or event.type == "ENVIRONMENT_CHANGE":
                valid = event.target in routes
            elif event.type in {"LOAD_CHANGE", "REST_CHANGE"}:
                valid = event.target in resources
            elif event.type == "DEMAND_CHANGE":
                valid = event.target in stocks
            else:
                valid = event.target == self.id
            if not valid:
                raise ValueError(f"invalid target for event {event.id}")
            if event.type == "ENVIRONMENT_CHANGE" and event.magnitude > 1:
                raise ValueError("environment magnitude must be a normalized index 0–1")
        return self
