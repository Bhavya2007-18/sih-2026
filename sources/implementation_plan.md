# Project Maya Implementation Plan
## Predictive Logistics Simulation & Decision-Support MVP

**Version:** 0.2  
**Date:** October 2026  
**Companion document:** `prd.md`

---

## 1. Implementation Strategy

Build Maya as **one integrated simulator first**, then deepen individual modules.

The engineering priority is not to create five separate products. The priority is to make one end-to-end what-if workflow work reliably:

```text
Scenario Builder
      ↓
Baseline Simulation
      ↓
What-If Event
      ↓
Re-Simulation
      ↓
Route + Readiness + Supply Forecast
      ↓
Uncertainty + Assumptions
      ↓
Offline Data Simulation
      ↓
Combined Dashboard
      ↓
Human Planner Decision
```

### Priority order

```text
P0  Shared scenario model
P0  Event + simulation pipeline
P0  Route resilience
P0  Supply/stock forecasting
P0  Readiness model
P0  Dashboard + before/after comparison
P1  Uncertainty / assumptions
P1  Offline queue + reconciliation
P2  Ghost Convoys
```

The demo should work even if P2 is incomplete.

---

# 2. Recommended MVP Architecture

```text
                     ┌──────────────────────┐
                     │     Web Planner UI   │
                     │ Scenario + Dashboard │
                     └──────────┬───────────┘
                                │ REST/JSON
                                ▼
                     ┌──────────────────────┐
                     │      API Server      │
                     │ scenario / run / sync│
                     └──────────┬───────────┘
                                │
                                ▼
                ┌────────────────────────────────┐
                │      MAYA SIMULATION CORE       │
                ├────────────────────────────────┤
                │  Scenario State                 │
                │  Event Engine                   │
                │  Route Engine                   │
                │  Readiness Engine               │
                │  Supply Forecast Engine         │
                │  Uncertainty Sampler            │
                │  Reconciliation Engine          │
                └───────────────┬────────────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │ Results / Persistence│
                     │ scenario + run + log │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │ Combined Result View │
                     └──────────────────────┘

Optional:
Ghost Convoy Simulation Service / Module
```

### Design principle

Keep the **simulation engine independent from the UI**.

That means:

- the same scenario can be run from a test script
- API output can be validated without the browser
- demo data can be replayed deterministically
- frontend redesign does not change simulation logic

---

# 3. Suggested Repository Structure

```text
project-maya/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── scenarios.py
│   │   │   ├── simulations.py
│   │   │   ├── sync.py
│   │   │   └── health.py
│   │   ├── core/
│   │   │   ├── scenario.py
│   │   │   ├── events.py
│   │   │   ├── simulation.py
│   │   │   └── random.py
│   │   ├── routing/
│   │   │   ├── engine.py
│   │   │   ├── scoring.py
│   │   │   └── models.py
│   │   ├── readiness/
│   │   │   ├── engine.py
│   │   │   ├── scoring.py
│   │   │   └── models.py
│   │   ├── supply/
│   │   │   ├── forecast.py
│   │   │   ├── inventory.py
│   │   │   └── models.py
│   │   ├── uncertainty/
│   │   │   ├── sampler.py
│   │   │   └── summarizer.py
│   │   ├── reconciliation/
│   │   │   ├── ledger.py
│   │   │   ├── queue.py
│   │   │   └── merge.py
│   │   └── storage/
│   │       ├── db.py
│   │       └── repositories.py
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ScenarioBuilder/
│   │   │   ├── RouteComparison/
│   │   │   ├── ReadinessCard/
│   │   │   ├── StockForecast/
│   │   │   ├── UncertaintyPanel/
│   │   │   ├── OfflineStatus/
│   │   │   └── WhatChanged/
│   │   ├── pages/
│   │   │   ├── ScenarioPage
│   │   │   └── DashboardPage
│   │   ├── api/
│   │   ├── store/
│   │   └── types/
│   └── package.json
│
├── data/
│   ├── demo_scenario.json
│   ├── routes.json
│   ├── resources.json
│   └── assumptions.json
│
├── docs/
│   ├── prd.md
│   └── implementation_plan.md
│
└── README.md
```

