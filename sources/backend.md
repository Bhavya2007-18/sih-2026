# Project Maya Backend
## Architecture, APIs, Data Model & Implementation Guide

**Companion documents:** `prd.md`, `implementation_plan.md`  
**Status:** Engineering design for hackathon MVP

---

## 1. Backend Responsibility

The backend is the orchestration layer for Maya. It should not contain presentation logic and it should not make autonomous operational decisions.

Its job is to:

1. accept and validate a simulation scenario
2. apply what-if events
3. run the simulation engines
4. propagate route, readiness and supply consequences
5. calculate forecasts and uncertainty ranges
6. simulate offline data state and reconciliation
7. persist scenarios and simulation runs
8. return explainable results to the frontend

The backend should expose **decision-support results**, while the planner remains the final decision-maker.

---

# 2. Recommended Stack

| Layer | Recommendation | Purpose |
|---|---|---|
| API | FastAPI + Python | REST API and orchestration |
| Validation | Pydantic | Typed request/response models |
| Simulation | NumPy + NetworkX | Monte Carlo and graph simulation |
| Data | PostgreSQL | Persistent scenario/run data |
| ORM | SQLAlchemy | Database access |
| Migrations | Alembic | Schema evolution |
| Caching | Redis, optional | Temporary run state / performance |
| Async jobs | FastAPI background tasks initially; Celery/RQ later | Long simulations |
| Testing | Pytest | Unit/integration tests |

For the hackathon MVP, keep infrastructure small. A single FastAPI service plus PostgreSQL is enough until measured performance requires more.

---

# 3. High-Level Architecture

```text
                 FRONTEND
                    │
                 REST/JSON
                    │
                    ▼
        ┌────────────────────────┐
        │       FastAPI API       │
        ├────────────────────────┤
        │ Scenario API            │
        │ Simulation API          │
        │ Forecast API            │
        │ Reconciliation API      │
        │ Health / Metadata API   │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │     Simulation Core     │
        ├────────────────────────┤
        │ Scenario State          │
        │ Event Engine            │
        │ Routing Engine          │
        │ Readiness Engine        │
        │ Supply Forecast         │
        │ Uncertainty              │
        │ Reconciliation          │
        └────────────┬───────────┘
                     │
                     ▼
              ┌─────────────┐
              │ PostgreSQL  │
              └─────────────┘
```

---

# 4. Core Domain Objects

## 4.1 Scenario

Represents one complete what-if world.

```json
{
  "id": "scenario_demo_01",
  "name": "Mountain Supply Simulation",
  "seed": 42,
  "horizon_hours": 120,
  "nodes": [],
  "routes": [],
  "resources": [],
  "stock_nodes": [],
  "events": [],
  "assumptions": []
}
```

## 4.2 Node

A logistics location in the simulation.

```text
id
name
type
latitude / longitude or synthetic coordinates
storage_capacity
initial_stock
critical_stock
consumption_rate
```

Coordinates can be synthetic for the hackathon demo.

## 4.3 Route

```text
id
origin_node
destination_node
distance
base_travel_time
capacity
environment_profile
risk_profile
availability
```

## 4.4 Resource

```text
id
resource_type
capacity
current_load
rest_hours
environment_tolerance
base_speed
readiness_state
```

The readiness values are simulation parameters, not medical diagnoses.

## 4.5 Event

Every what-if change should be represented as an explicit event.

```text
event_id
timestamp
type
severity
target
parameters
```

Example event types for the simulator:

```text
ROUTE_DISRUPTION
TRAVEL_DELAY
ENVIRONMENT_CHANGE
RESOURCE_DEGRADATION
DEMAND_CHANGE
STOCK_ADJUSTMENT
CONNECTIVITY_LOSS
CONNECTIVITY_RESTORE
```

---

# 5. Backend Workflow

```text
POST /scenarios
      ↓
Scenario validation
      ↓
POST /simulations
      ↓
Baseline simulation
      ↓
Route evaluation
      ↓
Readiness evaluation
      ↓
Delivery ETA
      ↓
Stock forecast
      ↓
Uncertainty sampling
      ↓
Combined result
      ↓
GET /simulations/{id}
```

For a what-if run:

```text
Existing Scenario
      ↓
POST /scenarios/{id}/events
      ↓
New event appended
      ↓
POST /simulations
      ↓
Re-simulate
      ↓
Compare with baseline
```

