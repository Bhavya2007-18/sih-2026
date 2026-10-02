# PRD: Project Maya
## Predictive Logistics Simulation & Decision-Support Platform

**Version:** 0.2  
**Date:** October 2026  
**Status:** Hackathon MVP specification

---

## 1. Product Summary

Project Maya is a simulation and decision-support platform for resilient logistics in disrupted environments.

Maya gives a planner a single **what-if workflow**:

```text
SCENARIO
   ↓
WHAT-IF EVENT
   ↓
RE-SIMULATE
   ↓
FORECAST
   ↓
COMBINED DASHBOARD
   ↓
PLANNER DECIDES
```

The platform combines five tightly connected capabilities:

1. **Route Resilience**: evaluates candidate routes under changing simulated conditions.
2. **Resource Readiness**: estimates whether the selected resources can complete the simulated movement.
3. **Supply & Stock Forecasting**: predicts inventory depletion, days of supply, delivery timing, and critical-stock events.
4. **Data Resilience**: keeps simulated logistics records available and reconcilable during connectivity loss.
5. **Ghost Convoys**: optional simulation capability for comparing real and decoy movement patterns.

Maya is a **decision-support simulator, not an autonomous command system**. The human planner remains responsible for interpreting the result and choosing an action.

All scenarios and outputs are synthetic/simulated for the hackathon.

---

## 2. Problem Statement

Conventional logistics planning can perform well under stable assumptions but becomes harder to reason about when several factors change at once.

### 2.1 Current Gaps

- **Expected-case routing**: a route may be fast on paper but fragile when a segment becomes unavailable or environmental conditions change.
- **Static resource assumptions**: available resources are often treated as constant rather than changing with load, fatigue, environment, and journey duration.
- **No end-to-end supply consequence**: route quality is not enough. The planner also needs to know whether stock at the destination becomes critical before the delivery arrives.
- **Connectivity dependency**: when devices lose connection, local records can diverge from each other and from the central view.
- **Separated analysis**: routing, readiness, supply status, and data continuity are often viewed independently, hiding interactions between them.
- **Limited predictive context**: a simulation that only says "Route B is better" does not show what happens next to inventory and readiness over time.

### 2.2 Maya's Core Question

> **If this happens, what changes next, how quickly does it matter, and what options does the planner have?**

Maya answers this through repeated what-if simulation and forward forecasting.

---

## 3. Goals

### 3.1 Primary Goals

1. Simulate a logistics scenario and compare multiple candidate routes under changing conditions.
2. Quantify route resilience rather than using distance/time alone.
3. Model resource readiness as a changing constraint on feasible delivery.
4. Model destination stock and consumption so route outcomes connect to supply consequences.
5. Forecast **days of supply, projected stock level, delivery timing, and time-to-critical** for key nodes.
6. Represent uncertainty and assumptions explicitly instead of presenting one overconfident number.
7. Demonstrate offline data continuity through local caching, queued updates, and later reconciliation.
8. Produce one dashboard that lets a human planner compare scenario outcomes and decide what to do.

### 3.2 Hackathon MVP Goal

A judge should be able to watch one scenario move through this chain in a few minutes:

```text
Set Scenario
    ↓
Run Baseline
    ↓
Trigger Disruption
    ↓
Re-run Simulation
    ↓
See Route Change
    ↓
See Readiness Impact
    ↓
See Stock Forecast Change
    ↓
See Offline Data Gap + Reconciliation
    ↓
Compare Options
```

### 3.3 Non-Goals for v1

- Live command and control.
- Live operational military feeds.
- Classified data integration.
- Autonomous execution of logistics decisions.
- Medical diagnosis or clinical decision-making.
- Production-grade electronic-warfare or communications operations.
- Replacing ERP, inventory, fleet-management, or enterprise systems.

---

## 4. Target Users

| User | Primary need |
|---|---|
| Logistics planner / analyst | Build scenarios, compare options, understand future supply impact |
| Exercise / wargame analyst | Run what-if cases and compare resilience |
| Readiness analyst | Understand how resource condition constrains a plan |
| Field user in the simulation | View locally cached plans, manifests, and status while offline |
| Hackathon judge | Quickly understand the problem, mechanism, and measurable result |

---

## 5. Core Product Experience

### 5.1 Scenario Builder

The planner creates a synthetic logistics scenario.

**Inputs:**

- origin and destination nodes
- candidate routes
- route distance / estimated travel time
- resource groups assigned to movement
- carried load / capacity
- opening stock at destination
- expected daily consumption
- safety-stock / critical-stock threshold
- environmental conditions
- planned rest / operating pattern
- simulated disruption events
- communication availability state
- simulation horizon

The scenario is stored as a single shared object used by every module.

### 5.2 What-If Event Engine

