# Project Maya
## ML, Optimization & Integration Roadmap

**Companion documents:** `prd.md`, `implementation_plan.md`, `backend.md`, `frontend.md`  
**Status:** Hackathon MVP roadmap

---

# 1. Purpose

Maya should be **simulation-first, ML-assisted**, not "AI everywhere".

The strongest technical story is:

```text
DETERMINISTIC CORE
      +
PROBABILISTIC SIMULATION
      +
OPTIONAL ML PREDICTION
      +
OPTIMIZATION
      ↓
EXPLAINABLE DECISION SUPPORT
```

ML should improve prediction where useful, while the core simulator remains understandable, testable, and reproducible.

---

# 2. Priority Map

| Area | MVP priority | Recommended method |
|---|---|---|
| Route simulation | P0 | Graph + Monte Carlo |
| ETA uncertainty | P0 | Probabilistic sampling |
| Stock forecasting | P0 | Simulation + time-series state model |
| Readiness | P0 | Transparent weighted/rule-based model first |
| Constraint optimization | P0/P1 | Weighted objective + feasible-route filtering |
| Assumption ranges | P1 | Parameter distributions |
| ML route prediction | P1 | Train only after baseline exists |
| ML demand forecast | P1 | Classical baseline before ML |
| Anomaly/conflict detection | P1 | Rules first, ML optional |
| Ghost Convoys | P2 | Simulation / optimization module |

Do not delay the end-to-end demo while waiting for a sophisticated ML model.

---

# 3. Core Simulation Mathematics

## 3.1 Route Outcome

For each candidate route, simulate multiple plausible outcomes.

A run can sample:

```text
travel time
segment delay
route availability
environment factor
resource performance factor
```

Then estimate:

```text
successful runs / total runs
```

as a simulated success probability.

The exact formulation should stay in the implementation and be reported honestly in the documentation.

---

# 4. Predictive Supply Layer

This is the most important predictive addition.

The simulator should forecast the future state of stock nodes rather than stopping at route comparison.

## State variables

```text
stock(t)
consumption_rate(t)
inbound_quantity(t)
arrival_time(t)
critical_threshold
```

## Basic state transition

```text
stock(t+Δt)
= stock(t)
+ arrivals(t, t+Δt)
- consumption(t, t+Δt)
```

The model should expose:

```text
days_of_supply
ETA
time_to_critical
projected stock curve
forecast interval
```

This directly connects a route event to a future supply consequence.

---

# 5. Demand Forecasting Roadmap

Start with the simplest baseline that can be measured.

## Level 0: fixed demand

```text
daily demand = configured value
```

Use this for the first integrated simulator.

## Level 1: scenario-varying demand

```text
demand(t) = baseline × demand_factor(t)
```

This allows what-if demand spikes.

## Level 2: statistical forecast

Try simple baselines such as:

- moving average
- exponential smoothing
- seasonal baseline where data supports it

Compare against the fixed-demand baseline.

## Level 3: ML forecast

Only add an ML model when sufficient historical or synthetic training data exists.

Candidate models can include:

```text
Gradient Boosting
Random Forest
XGBoost / LightGBM
Temporal neural model only if justified by data volume
```

For a hackathon, a simple model with an honest evaluation is preferable to a deep model with no validation.

---

# 6. Readiness Model Roadmap

The readiness layer needs an explainable basis before ML.

## MVP formulation

Normalize relevant model inputs:

```text
load_ratio
rest_factor
environment_factor
duration_factor
altitude_factor
```

Then combine them with documented weights or a transparent formula.

Example architecture:

```text
Inputs
  ↓
Normalize
  ↓
Factor scores
  ↓
Weighted readiness index
  ↓
Threshold classification
  ↓
Time-to-threshold estimate
```

The exact coefficients should be treated as project assumptions until validated.

## Why not start with ML?

Because the hackathon judge should be able to ask:

> "Why did readiness become amber?"

and the system should answer directly.

---

# 7. Readiness ML Upgrade

Once baseline logic works, compare it with a trained predictor.

Potential supervised target:

```text
time_to_readiness_threshold
```

Features:

```text
load_ratio
route_duration
rest_hours
environment variables
altitude profile
resource type
```

Candidate models:

```text
Linear Regression baseline
Random Forest Regressor
Gradient Boosting Regressor
```

Evaluate with:

```text
MAE
RMSE
R²
prediction interval coverage, if intervals are implemented
```