Adjust the tree to match the real stack already present in the repository. The names above are the recommended logical boundaries, not claims about the current codebase.

---

# 4. Phase 0: Lock the Demo Scenario

## Objective

Create one fictional scenario that can exercise all major modules.

## Deliverables

- 2-3 candidate routes
- 1 origin node
- 1 destination node
- 1 supply demand profile
- 1-2 resource groups
- baseline environment
- one disruption event
- one connectivity-loss event
- fixed simulation horizon
- fixed seed for deterministic demo playback

## Required scenario data

```text
Origin
Destination
Routes A/B/C
Initial destination stock
Daily demand
Critical stock threshold
Resource capacity
Resource load
Rest hours
Environment values
Route event
Connectivity event
```

## Acceptance test

A new developer can run the scenario without manually inventing missing values.

---

# 5. Phase 1: Shared Scenario Model

## Objective

Build the single source of truth that every module reads.

## Tasks

1. Define typed scenario models.
2. Validate required fields.
3. Add scenario versioning.
4. Add random seed.
5. Add event list.
6. Add assumption ledger.
7. Persist scenario state.

## Minimum entities

- Scenario
- Node
- Route
- Resource
- StockNode
- SupplyTask
- Event
- Assumption
- SimulationRun
- SimulationResult
- SyncRecord

## Acceptance test

Given one scenario JSON, every core engine can consume the same object without custom transformations.

---

# 6. Phase 2: Baseline Route Engine

## Objective

Produce a useful route comparison before adding uncertainty.

## Implementation

Represent each route as a sequence of segments with attributes such as:

```text
segment length
nominal duration
environment friction
availability
simulated disruption factor
```

Calculate baseline metrics:

```text
nominal ETA
nominal distance
resource-feasible yes/no
route score
```

Then add repeated simulation runs where uncertain values are sampled.

## Recommended MVP approach

Use a transparent weighted score plus Monte Carlo variation.

Example concept:

```text
route_cost =
    w_time * travel_time
  + w_disruption * disruption_cost
  + w_environment * environment_cost
  + w_resource * resource_penalty
```

Do not hide the weights from the user.

## Output

```json
{
  "route_id": "B",
  "eta_median_hours": 14.2,
  "eta_p10_hours": 12.8,
  "eta_p90_hours": 17.5,
  "resilience_score": 78,
  "feasible": true,
  "drivers": [
    "lower disruption exposure",
    "higher travel time",
    "better resource fit"
  ]
}
```

Values shown here are examples only.

---

# 7. Phase 3: Supply & Stock Forecasting

This phase directly fixes the missing "so what happens to the people waiting for supplies?" problem.

## 7.1 Inventory State

For every destination node:

```text
current_stock
reserved_stock
daily_consumption
safety_threshold
critical_threshold
scheduled_inbound
```

## 7.2 Time-Step Simulation

For each simulation timestep:

```text
stock[t] = stock[t-1]
          + deliveries[t]
          - consumption[t]
          - losses[t]
```

Delivery only enters stock when the simulated route arrives.

## 7.3 Forecast Outputs

Generate:

- stock curve
- days of supply curve
- minimum stock
- time-to-critical
- projected shortage
- delivery-versus-demand gap

## 7.4 Key Integration

Route engine emits ETA distribution.

Supply engine converts ETA into delivery timing.

Delivery timing changes stock.

Therefore a route event automatically changes forecasted stock.

## Acceptance test

Changing a route event must change the stock forecast without the frontend manually editing inventory values.

---

# 8. Phase 4: Readiness Engine

## Objective

Replace unexplained amber/green/red states with a visible model.

## 8.1 MVP Baseline Model