The user can introduce a change such as:

- route segment becomes unavailable
- travel time increases
- environmental stress rises
- available readiness falls
- load changes
- consumption rate increases
- communication becomes unavailable
- one or more local data replicas become unavailable

The event engine updates the scenario and requests a new simulation run.

### 5.3 Re-Simulation

Maya reruns the affected portions of the scenario and propagates the consequences through:

```text
EVENT
 ↓
ROUTE
 ↓
ETA / DELIVERY TIMING
 ↓
RESOURCE READINESS
 ↓
INBOUND SUPPLY
 ↓
DESTINATION STOCK
 ↓
FORECASTED CRITICAL POINT
 ↓
COMBINED RESULT
```

This propagation chain is the core differentiator of the MVP.

---

# 6. Functional Requirements

## FR-1 Scenario Management

**FR-1.1** The system shall allow a planner to create, save, load, clone, and reset a simulation scenario.

**FR-1.2** A scenario shall contain nodes, routes, resources, supply state, environmental conditions, disruption events, and connectivity state.

**FR-1.3** Every simulation result shall retain a reference to the exact scenario assumptions used to produce it.

**FR-1.4** The planner shall be able to compare a baseline scenario against one or more what-if scenarios.

---

## FR-2 Route Resilience Engine

**FR-2.1** The system shall evaluate multiple candidate routes for the same origin/destination task.

**FR-2.2** The engine shall consider at minimum:

- route length / travel time
- route disruption probability or scenario availability
- environmental friction
- simulated route risk/cost
- resource constraints
- uncertainty

**FR-2.3** The system shall run repeated simulations for each candidate route rather than relying on a single deterministic outcome.

**FR-2.4** The engine shall produce, per route:

- estimated arrival time distribution
- route resilience / feasibility score
- disruption count or exposure summary
- fuel/capacity feasibility
- explanation of major score drivers

**FR-2.5** When an event changes a route, the system shall show the before/after route result rather than only a "blocked" state.

**FR-2.6** The UI shall clearly separate **distance/time** from **resilience/feasibility** so the planner can see the trade-off.

---

## FR-3 Resource Readiness Predictor

### 3.1 Readiness Basis

The MVP shall avoid hard-coded colors without explanation.

For each simulated resource group, readiness shall be based on explicit model inputs and a transparent scoring function.

Example demo baseline:

```text
Readiness = f(
    available_capacity,
    route_duration,
    load_ratio,
    cumulative_workload,
    rest_available,
    temperature_stress,
    altitude_stress,
    resource_type
)
```

The exact function shall be configurable and shown in the technical documentation.

### 3.2 Minimum MVP Inputs

- resource type
- nominal capacity
- current load
- route duration
- cumulative operating time
- rest duration
- temperature stress index
- elevation/altitude stress index
- optional configurable resource-specific capability factors

### 3.3 Minimum MVP Outputs

- readiness score, 0-100
- state: Green / Amber / Red
- time-to-threshold estimate
- limiting factors
- route feasibility flag

### 3.4 Explainability Requirement

Every readiness result shall answer:

> **Why did readiness change?**

Example:

```text
Readiness: 61 / 100  → AMBER
Main drivers:
- High load ratio
- Long travel duration
- Low planned rest
- Increased environmental stress
```

The example is illustrative, not a validated physiological prediction.

---

## FR-4 Supply, Stock and Forecasting Engine

This is the predictive layer that connects logistics movement to supply consequences.

### 4.1 Supply State

Each logistics node shall track:

- current stock
- reserved stock
- inbound quantity
- daily consumption rate
- safety-stock threshold
- critical-stock threshold
- replenishment events
- projected delivery time

### 4.2 Core Calculations

At simulation step `t`:

```text
Ending Stock(t)
= Opening Stock(t)
+ Delivered Supply(t)
- Forecast Consumption(t)
- Simulated Losses(t)
```

Days of supply:

```text
DoS(t) = Usable Stock(t) / Forecast Daily Consumption(t)
```

Criticality:

```text
Critical when Projected Stock(t) <= Critical Threshold
```

### 4.3 Predictive Outputs

The engine shall forecast:

- stock level over the simulation horizon
- days of supply
- projected delivery time
- time-to-critical
- expected shortage quantity, if any
- minimum stock reached during the scenario
- effect of the disruption on stock

### 4.4 Required Judge-Facing Output

The dashboard shall be able to show a statement such as:

```text
BASELINE
Destination stock remains above critical threshold.

WHAT-IF: Route disruption
Projected delivery shifts later.
Days of supply decrease.
Post becomes critical before replenishment arrives.
```

The actual values must come from the current simulation run and must never be hard-coded in the final demo build.

---

## FR-5 Predictive Uncertainty and Assumptions

