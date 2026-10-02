# SatQuery-inspired Maya architecture

These are domain-neutral patterns adapted for the synthetic Maya logistics
simulator. They do not import satellite processing, SAR, GeoTIFF, VQA, Sentinel
datasets, Qwen, QLoRA, spectral indices or remote-sensing models.

## P0 modules

- `policy-engine`: `backend/app/agentic/policy_engine.py` defines and validates
  the static Scenario → route → readiness → supply → uncertainty → evidence →
  confidence graph. No LLM selects tools.
- `tool-registry`: `backend/app/agentic/tool_registry.py` describes tools,
  schemas, versions, availability and declared fallbacks.
- `fact-sheet`: `backend/app/agentic/contracts.py` and
  `backend/app/agentic/execution.py` preserve computed values and their source
  tools for API and UI explanation.
- `confidence-engine`: `backend/app/agentic/confidence_engine.py` reports
  execution quality with explicit caps and degradation reasons. It is not a
  statistical accuracy claim.
- `audit-trace`: `backend/app/agentic/audit_trace.py` records policy, tools,
  inputs, outputs, warnings, assumptions and final status.

## P1 extension points

The execution contracts reserve stable names for async jobs and event streams.
The initial simulator remains synchronous and bounded; job orchestration should
wrap the same policy execution rather than create a second result contract.

## Structured result rule

Every future Maya tool returns status, data/evidence, warnings, assumptions,
execution metadata and quality controls. Tool failure or fallback must remain
visible in the result and audit; no placeholder forecast may be presented as a
successful tool output.