Use a transparent normalized score instead of a black-box model.

Example structure:

```text
base_capacity_score
- load_penalty
- duration_penalty
- low_rest_penalty
- environmental_penalty
+ capability_adjustment
= readiness_score
```

Clamp to 0-100.

Then map to:

```text
80-100  GREEN
50-79   AMBER
0-49    RED
```

These thresholds should remain configurable and be presented as **simulation thresholds**, not medical truth.

## 8.2 Time-to-Threshold

Simulate readiness over time rather than computing a single static score.

```text
readiness[t] = readiness[t-1] + recovery - workload - stress
```

Then determine:

```text
first time readiness < threshold
```

## 8.3 Integration With Routing

A route becomes infeasible when one or more hard constraints fail.

Example logical check:

```text
if route_duration > resource_supported_duration:
    route_feasible = false
```

This should be a simulation constraint, not a claim about a real unit.

## Acceptance test

Increasing load or reducing rest must change readiness and may alter route feasibility.

---

# 9. Phase 5: Uncertainty Layer

## Objective

Prevent Maya from appearing to produce false precision.

## 9.1 Random Variables

Choose a small number of variables for the first implementation:

- travel time
- disruption delay
- demand rate
- environmental stress
- readiness decay

## 9.2 Sampling

Each Monte Carlo run samples from configured distributions.

Example:

```text
travel_time ~ configured distribution around nominal ETA
demand      ~ configured variation around baseline consumption
delay       ~ configured disruption distribution
```

## 9.3 Summary Statistics

For each key metric compute:

- median
- P10
- P90
- mean where useful
- probability of threshold crossing

## 9.4 UI

Show:

```text
On-time probability: 70%
Likely range: 62-78%

Time-to-critical: Day 4
Likely window: Day 3-Day 5
```

These are presentation examples. Production values must come from the simulation.

## 9.5 Assumption Panel

Every chart should be traceable to its key assumptions.

A user should be able to click:

```text
Why this forecast?
```

and see the assumptions used.

---

# 10. Phase 6: What-If Event Engine

## Objective

Make the simulator dynamic rather than a static dashboard.

## Event types for MVP

```text
ROUTE_DELAY
ROUTE_UNAVAILABLE
ENVIRONMENT_CHANGE
LOAD_CHANGE
REST_CHANGE
DEMAND_CHANGE
CONNECTIVITY_LOSS
REPLICA_LOSS
```

## Event application

A simple event model:

```json
{
  "type": "ROUTE_DELAY",
  "target": "route-B",
  "magnitude": 0.35,
  "start_hour": 8
}
```

## Event lifecycle

```text
Create Event
   ↓
Apply to Scenario
   ↓
Re-run affected simulation
   ↓
Compare Against Baseline
   ↓
Show What Changed
```

## Acceptance test

One button should be sufficient to apply the demo disruption and rerun the scenario.

---

# 11. Phase 7: Offline Data Resilience

## Objective

Make the vague "data resilience" pillar tangible.

## 11.1 Local Store

Use a browser/mobile local persistence layer appropriate to the actual frontend stack.

Minimum locally cached objects:

```text
scenario snapshot
route plan
manifest
stock snapshot
readiness snapshot
sync queue
last known server version
```

## 11.2 Offline Queue

Each user mutation creates an event:

```json
{
  "event_id": "evt-123",
  "entity_id": "manifest-01",
  "entity_version": 7,
  "operation": "UPDATE",
  "payload": {},
  "created_at": "...",
  "sync_status": "PENDING"
}
```

## 11.3 Reconciliation

On reconnect:

```text
Fetch latest server version
        ↓
Compare local queued events
        ↓
Validate versions / signatures
        ↓
Merge non-conflicting changes
        ↓
Flag conflicts
        ↓
Persist reconciled state
        ↓
Mark queue items synced
```

## 11.4 Demo Mode

The cleanest hackathon demo is:

```text
ONLINE
↓
Show manifest / stock snapshot
↓
Toggle OFFLINE
↓
Make local update
↓
Show "1 pending update"
↓
Simulate another replica with a different update
↓
Toggle ONLINE
↓
Run reconciliation
↓
Show merged record + conflict marker
```

If threshold sharing is implemented, show it as a separate technical panel. Do not let cryptographic mechanics obscure the main product story.

## Acceptance test

A local update created while offline remains present after reload and is reconciled when connectivity returns.

---

# 12. Phase 8: Combined Analytics

## Objective

Turn separate module outputs into one decision-support result.

Create a combined result object:

```json
{
  "baseline": {},
  "what_if": {},
  "changes": {
    "route": {},
    "readiness": {},
    "delivery": {},
    "stock": {},
    "data": {}
  },
  "uncertainty": {},
  "assumptions": {}
}
```

## "What Changed?" calculation

Compute a concise diff:

```text
Route: B → C
ETA: +3.1 h
Readiness: 74 → 61
Delivery: +3.1 h
Days of supply: 5.6 → 3.9
Critical date: Day 6 → Day 4
Data state: online → offline / queued
```

Values are generated at runtime.

This panel is likely to become the strongest judge-facing component because it explains causality instead of just displaying charts.

---

# 13. Phase 9: Frontend Implementation

## Screen 1: Scenario Builder

### Layout

```text
LEFT                    CENTER                 RIGHT
Scenario inputs         Route/map view         Scenario summary
Resources               event markers           key constraints
Stock                   route list              assumptions
Environment
```

Primary action:

**RUN SIMULATION**

Secondary action:

**TRIGGER WHAT-IF**

---

## Screen 2: Results Dashboard

Top strip:

```text
Scenario     Status     Simulation Time     Seed
```

Main content:

```text
┌─────────────────────┐  ┌─────────────────────┐
│ Route Comparison    │  │ What Changed?       │
│ A / B / C           │  │ Event → Consequence │
└─────────────────────┘  └─────────────────────┘

┌─────────────────────┐  ┌─────────────────────┐
│ Stock Forecast      │  │ Readiness            │
│ curve + critical    │  │ score + drivers      │
└─────────────────────┘  └─────────────────────┘

┌───────────────────────────────────────────────┐
│ Uncertainty + Assumptions                     │
└───────────────────────────────────────────────┘

┌───────────────────────────────────────────────┐
│ Offline / Reconciliation                      │
└───────────────────────────────────────────────┘
```

### Design rule

Prefer **causal summaries** over decorative charts.

The judge should be able to understand the result in seconds.

---

# 14. API Plan

These endpoints are enough for the MVP.

## Scenarios

```text
POST   /api/scenarios
GET    /api/scenarios/{id}
PUT    /api/scenarios/{id}
POST   /api/scenarios/{id}/clone
```

## Simulation

```text
POST   /api/simulations
GET    /api/simulations/{run_id}
POST   /api/simulations/{run_id}/compare
```

## Events

```text
POST   /api/scenarios/{id}/events
GET    /api/scenarios/{id}/events
```

## Sync

```text
POST   /api/sync/push
POST   /api/sync/reconcile
GET    /api/sync/status/{scenario_id}
```

## Health

```text
GET /api/health
```

---

# 15. Backend Module Contracts

## Routing Engine

Input:

```text
Scenario + routes + resource constraints + uncertainty config
```

Output:

```text
RouteResult[]
```

---

## Readiness Engine

Input:

```text
Resource state + route timeline + environment
```

Output:

```text
ReadinessTimeline + threshold events
```

---

## Supply Forecast Engine

Input:

```text
Stock state + consumption model + delivery timeline
```

Output:

```text
StockTimeline + DoS + time_to_critical + shortage
```

---

## Uncertainty Engine

Input:

```text
base scenario + distributions + random seed
```

Output:

```text
samples + percentile summaries + threshold probabilities
```

---

## Reconciliation Engine