Do not replace the baseline unless the ML model actually improves measured performance.

---

# 8. Route Optimization

Separate **simulation** from **optimization**.

Simulation answers:

> What happens if we use this route?

Optimization answers:

> Which feasible options should we examine?

A simple objective can combine normalized metrics:

```text
Objective(route)
= w1 × travel_time
+ w2 × simulated_failure_cost
+ w3 × resource_penalty
+ w4 × stock_criticality_penalty
```

The weights must be configuration, not hidden constants in the frontend.

The planner should be able to inspect the assumptions behind the result.

---

# 9. Constraint Handling

Before optimization, reject routes that violate hard constraints.

Examples:

```text
resource capacity exceeded
route unavailable
arrival beyond simulation horizon
stock requirement impossible under current scenario
```

Then optimize across the remaining feasible candidates.

This prevents the system from producing a mathematically attractive but infeasible result.

---

# 10. Multi-Objective Analysis

For the hackathon, do not build a huge Pareto-front system unless needed.

Show a small set of dimensions:

```text
Time
Resilience
Resource Margin
Supply Impact
Uncertainty
```

A route can be strong on one dimension and weaker on another.

The dashboard should expose those trade-offs instead of hiding them behind one magic score.

---

# 11. Monte Carlo Layer

Use Monte Carlo for uncertainty and disruption simulation.

```text
for i in range(N):
    sample uncertain parameters
    apply scenario events
    simulate route
    simulate resource state
    calculate delivery timing
    update stock state
    record outcomes
```

Aggregate into:

```text
mean
median
percentiles
success probability
arrival range
time-to-critical range
```

A fixed random seed should be available for deterministic hackathon demos.

---

# 12. Uncertainty Reporting

The model should produce intervals where possible.

Example structure:

```text
ETA
54 h
47–63 h expected range

Days of supply
3.8
3.1–4.6 range
```

The exact statistical interpretation should be labelled correctly in the UI. Avoid calling a percentile band a "confidence interval" unless the statistical method actually supports that terminology.

---

# 13. Sensitivity Analysis

Add a small sensitivity module so judges can see what drives the result.

For each major input:

```text
increase / decrease parameter
rerun
measure change in outcome
```

Rank sensitivity by absolute effect on the selected metric.

Example UI:

```text
WHAT DRIVES TIME-TO-CRITICAL?

Travel delay       ██████████
Demand increase    ███████
Readiness loss     ████
Opening stock      ███
```

The values must be generated from actual scenario runs.

---

# 14. Data Reconciliation Logic

Treat reconciliation as a deterministic systems problem first.

## Record model

```text
record_id
entity_id
version
updated_at
device_id
payload_hash
payload
status
```

## Offline queue

```text
LOCAL WRITE
   ↓
append event
   ↓
store locally
   ↓
queue pending sync
```

## Reconnection

```text
exchange pending records
      ↓
validate version / integrity
      ↓
identify duplicate
      ↓
identify conflict
      ↓
merge
      ↓
mark resolved / unresolved
```

For the MVP, the frontend can visualize this using simulated devices rather than requiring physical device deployment.

---

# 15. Reconciliation Conflict Policy

Define deterministic rules before building the UI.

Possible states:

```text
IDENTICAL
NEWER_VERSION
DUPLICATE
CONFLICT
INCOMPLETE
```

For a conflict, do not silently pick a winner. Return:

```text
conflict_id
records_in_conflict
reason
resolution_status
```

The planner can inspect it.

---

# 16. Integration Contract

All modules must communicate through typed domain objects.

```text
Scenario
   ↓
Event Engine
   ↓
RouteResult[]
   ↓
ReadinessResult[]
   ↓
DeliveryForecast[]
   ↓
StockForecast[]
   ↓
UncertaintySummary
   ↓
ReconciliationResult
   ↓
CombinedSimulationResult
```

Avoid a module directly reaching into another module's internal database tables.

---

# 17. Combined Decision Model

The integration layer should not create a hidden autonomous "answer".

Instead produce:

```text
candidate options
trade-offs
forecast consequences
uncertainty
assumptions
```

The frontend then presents these options to the human planner.

Recommended object:

```json
{
  "options": [
    {
      "route_id": "A",
      "eta_range": {},
      "readiness": {},
      "stock_impact": {},
      "uncertainty": {},
      "drivers": []
    }
  ],
  "assumptions": [],
  "comparison": {}
}
```

