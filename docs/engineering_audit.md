# MAYA initial engineering audit

Date: 2026-10-02. Audit describes the checkout **before implementation**.
Scope: fictional logistics simulation and human-planner decision support only.

## Executive finding

MAYA currently is a specification repository, not an application or prototype.
Recursive inspection found nine working-tree files: four design documents in
`sources/` and five files in `agent-skills/`. No source modules, package manifests,
database, datasets, executable simulation, tests, CI, or deployment files exist.
Consequently no existing application behavior can be claimed or rewritten.

The intended product is one shared scenario → event → route/readiness/delivery →
stock forecast → uncertainty → combined comparison → planner decision loop.
Offline cache, durable queue and visible reconciliation belong to its demo
acceptance, not a disconnected communications feature. Ghost Convoys are secondary.

## Inspection evidence and file-purpose map

- `sources/prd.md` (803 lines): v0.2 product authority, FR-1–FR-9,
  logical objects, scope restrictions and demo acceptance.
- `sources/implementation_plan.md` (1,299 lines): integrated implementation
  strategy, logical module tree, candidate contracts, testing and demo order.
- `sources/backend.md` (735 lines): proposed FastAPI/Pydantic backend,
  SQLAlchemy/PostgreSQL persistence, engine boundaries and versioned API design.
- `sources/ml_optimization_and_integration_roadmap.md` (860 lines):
  deterministic baselines, Monte Carlo, transparent constraints and optional ML.
- `agent-skills/python-pro.md` (149 lines): applicable Python typing,
  validation, standard-library-first calculation, pytest, ruff and static checks.
- `agent-skills/data-scientist-SKILL.md` (279 lines): applicable assumptions,
  reproducibility, defensible baselines and honest interval interpretation.
- `agent-skills/frontend-engineering-SKILL.md` (68 lines): applicable state
  ownership, API integration, accessibility and loading/error/empty/success states.
- `agent-skills/data-engineering-SKILL.md` (65 lines): applicable integrity,
  idempotency and versioned schema/reconciliation principles; not an ML guide.
- `agent-skills/react-state-management-skills.md` (503 lines): **catalog**,
  not React state-management instructions. Its named skills are not installed here.

All nine files were read in full. Recursive `find` found no additional project
files or AGENTS.md. `git ls-tree -r HEAD` contains only three older documents.
`git show HEAD:<path>` was used to inspect these without restoring deleted files:

- Historical `backend.md`: older network/inventory/ML-first delivery checklist.
- Historical `frontend.md`: Next.js App Router/Tailwind, map-first design and
  operational-style approval language. No corresponding current frontend source.
- Historical `ml_optimization_and_integration_roadmap.md`: older allocation and
  forecasting-first team roadmap.

Working tree initially has those three root documents deleted and `sources/`,
`agent-skills/` untracked. Preserve that user work; do not stage, restore or commit
it automatically. No current README or `sources/frontend.md` exists.

## Capability gap classification

Status vocabulary: IMPLEMENTED = inspected working code; PROTOTYPE = limited
working demonstrator; PARTIALLY IMPLEMENTED = incomplete inspected behavior;
PLANNED = specification exists but no code; MISSING = neither execution nor setup;
BROKEN = inspected code demonstrably fails; UNKNOWN = insufficient evidence.

- Frontend framework: **PLANNED**. No installed framework. Historical design
  specifies Next.js App Router; current documents leave the final choice open.
- Backend framework/API structure: **PLANNED** FastAPI + Pydantic; no endpoints.
- Database: **PLANNED** PostgreSQL + SQLAlchemy/Alembic; no schema or connection.
- Simulation engine: **PLANNED**, independent Python modules and repeated runs.
- ML code: **PLANNED optional**, no training/inference, data or evaluations.
- Shared scenario/data models: **PLANNED**, illustrative JSON only; no validation.
- Routing: **PLANNED**, candidate segment routes, scoring, constraints and sampling.
- Inventory: **PLANNED**, consumption/inbound/reserved stock/threshold semantics.
- Forecasting: **PLANNED**, fixed-demand state transitions before statistical ML.
- Readiness: **PLANNED**, transparent configurable toy model; no calibrated model.
- Uncertainty: **PLANNED**, seeds/assumption ledger/P10–P90; no statistical outputs.
- Offline/reconciliation: **PLANNED**, durable local records/queue/conflict checks.
- Dashboard: **PLANNED**, combined before/after explanation, no components.
- Authentication/security: **MISSING** implementation; user accounts optional in
  backend design. No evidence of existing authentication or secure deployment.
- Test coverage: **MISSING** tests/configuration; coverage percentage undefined,
  not a fabricated zero-percent measurement.
