"""Explicit fallback selection; unavailable tools never report primary success."""

from dataclasses import dataclass

from app.agentic.tool_registry import DEFAULT_REGISTRY, ToolRegistry, ToolSpec


@dataclass(frozen=True)
class FallbackSelection:
    selected: ToolSpec
    requested: str
    fallback_used: bool
    warning: str | None = None


def select_tool(
    name: str,
    *,
    unavailable: set[str] | None = None,
    registry: ToolRegistry = DEFAULT_REGISTRY,
) -> FallbackSelection:
    selected, used = registry.resolve(name, unavailable)
    return FallbackSelection(
        selected=selected,
        requested=name,
        fallback_used=used,
        warning=(
            f"{name} unavailable; executed declared fallback {selected.name}."
            if used
            else None
        ),
    )
