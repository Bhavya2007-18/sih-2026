# Initial P0 contract (implementation refinement)

Scenario/result Python authority: `backend/app/models.py`; generated OpenAPI will
describe concrete request/response validation. Fixture: `data/demo_scenario.json`.

## API

- `GET /api/demo-scenario`: fixture (proposed convenience endpoint).
- `GET /api/health`: service and simulation-only scope.
- `POST /api/scenarios`: Scenario → Scenario (201).
- `GET /api/scenarios/{id}`: Scenario.
- `PUT /api/scenarios/{id}`: Scenario with current version → incremented Scenario.
- `POST /api/scenarios/{id}/clone`: `{id, name?}` → independent Scenario (201).
- `POST /api/scenarios/{id}/events`: `{expected_version, event: Event}` → Scenario.
- `POST /api/simulations`: `{scenario_id, samples: 1..1000}` → Run.
- `GET /api/simulations/{run_id}` → Run.
- `POST /api/simulations/{run_id}/compare`: `{baseline_id}` → Comparison.

Run: `{run_id, created_at, scenario: Scenario, result: SimulationResult}`. Result
has per-candidate options containing route, readiness and supply forecasts plus
top-level recommended option outputs. It is a suggestion, not a planner decision.
The result also includes deterministic execution metadata:

- `execution_status`: `SUCCESS|DEGRADED|FAILED`.
- `policy_id` and `tool_executions`: the static policy DAG and structured tool receipts.
- `fact_sheet`: computed evidence facts with source tool, label and unit.
- `confidence`: execution-quality controls for input completeness, sample stability,
  synthetic model quality, data freshness, uncertainty control and fallback usage.
  This is not prediction accuracy or a confidence interval; the uncalibrated
  synthetic model applies an explicit quality cap.
- `audit_trace`: ordered policy/tool events with inputs, output keys, warnings and
  assumptions. A failed tool is never recorded as successful; a declared fallback
  is recorded as `DEGRADED`.
Comparison: `{baseline_id, what_if_id, changes: [{metric, before, after, delta}], explanation: string[]}`.
Metrics: route, eta_hours, readiness_score, minimum_stock, time_to_critical_hours,
shortage_quantity, connectivity_online. Delta null for categorical/missing values.
Readiness score comparison uses the lowest resource score. Stock metrics use the
destination node. Runs are immutable; only scenario snapshots may be updated.

## Offline data prototype (explicit additional API)

Record: `{id, scenario_id, kind, version, payload, updated_at}`.
Kinds: `manifest`, `inventory_update`, `delivery_status`, `resource_status`,
`scenario_event`. Required payload fields respectively:
`shipment_id,quantity`; `node_id,stock`; `shipment_id,status`;
`resource_id,readiness`; `event_id,type`. Values are JSON scalar values only.
Unknown extra payload fields allowed for inspectable field-level merging.

- `POST /api/records`: `{id, scenario_id, kind, payload}` → Record (201).
- `GET /api/records/{id}` → Record.
- `POST /api/sync/reconcile`: `{updates: Update[]}` → `{outcomes: Outcome[]}`.

Update: `{event_id, record_id, device_id, base_version, base_payload, patch,
payload_hash, created_at}`. SHA-256 hash of canonical serialized
`{event_id,record_id,device_id,base_version,base_payload,patch,created_at}`,
keys sorted, compact JSON, UTF-8 (`ensure_ascii=False`). Initial prototype payloads
use strings, boolean/null and finite integers only to avoid cross-language floating
number canonicalization ambiguity. Hash is an accidental-corruption checksum,
**not an authentication signature**.
Outcome: `{event_id, status: ACCEPTED|DUPLICATE|CONFLICT|INVALID, record?,
conflicting_fields: string[], missing_fields: string[], message}`.
Atomic per update. Compare base to current per field; nonconflicting patches merge,
conflicting mutation remains queued; no silent winner. Successful retries return
DUPLICATE. Explicit conflict resolution creates a NEW event against the current
server base; original conflict remains an inspectable local audit entry.

## Planner annotation (explicit additional API)

`POST /api/decisions`: `{run_id, route_id, note}` → `{id, run_id, route_id, note, created_at}`.
`GET /api/decisions/{id}` reads it back. Backend verifies the candidate is feasible.
No dispatch, external integration or real-world execution occurs.