Maya shall avoid presenting simulation outputs as exact facts.

### 5.1 Assumption Ledger

Every run shall record the assumptions that materially affect the result.

Examples:

- demand rate
- route travel-time distribution
- disruption probability
- resource capacity
- readiness parameters
- stock thresholds
- simulation horizon

### 5.2 Ranges Instead of Single Numbers

Where the engine samples uncertain inputs, the UI shall present a range or percentile interval.

Example format:

```text
Estimated on-time probability: 70%
Likely range: 62-78%

Primary uncertainty:
Travel-time variation under disruption
```

The values above are example presentation values only.

### 5.3 Scenario Confidence

Maya shall display:

- median / expected value
- lower and upper percentile or confidence range
- major uncertainty drivers
- assumptions used

The UI shall not describe simulated probability as guaranteed real-world probability.

---

## FR-6 Offline Data Resilience

The MVP shall demonstrate a concrete and inspectable offline workflow.

### 6.1 Records Cached Locally

At minimum, the local simulation/field client shall cache:

- scenario identifier and version
- route plan / route status
- manifest
- stock snapshot
- readiness snapshot
- pending updates
- audit/event timestamps

### 6.2 Offline Queue

When connectivity is unavailable:

1. new user actions are written to the local store
2. a pending event is added to an outbound queue
3. the UI displays an **Offline** state
4. the local user can continue using cached data
5. updates remain queued until reconnection

### 6.3 Reconciliation on Reconnection

When connectivity returns:

1. queued updates are discovered
2. records are validated
3. non-conflicting updates are merged
4. conflicting updates are flagged
5. the system produces one reconciled record with an audit trail

For the hackathon, the data-resilience demo may simulate fractional record storage across multiple clients. The implementation shall clearly identify which parts are real prototype behavior and which parts are simulated.

### 6.4 Conflict Visibility

A reconciliation result shall show:

- complete fields
- missing fields
- conflicting fields
- source/version of each update
- final merged state

The objective is **continuity and trustworthy reconstruction**, not covert communication.

---

## FR-7 Combined Decision View

The dashboard shall combine module outputs instead of showing three unrelated panels.

### Required panels

1. **Scenario summary**
2. **Route comparison**
3. **Readiness**
4. **Stock forecast**
5. **Uncertainty & assumptions**
6. **Offline/reconciliation status**
7. **Before vs. after what-if comparison**

### Required question answered by the UI

> **What changed because of the event?**

The dashboard should surface a concise chain:

```text
Event
→ Route ETA changed
→ Readiness changed
→ Delivery timing changed
→ Stock forecast changed
→ Critical point moved
```

---

## FR-8 Human-in-the-Loop Decision Support

**FR-8.1** Maya shall present ranked/compared options and their assumptions.

**FR-8.2** Maya shall not autonomously execute a logistics plan.

**FR-8.3** Every final action is selected by the human planner.

**FR-8.4** The UI shall distinguish **simulation result** from **planner decision**.

---

## FR-9 Ghost Convoys

Ghost Convoys remain a secondary, showcase capability.

**FR-9.1** The system may generate simulated decoy movement schedules paired with a scenario.

**FR-9.2** The system shall evaluate them only inside the simulation environment.

**FR-9.3** Ghost Convoys shall not block or delay completion of the core predictive logistics flow.

If time is limited, Ghost Convoys may be implemented as a playback/comparison module using synthetic movement patterns rather than a full generative system.

---

# 7. System Architecture

```text
┌──────────────────────────────┐
│        Planner UI             │
│ Scenario Builder + Dashboard  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│        Maya API Layer         │
│ Scenario / Simulation / Sync  │
└──────────────┬───────────────┘
               │
               ▼
┌───────────────────────────────────────────┐
│           Shared Scenario Engine           │
├───────────────────────────────────────────┤
│  Event Engine                              │
│      ↓                                     │
│  Route Resilience Engine                   │
│      ↓                                     │
│  Readiness Engine                          │
│      ↓                                     │
│  Supply + Stock Forecast Engine            │
│      ↓                                     │
│  Data Resilience / Reconciliation          │
└──────────────────────┬────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────┐
│            Forecast + Analytics             │
│  baseline vs what-if + uncertainty         │
└──────────────────────┬────────────────────┘
                       │
                       ▼
               ┌──────────────┐
               │  Dashboard   │
               │ Decision Aid │
               └──────────────┘

Optional / secondary:
Ghost Convoy Simulation
```

---

## 8. Logical Data Model

### Scenario

```json
{
  "id": "scenario-001",
  "origin": "node-a",
  "destination": "node-b",
  "horizon_hours": 120,
  "routes": [],
  "resources": [],
  "stock_states": [],
  "events": [],
  "assumptions": {},
  "connectivity": {}
}
```