Input:

```text
local events + remote versions + record metadata
```

Output:

```text
reconciled record + conflicts + missing data + audit trail
```

---

# 16. Database / Persistence Plan

A relational database is sufficient for the MVP.

Suggested tables:

```text
scenarios
scenario_versions
nodes
routes
resources
stock_nodes
simulation_runs
route_results
readiness_results
forecast_results
events
assumptions
sync_records
reconciliation_events
```

For the demo, time-series results may be stored as JSON blobs if that simplifies implementation. The logical model matters more than premature schema complexity.

---

# 17. Testing Plan

## Unit Tests

### Routing

- shortest route remains shortest on baseline
- disrupted route changes outcome
- route score changes when disruption parameter changes
- fixed seed produces repeatable output

### Readiness

- higher load lowers readiness
- more rest improves readiness
- longer duration changes threshold time
- environment stress changes score
- threshold labels match configured bands

### Supply Forecast

- stock decreases under demand
- delivery increases stock at arrival time
- later ETA moves stock curve later
- critical date is detected correctly

### Uncertainty

- fixed seed is reproducible
- percentiles are ordered
- threshold probability is between 0 and 1

### Reconciliation

- offline queue persists
- non-conflicting events merge
- conflicting events are flagged
- missing data is visible

---

# 18. Integration Tests

The most important integration test is:

```text
Change Route Delay
      ↓
ETA changes
      ↓
Readiness timeline changes if duration crosses a constraint
      ↓
Delivery time changes
      ↓
Stock forecast changes
      ↓
Time-to-critical changes
      ↓
Dashboard "What Changed?" updates
```

A second test:

```text
Connectivity OFF
      ↓
Local update queued
      ↓
Reload
      ↓
Queue still present
      ↓
Connectivity ON
      ↓
Reconcile
      ↓
Conflict/merge result displayed
```

These two tests prove the heart of Maya.

---

# 19. Performance Plan

The original requirement targets 1,000 simulation runs within an interactive window.

## First implementation

Use a straightforward synchronous simulation to get correctness first.

## Optimization order

1. remove redundant calculations
2. batch sampling
3. vectorize numerical operations where useful
4. parallelize independent runs
5. cache static route/environment calculations
6. move long-running simulations to a background worker if required

Do not optimize before measuring.

Track:

```text
scenario build time
simulation time
number of runs
API response time
dashboard render time
reconciliation time
```

---

# 20. Demo Data Strategy

Use fully synthetic data that has deliberately chosen relationships strong enough to demonstrate the causal chain.

Example relationships:

```text
Route B = longer but more reliable
Route A = faster but more sensitive to disruption
High load = lower readiness
Lower rest = lower readiness
Delayed delivery = lower destination stock
Higher demand = earlier critical date
Connectivity loss = queued local updates
```

Do not hard-code the final result itself.

Hard-code **inputs**, not **answers**.

That distinction is important when judges ask:

> "Did you just program the dashboard to say this?"

The answer should be:

> "The scenario parameters are fixed for reproducibility, but the displayed route, readiness, and forecast results are calculated by the engine."

---

# 21. Demo Script

## 0:00-0:30: Baseline

- Open the scenario.
- Show 3 routes.
- Show current stock and demand.
- Show readiness.
- Show uncertainty and assumptions.

## 0:30-1:00: Ask "What if?"

Trigger one route disruption.

## 1:00-1:45: Maya Re-simulates

Show:

```text
Route ranking changed
ETA changed
Readiness changed
Stock forecast changed
Critical point moved
```

## 1:45-2:15: Offline Event

Toggle connectivity off.

Create a local manifest/status update.

Show pending queue.

## 2:15-2:45: Reconnect

Show reconciliation and any simulated conflict/gap.

## 2:45-3:00: Human Decision

The planner reviews the alternatives and records the preferred simulated option.

Then show the final combined result.

---

# 22. Team Work Division

