from app.agentic.contracts import Contract


class ToolSpec(Contract):
    name: str
    category: str
    inputs: list[str]
    outputs: list[str]
    schema: dict[str, str]
    availability: str
    fallback: str | None = None
    version: str = "1.0.0"


class ToolRegistry:
    def __init__(self, tools: tuple[ToolSpec, ...] = ()) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def register(self, tool: ToolSpec) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown Maya tool: {name}") from exc

    def resolve(self, name: str, unavailable: set[str] | None = None) -> tuple[ToolSpec, bool]:
        """Return the selected tool and whether a declared fallback was used."""
        unavailable = unavailable or set()
        primary = self.get(name)
        if name not in unavailable and primary.availability == "AVAILABLE":
            return primary, False
        if primary.fallback is None:
            raise RuntimeError(f"tool unavailable with no fallback: {name}")
        fallback = self.get(primary.fallback)
        if fallback.availability != "AVAILABLE" or fallback.name in unavailable:
            raise RuntimeError(f"tool and fallback unavailable: {name}")
        return fallback, True

    def describe(self) -> list[ToolSpec]:
        return list(self._tools.values())


DEFAULT_REGISTRY = ToolRegistry(
    (
        ToolSpec(
            name="route_simulator",
            category="simulation",
            inputs=["scenario", "samples"],
            outputs=["route_results", "selected_route_id"],
            schema={"scenario": "Scenario", "samples": "integer[1..1000]"},
            availability="AVAILABLE",
            fallback="deterministic_baseline",
            version="1.0.0",
        ),
        ToolSpec(
            name="readiness_predictor",
            category="simulation",
            inputs=["scenario", "route_results"],
            outputs=["readiness_results"],
            schema={"scenario": "Scenario", "route_results": "RouteResult[]"},
            availability="AVAILABLE",
            fallback="deterministic_baseline",
            version="1.0.0",
        ),
        ToolSpec(
            name="stock_forecaster",
            category="simulation",
            inputs=["scenario", "route_results", "readiness_results"],
            outputs=["supply_forecast"],
            schema={"scenario": "Scenario", "route_results": "RouteResult[]"},
            availability="AVAILABLE",
            fallback="deterministic_baseline",
            version="1.0.0",
        ),
        ToolSpec(
            name="uncertainty_engine",
            category="quality",
            inputs=["samples", "route_results", "supply_forecast"],
            outputs=["uncertainty"],
            schema={"samples": "integer[1..1000]", "outputs": "SimulationResult"},
            availability="AVAILABLE",
            fallback="deterministic_baseline",
            version="1.0.0",
        ),
        ToolSpec(
            name="evidence_layer",
            category="evidence",
            inputs=["simulation_result"],
            outputs=["fact_sheet"],
            schema={"simulation_result": "SimulationResult"},
            availability="AVAILABLE",
            fallback=None,
            version="1.0.0",
        ),
        ToolSpec(
            name="confidence_engine",
            category="quality",
            inputs=["scenario", "samples", "tool_executions"],
            outputs=["confidence"],
            schema={"scenario": "Scenario", "samples": "integer", "fallbacks": "integer"},
            availability="AVAILABLE",
            fallback=None,
            version="1.0.0",
        ),
        ToolSpec(
            name="deterministic_baseline",
            category="fallback",
            inputs=["scenario", "samples"],
            outputs=["simulation_result"],
            schema={"scenario": "Scenario", "samples": "integer[1..1000]"},
            availability="AVAILABLE",
            fallback=None,
            version="1.0.0",
        ),
    )
)