### Route

```json
{
  "id": "route-a",
  "distance_km": 0,
  "nominal_time_hours": 0,
  "risk_factors": [],
  "environment_factors": [],
  "available": true
}
```

### Resource State

```json
{
  "resource_id": "resource-01",
  "type": "vehicle_or_transport_unit",
  "capacity": 0,
  "load": 0,
  "rest_hours": 0,
  "operating_hours": 0,
  "environment_stress": 0
}
```

### Stock Node

```json
{
  "node_id": "post-b",
  "stock": 0,
  "daily_consumption": 0,
  "safety_threshold": 0,
  "critical_threshold": 0,
  "scheduled_inbound": []
}
```

### Simulation Result

```json
{
  "scenario_id": "scenario-001",
  "run_id": "run-001",
  "route_results": [],
  "readiness_results": [],
  "forecast_results": [],
  "data_resilience": {},
  "assumptions": {},
  "uncertainty": {}
}
```

---

## 9. Non-Functional Requirements

| Area | MVP requirement |
|---|---|
| Performance | Typical demo simulation completes in an interactive time window; target under 60 seconds for 1,000 route simulation runs |
| Explainability | Every major score/alert shows top contributing factors |
| Reproducibility | A run can be repeated from the same scenario seed and assumptions |
| Uncertainty | Variable inputs can be sampled and summarized as ranges |
| Offline | Cached scenario/manifest/status remain readable without connection |
| Recovery | Queued changes survive app reload during offline mode |
| Integrity | Reconciliation validates record versions / signatures or equivalent prototype checks |
| Usability | Core workflow should be understandable without a technical operator |
| Auditability | Scenario, event, result, and reconciliation actions are timestamped |

---

## 10. Evaluation Metrics

The hackathon demo should report real measured values generated by the current build.

### Routing

- survival/resilience metric vs fastest-route baseline
- route ETA distribution
- route rerouting response after disruption

### Readiness

- response to increased load
- response to longer duration
- response to environmental stress
- lead time before readiness threshold

### Supply Forecasting

- stock forecast error on synthetic test data
- correct identification of time-to-critical
- shortage quantity estimation
- difference between baseline and disrupted scenario

### Data Resilience

- percentage of records recovered
- reconstruction success under simulated replica loss
- number of conflicts correctly detected
- time to reconcile after reconnection

### Integration

- whether a route change propagates to ETA, readiness, and stock forecast
- end-to-end runtime
- repeatability across fixed random seeds

---

## 11. Demo Acceptance Criteria

The MVP is considered demo-ready when a fresh run can show all of the following:

### A. Baseline

- scenario loads
- route options are visible
- stock forecast is visible
- readiness is visible
- assumptions are visible

### B. What-If Event

- user triggers one disruption
- simulation reruns
- at least one route changes in rank or feasibility

### C. Predictive Result

- ETA changes
- stock curve changes
- days of supply changes
- projected critical point moves

### D. Readiness Result

- readiness changes from its prior state when an input changes
- UI shows the underlying factors

### E. Uncertainty

- dashboard shows a range/percentile, not only one number
- assumptions can be inspected

### F. Offline Data Result

- connectivity can be toggled off in the demo
- a local update is created and queued
- reconnect triggers reconciliation
- final record shows complete/partial/conflicting fields

### G. Human Decision

- dashboard presents the options
- planner explicitly selects or records the preferred simulated option

---

## 12. Safety / Scope Boundary

Project Maya is an academic and hackathon simulation.

The software should use fictional entities, synthetic data, and configurable toy scenarios for demonstration. It is not presented as an operational military planning, targeting, deployment, medical, or communications-control system.

---

## 13. Future Scope

- richer demand forecasting models
- calibrated route-time and readiness models using approved public research data
- scenario libraries and replay
- richer mobile offline experience
- more robust reconciliation tests
- advanced analytics and report export
- optional ML models where they materially outperform transparent baselines
- additional simulated logistics assets and constraints

---

## 14. Open Questions

1. Which synthetic scenario will be the final demo scenario?
2. Which inventory classes will be modeled in the MVP?
3. Which readiness parameters will be configurable in the final UI?
4. What random-distribution assumptions will be used for route time and disruption?
5. Which offline transport mechanism will be demonstrated, if any, beyond simulated local peer exchange?
6. Which exact framework/library choices will be locked before implementation?

---

## 15. Definition of Done

Maya v0.2 is complete when one scenario can be run from start to finish and the user can visibly trace:

```text
Scenario
→ What-If Event
→ Route Result
→ Readiness Result
→ Delivery Timing
→ Stock Forecast
→ Uncertainty
→ Offline Data State
→ Reconciled Record
→ Planner Decision
```

Ghost Convoys are optional to the core definition of done.