---

# 18. ML Experiment Structure

Keep experiments separate from production code.

```text
ml/
├── datasets/
├── notebooks/
├── features/
├── training/
├── evaluation/
├── models/
└── reports/
```

Track:

```text
model version
dataset version
feature set
training parameters
metrics
random seed
```

Only promoted models should be callable by the backend.

---

# 19. Synthetic Data Strategy

Because the hackathon system uses synthetic/open scenario data, generate controlled datasets for development.

Create variation across:

```text
route length
travel time
stock levels
consumption
resource load
rest
environment
event severity
```

Ensure the synthetic generator produces edge cases:

```text
very low stock
very high demand
route unavailable
late delivery
insufficient capacity
conflicting offline records
```

The dataset generator should record the assumptions used to create the data.

---

# 20. Evaluation Plan

Every predictive or optimization component needs a baseline.

## Route simulation

Compare against:

```text
fastest-route baseline
```

Measures:

```text
simulated arrival success
ETA
resource feasibility
stock-at-destination outcome
```

## Forecasting

Compare:

```text
naive/fixed baseline
vs
statistical / ML model
```

Measures:

```text
MAE
RMSE
interval coverage where applicable
```

## Readiness

Measure response to controlled changes:

```text
higher load
less rest
longer duration
higher environmental stress
```

## Reconciliation

Test:

```text
0 conflicts
1 conflict
missing replica
duplicate update
out-of-order update
```

---

# 21. Roadmap by Phase

## Phase A: Make the simulation work

```text
Scenario model
Route graph
Monte Carlo
Stock state model
Readiness baseline
Combined result
```

## Phase B: Make it predictive

```text
Time-to-critical
Days-of-supply forecast
ETA range
Assumptions
Sensitivity analysis
```

## Phase C: Make it resilient

```text
Offline local state
Queued updates
Reconnection
Conflict detection
Reconciliation visualization
```

## Phase D: Add ML where it earns its place

```text
Demand model
Readiness model candidate
Prediction benchmarking
Model selection
```

## Phase E: Optimization and polish

```text
Constraint filtering
Multi-objective analysis
Scenario comparison
Performance tuning
```

## Phase F: Secondary capability

```text
Ghost Convoy simulation
```

---

# 22. Recommended Team Division

For a four-person team:

### Member 1: Backend / Simulation Core

Own:

```text
scenario schema
API
simulation orchestration
persistence
```

### Member 2: Routing / Optimization

Own:

```text
route graph
Monte Carlo
scoring
optimization
sensitivity
```

### Member 3: Forecast / ML / Readiness

Own:

```text
stock forecasting
readiness model
uncertainty
ML experiments
```

### Member 4: Frontend / Integration

Own:

```text
scenario UI
dashboard
charts
what-if flow
API integration
```

All members should agree on the shared scenario/result schemas before parallel work begins.

---

# 23. Integration Checkpoints

## Checkpoint 1

```text
Frontend can create scenario
Backend stores it
```

## Checkpoint 2

```text
Scenario runs
Route results return
Dashboard renders them
```

## Checkpoint 3

```text
Event changes scenario
Re-simulation changes outputs
```

## Checkpoint 4

```text
Route change affects ETA
ETA affects stock forecast
```

## Checkpoint 5

```text
Readiness affects route feasibility
```

## Checkpoint 6

```text
Offline event produces queued records
Reconnect produces reconciliation result
```

## Checkpoint 7

```text
Uncertainty + assumptions appear beside forecast
```

## Checkpoint 8

```text
One clean 2-3 minute demo works end-to-end
```

---

# 24. What Not to Build Yet

To protect the hackathon timeline, defer:

```text
complex deep-learning stacks
real-time streaming infrastructure
full GIS production mapping
large-scale distributed simulation
custom mobile mesh hardware
production-grade military integrations
fully autonomous recommendation loops
```

Build the visible causal chain first.

---

# 25. Final Technical Story

The strongest explanation of Maya's architecture is:

> **Maya combines simulation, forecasting and constrained optimization into one what-if engine. A disruption changes the simulated route; the changed delivery timing propagates into resource readiness and destination stock; uncertainty shows the range of possible outcomes; and the offline layer demonstrates how logistics records remain recoverable and reconcilable when connectivity is interrupted. The planner reviews the resulting options and makes the final decision.**

That is the technical spine of the product.