---

# 6. API Design

## Scenario APIs

### `POST /api/v1/scenarios`

Create a scenario.

### `GET /api/v1/scenarios/{scenario_id}`

Return one scenario and its assumptions.

### `PUT /api/v1/scenarios/{scenario_id}`

Update scenario inputs before a run.

### `POST /api/v1/scenarios/{scenario_id}/clone`

Create a what-if copy without mutating the baseline.

### `POST /api/v1/scenarios/{scenario_id}/events`

Append a simulated event.

---

## Simulation APIs

### `POST /api/v1/simulations`

Run a scenario.

Request:

```json
{
  "scenario_id": "scenario_demo_01",
  "mode": "baseline",
  "runs": 1000,
  "seed": 42
}
```

Response:

```json
{
  "simulation_id": "sim_001",
  "status": "completed",
  "baseline": true
}
```

### `GET /api/v1/simulations/{simulation_id}`

Return combined results.

### `GET /api/v1/simulations/{simulation_id}/routes`

Return route-level metrics.

### `GET /api/v1/simulations/{simulation_id}/forecast`

Return stock and delivery forecast.

### `GET /api/v1/simulations/{simulation_id}/readiness`

Return resource readiness timeline.

### `GET /api/v1/simulations/{simulation_id}/assumptions`

Return assumptions used by the run.

### `GET /api/v1/simulations/compare?baseline_id=...&whatif_id=...`

Return before/after deltas.

---

# 7. Combined Result Contract

The frontend should receive one stable result object.

```json
{
  "simulation_id": "sim_002",
  "scenario_id": "scenario_demo_01",
  "route_results": [],
  "readiness_results": [],
  "supply_forecast": [],
  "data_resilience": {},
  "uncertainty": {},
  "assumptions": [],
  "changes_from_baseline": []
}
```

This avoids forcing the UI to reproduce backend logic.

---

# 8. Route Engine Interface

The routing module should expose a clean function boundary:

```python
def evaluate_routes(scenario) -> RouteAnalysis:
    ...
```

Each route result should include:

```text
route_id
expected_time
travel_time_range
resilience_score
success_probability_range
fuel_or_resource_cost
key_risk_drivers
assumption_ids
```

Do not expose undocumented internal weights to the UI. Return human-readable drivers such as:

```text
Longer travel time
Higher simulated disruption exposure
Lower resource margin
Greater uncertainty
```

---

# 9. Readiness Engine Interface

```python
def evaluate_readiness(resource, route, scenario) -> ReadinessResult:
    ...
```

Inputs should include only the factors used by the implemented model, for example:

```text
load_ratio
route_duration
environment_stress
rest_hours
altitude_factor
```

Output:

```text
readiness_score
state: GREEN | AMBER | RED
time_to_threshold
factor_contributions
confidence / uncertainty
```

The dashboard should be able to answer: **"Why is this resource amber?"**

---

# 10. Supply & Stock Forecast Engine

This is the main predictive layer added to close the "simulator only" gap.

For every stock node, compute:

```text
opening_stock
consumption_rate
inbound_quantity
arrival_time
projected_stock_by_time
critical_threshold
days_of_supply
time_to_critical
```

Core calculation:

```text
Projected Stock(t)
= Opening Stock
+ Deliveries Arriving By t
- Cumulative Consumption(t)
```

The prediction should be shown as a timeline, not only as one number.

Example structure:

```text
Day 0   9.0 days supply
Day 1   7.8
Day 2   6.6
Day 3   5.1
Day 4   3.7  ← disruption delays delivery
Day 5   2.9  ← projected critical point
```

The values above are illustrative only. Demo values must be clearly labelled as synthetic.

---

# 11. Forecast API Output

```json
{
  "node_id": "POST_B",
  "days_of_supply": {
    "baseline": 9.0,
    "what_if": 3.0
  },
  "time_to_critical_hours": {
    "baseline": 216,
    "what_if": 72
  },
  "delivery_eta_hours": {
    "baseline": 28,
    "what_if": 64
  },
  "stock_timeline": [],
  "confidence_interval": {
    "low": 2.6,
    "high": 3.5
  }
}
```

Use actual simulation output in the final demo. Do not hardcode the example values.

---

# 12. Uncertainty Layer