For a four-member team, the cleanest split is by subsystem with one shared integration owner.

### Member 1: Simulation Core

- scenario model
- event engine
- simulation orchestration
- random seed / repeatability

### Member 2: Predictive Logistics

- route resilience
- supply/stock forecasting
- ETA distribution
- uncertainty metrics

### Member 3: Readiness + Offline Data

- readiness model
- readiness-to-route constraints
- local cache
- offline queue
- reconciliation prototype

### Member 4: Frontend + Integration

- scenario builder
- dashboard
- what-changed view
- API integration
- demo flow / polish

### Shared responsibility

Everyone reviews:

- scenario consistency
- demo reliability
- metric correctness
- documentation
- pitch narrative

---

# 23. Development Checkpoints

## Checkpoint 1

**Scenario loads and saves.**

## Checkpoint 2

**Baseline routes compare correctly.**

## Checkpoint 3

**Supply forecast works independently.**

## Checkpoint 4

**Readiness changes with load/rest/environment.**

## Checkpoint 5

**Route event propagates into stock forecast.**

## Checkpoint 6

**Uncertainty ranges appear in dashboard.**

## Checkpoint 7

**Offline queue and reconciliation work.**

## Checkpoint 8

**Full demo works with one click per major step.**

## Checkpoint 9

**Ghost Convoy demo added only after core is stable.**

---

# 24. Failure Modes and Mitigations

| Failure | Mitigation |
|---|---|
| Route engine is too complex | Start with 2-3 candidate routes and transparent scoring |
| Readiness looks arbitrary | Show formula inputs, score drivers, thresholds |
| Predictive layer is too weak | Forecast stock, delivery timing, and time-to-critical rather than only route ranking |
| Demo values look hard-coded | Use fixed inputs + generated outputs + fixed random seed |
| Uncertainty is confusing | Show only a few key intervals and explain their drivers |
| Offline sync becomes too ambitious | Implement local queue + reconciliation first; keep advanced threshold sharing optional |
| Dashboard becomes crowded | Prioritize "What Changed?" and causal metrics |
| Ghost Convoys consume time | Keep it isolated as P2 |
| Simulation is slow | Profile before optimizing; parallelize repeated runs only after correctness |
| Team merges break integration | Keep shared interfaces stable and run end-to-end test after each merge |

---

# 25. Definition of Done

Maya's MVP is complete when all of the following can be demonstrated in one scenario:

- scenario can be created and saved
- baseline can be simulated
- disruption can be triggered
- routes are re-evaluated
- readiness changes with changed conditions
- delivery timing affects inventory
- stock forecast identifies time-to-critical
- uncertainty and assumptions are visible
- offline update is queued locally
- reconnection reconciles the update
- before/after results are compared
- human planner sees options and records a decision

Ghost Convoys are not required to satisfy the core MVP.

---

# 26. Recommended Build Order for the Team

```text
DAY 1
Scenario schema + demo data + baseline UI

DAY 2
Route engine + results API

DAY 3
Supply/stock forecast + stock chart

DAY 4
Readiness engine + integration

DAY 5
What-if events + before/after diff

DAY 6
Uncertainty + assumptions panel

DAY 7
Offline queue + reconciliation

DAY 8
End-to-end integration + testing

DAY 9
Dashboard polish + judge-facing narrative

DAY 10
Ghost Convoy secondary demo + final hardening
```

Shift the day labels to the actual hackathon schedule. The order is more important than the exact calendar.

---

# 27. Technical Principle to Protect

The single most important implementation rule is:

> **Never let the dashboard become a collection of disconnected numbers. Every visible result should come from the shared scenario and propagate through the simulation chain.**

The strongest Maya demo is not "look at our AI." It is:

```text
Here is the situation.

Here is what changed.

Maya re-simulated the system.

Here is the chain reaction.

Here is the forecast.

Here is the uncertainty.

Here is the recovered data state.

Now the planner can make an informed decision.
```