- Deployment: **PLANNED** historical Docker Compose, **MISSING** actual setup/CI.
- Ghost Convoys: **PLANNED** secondary simulation-only capability.
- Existing broken application functionality: **UNKNOWN/not applicable** because
  there is no executable application to reproduce.

Installed tools observed: Python 3.14.4, Node 22.22.1, npm and uv 0.12.10.
These are host tools, not proof of project dependencies or framework installation.

## Conflicts and decisions (not silent architecture changes)

1. **Source locations**: requested root design documents are now in `sources/`.
   Follow their current contents. Keep the original source plan untouched and
   create the requested root `implementation_plan.md` as the live execution plan.
2. **Product scope**: older frontend asks for command-center styling and approval
   calls; current PRD §§3.3, 8 and 12 prohibits autonomous operational execution.
   Follow the PRD: fictional planner options and a recorded simulation decision,
   never deployment/approval of real-world movements.
3. **Priorities**: source plan labels uncertainty/offline P1, but PRD §11 requires
   them in the demo and ML roadmap labels ETA uncertainty P0. Include minimum
   honest uncertainty and durable offline reconciliation in P0 demo acceptance;
   richer statistical inference/peer transport remain P1/P3.
4. **API shape**: source plan uses `/api` and POST compare, backend uses `/api/v1`
   and GET compare. Follow the higher-priority plan's `/api` paths. Actual request
   models will be explicit implementation refinements, not claims of existing APIs.
5. **Scoring visibility**: source plan says show weights; backend says do not expose
   undocumented weights. Resolve with documented configurable weights and driver
   contributions in results. Never duplicate scoring in the UI.
6. **Model naming**: PRD says `stock_states`, backend/plan say stock nodes. Adopt
   `stock_nodes` in a typed, versioned shared schema; do not maintain both variants.
7. **Persistence**: PostgreSQL is recommended, not present. Proposed local
   increment: SQLAlchemy repositories with SQLite as a zero-service demo default
   and configurable PostgreSQL URL/driver. This is a disclosed local-development
   addition, not a claim that PostgreSQL has been installed or tested. Production
   migrations/PostgreSQL integration remain separate acceptance gates.
8. **Routing depth**: initial explicit candidate segment paths implement the
   source plan's small-route baseline; no invented full GIS/topology engine.
   Automated graph-path generation is a later improvement, clearly distinguished
   from candidate route evaluation.

## Highest risks

- No existing integration contract: lock scenario/result units and versioning
  before independent implementations.
- Stock accounting: missed arrival instants, clamping away shortages, or replenishing
  failed routes can create plausible but false forecasts. Test conservation,
  within-step critical crossings, failed delivery and zero-demand semantics.
- Readiness is uncalibrated: disclose coefficients as synthetic toy assumptions;
  never label results clinical or validated resource capabilities.
- False uncertainty: compute sample percentiles/probabilities; distinguish
  conditional ETA from failed deliveries and horizon-censored critical times.
- Event semantics: initially allow at-start events only, explicitly reject
  unsupported future-effective events rather than silently applying them at t=0.
- Reconciliation loss: retain unresolved conflicts; check versions/checksums,
  handle duplicate submissions and persist queue through reload before claiming done.
- Unsupported skill references: reference directories/scripts named in the three
  methodology files are absent. Apply available instructions only; do not claim
  those resources or the catalog's 184 skills were loaded.
- Local no-auth demo must bind to loopback, use no secrets/sensitive data and not
  be advertised as production-secure. Public deployment requires a separate gate.

## Exact methodology used

For the audit/plan: inspected project documents and all installed skill contents;
`omnirush-feature` supplies acceptance-first integration and real-check discipline.
For implementation: `python-pro` for Python; `data-scientist` for stochastic design;
`frontend-engineering` for UI; `data-engineering` for integrity/idempotency.
The catalog is not used as a skill. No FastAPI templates, Next.js patterns,
test-driven-development or code-review-and-quality instruction pack exists here.
Generic advice cannot override the project specification or session model selection.

## Highest-value next work / execution order

1. Save this audit and a live dependency-driven implementation plan.
2. Define validated shared schema, fixed synthetic scenario, seed and run bounds.
3. Parallelize only after contract lock: domain simulator and frontend consumer.
   Integration owner implements persistence/API/reconciliation and verifies both.
4. Route duration → readiness/feasibility → actual inbound → continuous stock
   accounting → aggregated uncertainty → combined baseline/what-if deltas.
5. Drive one web planner flow from those API results; show causal differences,
   assumptions, offline lifecycle and explicit human option selection.
6. Run domain/API/frontend checks and a reproducible full-stack demo. Record
   limitations and unmet acceptance, then defer Ghost Convoys/advanced ML.

This audit is the starting evidence snapshot. Implementation status and actual
verification results belong in root `implementation_plan.md`, not retroactively
relabelled as existing code in this initial audit.