The backend should never imply that a synthetic forecast is exact.

Store:

```text
assumption_id
parameter
base_value
low_value
high_value
source_type
notes
```

At simulation time, sample from configured ranges.

The output can then report:

```text
Estimated arrival: 54 h
Likely range: 47-63 h
```

or

```text
Projected days of supply: 3.8
Range: 3.1-4.6
```

The UI must display the assumptions behind the range.

---

# 13. Data Resilience Demo Backend

Keep the hackathon implementation concrete and observable.

## Local State

Simulate three logical field devices:

```text
Device A
Device B
Device C
```

Each has a local record store and an outbound queue.

## Offline flow

```text
CONNECTED
   ↓
Local cache populated
   ↓
CONNECTIVITY LOST
   ↓
New updates written locally
   ↓
Updates added to queue
   ↓
CONNECTIVITY RESTORED
   ↓
Peers exchange pending records
   ↓
Conflict / version checks
   ↓
Merged record
```

For the MVP, demonstrate:

- cached manifest
- queued update
- stale local version
- reconnection
- successful reconciliation
- flagged conflict if two versions disagree

Do not claim production-grade secure communications based only on a simulator.

---

# 14. Database Schema

Recommended tables:

```text
users                    optional for hackathon
scenarios
scenario_nodes
scenario_routes
scenario_resources
scenario_stock
scenario_events
scenario_assumptions
simulation_runs
route_results
readiness_results
forecast_results
sync_records
sync_events
```

## Important relations

```text
scenario 1 ─── N nodes
scenario 1 ─── N routes
scenario 1 ─── N resources
scenario 1 ─── N stock nodes
scenario 1 ─── N events
scenario 1 ─── N assumptions
scenario 1 ─── N simulation_runs
simulation_run 1 ─── N route_results
simulation_run 1 ─── N readiness_results
simulation_run 1 ─── N forecast_results
```

---

# 15. Service Boundaries

Keep modules independent enough to test separately.

```text
app/core/
    scenario.py
    events.py
    simulation.py

app/routing/
    engine.py
    scoring.py

app/readiness/
    engine.py
    scoring.py

app/supply/
    forecast.py
    inventory.py

app/uncertainty/
    sampler.py
    summarizer.py

app/reconciliation/
    queue.py
    merge.py
```

A module should consume typed inputs and return typed outputs rather than mutate unrelated state.

---

# 16. Error Handling

Return clear API errors.

Examples:

```text
400 Invalid scenario input
404 Scenario not found
409 Scenario version conflict
422 Invalid simulation parameter
500 Simulation engine failure
```

Log:

```text
time
request_id
scenario_id
simulation_id
module
error
```

Never log secrets or sensitive data.

---

# 17. Testing Strategy

## Unit tests

Test:

- route scoring
- travel-time calculation
- stock depletion
- critical threshold detection
- readiness scoring
- uncertainty sampling
- event application
- reconciliation conflicts

## Integration tests

```text
scenario → simulation → combined result
```

## Regression test

Use one fixed seed and demo scenario so a code change can be compared against a known output envelope.

---

# 18. Performance Target

The PRD targets a 1,000-run typical simulation within 60 seconds on a standard server.

First optimize the actual bottleneck. Likely steps:

1. vectorize repeated calculations
2. cache immutable scenario layers
3. reduce unnecessary serialization
4. parallelize independent Monte Carlo runs
5. move to background jobs only when necessary

Measure before and after each optimization.

---

# 19. Backend Build Order

```text
P0.1  Scenario schema
P0.2  Scenario CRUD
P0.3  Event engine
P0.4  Baseline simulation
P0.5  Route engine
P0.6  Stock forecast
P0.7  Readiness engine
P0.8  Combined result
P0.9  Compare baseline vs what-if

P1.1  Uncertainty layer
P1.2  Assumptions API
P1.3  Offline queue simulation
P1.4  Reconciliation

P2.1  Ghost convoy simulation
P2.2  Performance tuning
P2.3  Production hardening
```

---

# 20. Backend Definition of Done

The backend is MVP-complete when a client can:

```text
create scenario
→ run baseline
→ add event
→ rerun
→ receive route results
→ receive readiness results
→ receive stock forecast
→ receive uncertainty
→ receive offline reconciliation result
→ compare before/after
```

The full workflow must be executable without manually editing database rows.
