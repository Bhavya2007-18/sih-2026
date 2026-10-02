"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { api, message } from "@/lib/api";
import type { Comparison, Decision, Run, Scenario, ScenarioEvent } from "@/lib/types";

import AsyncJobPanel from "./async-job-panel";
import AuditTracePanel from "./audit-trace-panel";
import ConfidencePanel from "./confidence-panel";
import FactSheetPanel from "./factsheet-panel";
import ToolRegistryPanel from "./tool-registry-panel";

// MapLibre GL uses a Web Worker that Turbopack/SSR can't resolve.
// dynamic + ssr:false ensures the map module is only loaded in the browser.
const MayaMap = dynamic(() => import("./maya-map"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        height: 380,
        background: "#080e17",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#8796a8",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: "11px",
        letterSpacing: ".08em",
      }}
    >
      INITIALIZING BASEMAP…
    </div>
  ),
});

type View =
  | "overview"
  | "builder"
  | "tools"
  | "evidence"
  | "audit"
  | "confidence"
  | "jobs"
  | "results";

const CACHE_KEY = "maya-command-center-v2";

function number(value: number | null | undefined, digits = 1) {
  return value == null || !Number.isFinite(value)
    ? "—"
    : new Intl.NumberFormat("en", { maximumFractionDigits: digits }).format(value);
}

function percent(value: number | null | undefined) {
  return value == null ? "—" : `${number(value * 100, 0)}%`;
}

function summary(
  value: { median: number; p10: number; p90: number } | null | undefined,
  unit = ""
) {
  if (!value) return "NOT OBSERVED";
  return `${number(value.median)}${unit}  /  P10 ${number(value.p10)} — P90 ${number(value.p90)}`;
}

function routeColor(index: number) {
  return ["#70d7ff", "#4be277", "#ffba61", "#ff7183"][index % 4];
}

export default function MayaCommandCenter() {
  const [view, setView] = useState<View>("overview");
  const [online, setOnline] = useState(true);
  const [health, setHealth] = useState("CHECKING");

  const [cachedData] = useState(() => {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as {
        scenario?: Scenario;
        whatIf?: Scenario;
        baseline?: Run;
        whatIfRun?: Run;
        comparison?: Comparison;
        decision?: Decision;
      };
    } catch {
      localStorage.removeItem(CACHE_KEY);
      return null;
    }
  });

  const [scenario, setScenario] = useState<Scenario | null>(cachedData?.scenario ?? null);
  const [whatIf, setWhatIf] = useState<Scenario | null>(cachedData?.whatIf ?? null);
  const [draft, setDraft] = useState(
    () => (cachedData?.scenario ? JSON.stringify(cachedData.scenario, null, 2) : "")
  );
  const [baseline, setBaseline] = useState<Run | null>(cachedData?.baseline ?? null);
  const [whatIfRun, setWhatIfRun] = useState<Run | null>(cachedData?.whatIfRun ?? null);
  const [comparison, setComparison] = useState<Comparison | null>(cachedData?.comparison ?? null);
  const [decision, setDecision] = useState<Decision | null>(cachedData?.decision ?? null);
  const [samples, setSamples] = useState(200);
  const [cloneId, setCloneId] = useState("maya-what-if");
  const [eventType, setEventType] = useState<ScenarioEvent["type"]>("ROUTE_UNAVAILABLE");
  const [eventTarget, setEventTarget] = useState("");
  const [magnitude, setMagnitude] = useState(24);
  const [decisionRoute, setDecisionRoute] = useState("");
  const [decisionNote, setDecisionNote] = useState("");
  const [unavailableTools, setUnavailableTools] = useState<string[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const active = whatIf ?? scenario;
  const activeRun = whatIfRun ?? baseline;
  const selectedOption =
    activeRun?.result.options.find(
      option => option.route.route_id === (activeRun.result.selected_route_id || decisionRoute)
    ) ?? activeRun?.result.options[0];
  const destinationStock = selectedOption?.supply_forecast.find(
    forecast => forecast.node_id === activeRun?.scenario.destination
  );
  const readiness = selectedOption?.readiness[0];

  const eventTargets = useMemo(() => {
    if (!active) return [];
    if (eventType === "DEMAND_CHANGE") return active.stock_nodes.map(node => node.node_id);
    if (eventType === "LOAD_CHANGE" || eventType === "REST_CHANGE")
      return active.resources.map(resource => resource.id);
    if (eventType === "CONNECTIVITY_LOSS" || eventType === "CONNECTIVITY_RESTORE")
      return [active.id];
    return active.routes.map(route => route.id);
  }, [active, eventType]);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    void api<{ status: string }>("/health")
      .then(result => setHealth(result.status.toUpperCase()))
      .catch(() => setHealth("UNREACHABLE"));
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  useEffect(() => {
    localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ scenario, whatIf, baseline, whatIfRun, comparison, decision })
    );
  }, [scenario, whatIf, baseline, whatIfRun, comparison, decision]);

  const selectedEventTarget = eventTargets.includes(eventTarget)
    ? eventTarget
    : eventTargets[0] ?? "";

  function toggleUnavailableTool(toolName: string) {
    setUnavailableTools(prev =>
      prev.includes(toolName) ? prev.filter(item => item !== toolName) : [...prev, toolName]
    );
  }

  async function action(label: string, callback: () => Promise<void>) {
    if (busy) return;
    if (!online) {
      setError(
        "BACKEND UNAVAILABLE — cached snapshots remain visible, but simulations require reconnection."
      );
      return;
    }
    setBusy(label);
    setError("");
    setNotice("");
    try {
      await callback();
      setNotice(`${label} COMPLETE`);
    } catch (cause) {
      setError(message(cause));
    } finally {
      setBusy("");
    }
  }

  async function loadDemo() {
    await action("DEMO SCENARIO LOADED", async () => {
      const loaded = await api<Scenario>("/demo-scenario");
      setScenario(null);
      setWhatIf(null);
      setBaseline(null);
      setWhatIfRun(null);
      setComparison(null);
      setDecision(null);
      setDraft(JSON.stringify(loaded, null, 2));
      setView("builder");
    });
  }

  async function saveScenario() {
    await action("SCENARIO SAVED", async () => {
      const parsed = JSON.parse(draft) as Scenario;
      const saved = await api<Scenario>("/scenarios", parsed);
      setScenario(saved);
      setWhatIf(null);
      setBaseline(null);
      setWhatIfRun(null);
      setComparison(null);
      setView("builder");
    });
  }

  async function runBaseline() {
    await action("BASELINE RUN STORED", async () => {
      if (!scenario) throw new Error("Save a scenario before running the baseline.");
      const run = await api<Run>("/simulations", { scenario_id: scenario.id, samples });
      setBaseline(run);
      setWhatIfRun(null);
      setComparison(null);
      setView("results");
    });
  }

  async function cloneScenario() {
    await action("WHAT-IF CLONE CREATED", async () => {
      if (!scenario) throw new Error("Save a baseline scenario before cloning.");
      const clone = await api<Scenario>(`/scenarios/${encodeURIComponent(scenario.id)}/clone`, {
        id: cloneId,
        name: `${scenario.name} / WHAT-IF`,
      });
      setWhatIf(clone);
      setDraft(JSON.stringify(clone, null, 2));
      setView("builder");
    });
  }

  async function appendEvent() {
    await action("WHAT-IF EVENT INJECTED", async () => {
      if (!whatIf) throw new Error("Create a what-if clone before injecting an event.");
      const event: ScenarioEvent = {
        id: `event-${crypto.randomUUID()}`,
        type: eventType,
        target: selectedEventTarget,
        magnitude: [
          "ROUTE_UNAVAILABLE",
          "CONNECTIVITY_LOSS",
          "CONNECTIVITY_RESTORE",
        ].includes(eventType)
          ? 0
          : magnitude,
        start_hour: 0,
      };
      const updated = await api<Scenario>(`/scenarios/${encodeURIComponent(whatIf.id)}/events`, {
        expected_version: whatIf.version,
        event,
      });
      setWhatIf(updated);
      setDraft(JSON.stringify(updated, null, 2));
    });
  }

  async function runWhatIf() {
    await action("WHAT-IF COMPARISON STORED", async () => {
      if (!whatIf || !baseline) throw new Error("Create a clone and run a baseline first.");
      const run = await api<Run>("/simulations", { scenario_id: whatIf.id, samples });
      const result = await api<Comparison>(
        `/simulations/${encodeURIComponent(run.run_id)}/compare`,
        { baseline_id: baseline.run_id }
      );
      setWhatIfRun(run);
      setComparison(result);
      setView("results");
    });
  }

  async function recordDecision() {
    await action("PLANNER DECISION RECEIPT STORED", async () => {
      if (!activeRun || !decisionRoute || !decisionNote.trim())
        throw new Error("Choose a feasible route and provide a rationale.");
      const receipt = await api<Decision>("/decisions", {
        run_id: activeRun.run_id,
        route_id: decisionRoute,
        note: decisionNote.trim(),
      });
      setDecision(await api<Decision>(`/decisions/${encodeURIComponent(receipt.id)}`));
    });
  }

  async function loadJobRun(runId: string) {
    try {
      const fetchedRun = await api<Run>(`/simulations/${encodeURIComponent(runId)}`);
      setWhatIfRun(fetchedRun);
      setView("results");
    } catch (err) {
      setError(message(err));
    }
  }

  function navigate(next: View) {
    setView(next);
    document.getElementById(next)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="maya-shell">
      {/* Sidebar Navigation */}
      <aside className="maya-sidebar select-none">
        <div>
          <div className="brand">
            <div className="brand-mark">M</div>
            <div>
              <strong>PROJECT MAYA</strong>
              <span>CONTESTED REPLENISHMENT SIMULATOR</span>
            </div>
          </div>
          <div className="telemetry-label">
            SIMULATION TELEMETRY <b>V3.8-REL</b>
          </div>
          <nav aria-label="Primary navigation">
            <button
              className={view === "overview" ? "nav-item active" : "nav-item"}
              onClick={() => navigate("overview")}
            >
              ▦ <span>Overview</span>
            </button>
            <button
              className={view === "builder" ? "nav-item active" : "nav-item"}
              onClick={() => navigate("builder")}
            >
              ◇ <span>Scenario Builder</span>
            </button>
            <button
              className={view === "tools" ? "nav-item active" : "nav-item"}
              onClick={() => navigate("tools")}
            >
              ⚙ <span>Tool Registry</span>
            </button>
            <button
              className={view === "evidence" ? "nav-item active" : "nav-item"}
              onClick={() => navigate("evidence")}
            >
              📄 <span>FactSheet Evidence</span>
            </button>
            <button
              className={view === "audit" ? "nav-item active" : "nav-item"}
              onClick={() => navigate("audit")}
            >
              📜 <span>Audit Trace</span>
            </button>
            <button
              className={view === "confidence" ? "nav-item active" : "nav-item"}
              onClick={() => navigate("confidence")}
            >
              🛡 <span>Confidence Control</span>
            </button>
            <button
              className={view === "jobs" ? "nav-item active" : "nav-item"}
              onClick={() => navigate("jobs")}
            >
              ⚡ <span>Async Job Runner</span>
            </button>
            <button
              className={view === "results" ? "nav-item active" : "nav-item"}
              onClick={() => navigate("results")}
            >
              ◈ <span>Decision &amp; Results</span>
            </button>
          </nav>
        </div>
        <div className="sidebar-footer">
          <div className="system-card">
            <span>SYS-LINK</span>
            <strong className={online && health === "OK" ? "nominal" : "warning"}>
              ● {online ? health : "OFFLINE"}
            </strong>
            <span>DATA-SEED</span>
            <b>{scenario ? `#${scenario.seed}-SYN` : "#—-SYN"}</b>
          </div>
          <span className="muted-caps">SATQUERY-AI ARCHITECTURE · SEC-LOCAL</span>
        </div>
      </aside>

      {/* Main Content Workspace */}
      <div className="maya-content">
        <header className="maya-header">
          <div className="scenario-chip">
            <span>SCENARIO:</span>
            <b>{active?.name || "NO SCENARIO LOADED"}</b>
          </div>
          <div className="header-status">
            <span className="status-dot" /> SYNTHETIC MODE{" "}
            <span className="header-sync">API: {health}</span>
          </div>
          <div className="header-actions">
            <button
              className="ghost-button"
              onClick={() => setOnline(current => !current)}
              aria-label="Toggle simulated connectivity"
            >
              {online ? "◉ LINK ONLINE" : "○ LINK OFFLINE"}
            </button>
            <button
              className="primary-button"
              disabled={!!busy}
              onClick={() => void (whatIf && baseline ? runWhatIf() : runBaseline())}
            >
              ▶ {busy || (whatIf && baseline ? "RUN WHAT-IF" : "RUN BASELINE")}
            </button>
          </div>
        </header>

        <main>
          {/* Mode Advisory Notice Bar */}
          <div className="advisory">
            <span>● SIMULATION MODE — DECISION SUPPORT</span>
            <em>
              Fictional inputs · backend-generated forecasts · SatQuery-AI policy DAG &amp; tool
              registry · human decision authorization
            </em>
            <b>AIRGAP PARITY: 100%</b>
          </div>

          {/* Sim Pipeline Stepper */}
          <div className="pipeline">
            <span>SIM PIPELINE:</span>
            <b className={scenario ? "complete" : ""}>1. SCENARIO</b>
            <i>→</i>
            <b className={whatIf ? "complete" : ""}>2. WHAT-IF INJECTION</b>
            <i>→</i>
            <b className={whatIfRun ? "complete" : ""}>3. RE-SIM (1,000 RUNS)</b>
            <i>→</i>
            <b className={decision ? "complete" : ""}>4. HUMAN DECISION</b>
          </div>

          {error && (
            <div className="toast error-toast" role="alert">
              ⚠️ {error}
            </div>
          )}
          {notice && (
            <div className="toast success-toast" role="status">
              ✓ {notice}
            </div>
          )}

          {/* VIEW: OVERVIEW */}
          {view === "overview" && (
            <>
              <section id="overview" className="workspace-heading">
                <div>
                  <div className="eyebrow">WORKSPACE // SECTOR-08 · MAYA-SIM-CORE v3.8.4</div>
                  <h1>Logistics Simulation Overview</h1>
                  <p>
                    Evaluate dynamic route, supply degradation, readiness, and connectivity
                    consequences from synthetic scenario inputs.
                  </p>
                </div>
                <div className="heading-actions">
                  <button className="secondary-button" onClick={() => void loadDemo()}>
                    ↓ LOAD DEMO FIXTURE
                  </button>
                  <button className="primary-button" onClick={() => navigate("builder")}>
                    ◇ OPEN BUILDER
                  </button>
                </div>
              </section>

              <section className="kpi-grid" aria-label="Simulation telemetry">
                <Metric
                  label="ACTIVE SCENARIO"
                  value={active?.id || "—"}
                  detail={
                    active?.destination
                      ? `${active.origin} → ${active.destination}`
                      : "Load synthetic fixture"
                  }
                />
                <Metric
                  label="ROUTE RESILIENCE"
                  value={selectedOption ? percent(selectedOption.route.success_probability) : "—"}
                  detail={selectedOption?.route.route_id || "Backend output pending"}
                  tone="cyan"
                />
                <Metric
                  label="DESTINATION STOCK"
                  value={destinationStock ? summary(destinationStock.minimum_stock) : "—"}
                  detail={
                    destinationStock
                      ? `critical ${percent(destinationStock.critical_probability)}`
                      : "Forecast pending"
                  }
                  tone="green"
                />
                <Metric
                  label="READINESS"
                  value={readiness ? `${number(readiness.score, 0)} / 100` : "—"}
                  detail={readiness?.state || "Backend output pending"}
                  tone={readiness?.state === "RED" ? "red" : "amber"}
                />
                <Metric
                  label="DATA LINK"
                  value={online && health === "OK" ? "NOMINAL" : "OFFLINE"}
                  detail="Local proxy · no live link"
                  tone={online && health === "OK" ? "green" : "red"}
                />
              </section>

              <section className="overview-grid">
                <div className="panel map-panel">
                  <PanelHeader code="MAP-01" title="MAYA SCENARIO MAP" />
                  <MayaMap
                    scenarioId={active?.id ?? "demo-ladakh-001"}
                    selectedRouteId={selectedOption?.route.route_id || decisionRoute}
                    onSelectRoute={setDecisionRoute}
                    isOnline={online && health === "OK"}
                  />
                  <div className="map-legend">
                    {(active?.routes ?? []).map((route, index) => (
                      <span
                        key={route.id}
                        onClick={() => setDecisionRoute(route.id)}
                        style={{ cursor: "pointer" }}
                      >
                        <i style={{ background: routeColor(index) }} />
                        {route.id.toUpperCase()}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="panel impact-panel">
                  <PanelHeader code="MOD-04" title="Attribution Differential" />
                  <div className="impact-list">
                    <Impact
                      label="ROUTE"
                      value={selectedOption?.route.route_id || "AWAITING RUN"}
                      detail={
                        selectedOption
                          ? `${summary(selectedOption.route.eta_hours, "h")} ETA`
                          : "Run backend simulation"
                      }
                      color="cyan"
                    />
                    <Impact
                      label="READINESS"
                      value={readiness ? `${number(readiness.score, 0)} / 100` : "—"}
                      detail={readiness?.feasible ? "FEASIBLE" : "Not evaluated"}
                      color="amber"
                    />
                    <Impact
                      label="SUPPLY"
                      value={
                        destinationStock
                          ? summary(destinationStock.time_to_critical_hours, "h")
                          : "—"
                      }
                      detail={
                        destinationStock
                          ? `${percent(destinationStock.stockout_probability)} stockout probability`
                          : "Destination forecast"
                      }
                      color="green"
                    />
                    <Impact
                      label="CONNECTIVITY"
                      value={active?.connectivity_online ? "ONLINE" : "OFFLINE"}
                      detail="Scenario state from API"
                      color={active?.connectivity_online ? "green" : "red"}
                    />
                  </div>
                  <button className="full-button" onClick={() => navigate("results")}>
                    OPEN FULL RESULTS →
                  </button>
                </div>
              </section>
            </>
          )}

          {/* VIEW: SCENARIO BUILDER */}
          {view === "builder" && (
            <section id="builder" className="panel builder-panel">
              <PanelHeader
                code="MODULE: SCENARIO-CONFIG"
                title="Scenario Builder & What-If Sandbox"
              />
              <div className="builder-toolbar">
                <span>
                  Construct synthetic supply environments and inject at-start disruptions. Forecasts are
                  computed by FastAPI under the deterministic policy DAG.
                </span>
                <div className="button-row">
                  <button className="secondary-button" onClick={() => void loadDemo()}>
                    LOAD PRESET
                  </button>
                  <button
                    className="primary-button"
                    disabled={!scenario || !!busy}
                    onClick={() => void runBaseline()}
                  >
                    RUN BASELINE
                  </button>
                </div>
              </div>
              <div className="builder-grid">
                <div className="builder-form">
                  <label>
                    SCENARIO JSON
                    <textarea
                      value={draft}
                      onChange={event => setDraft(event.target.value)}
                      rows={13}
                      spellCheck={false}
                      placeholder="Load the demo fixture or paste a complete Scenario object."
                    />
                  </label>
                  <div className="form-row">
                    <label>
                      MONTE CARLO SAMPLES
                      <input
                        type="number"
                        min="1"
                        max="1000"
                        step="1"
                        value={samples}
                        onChange={event => setSamples(Number(event.target.value))}
                      />
                    </label>
                    <button
                      className="secondary-button save-button"
                      disabled={!draft || !!busy}
                      onClick={() => void saveScenario()}
                    >
                      SAVE SCENARIO TO API
                    </button>
                  </div>
                </div>
                <div className="experiment-card">
                  <div className="card-label">WHAT-IF CONTROL // HOUR 0</div>
                  <label>
                    CLONE ID
                    <input value={cloneId} onChange={event => setCloneId(event.target.value)} />
                  </label>
                  <button
                    className="secondary-button full-button"
                    disabled={!scenario || !!busy}
                    onClick={() => void cloneScenario()}
                  >
                    CLONE BASELINE
                  </button>
                  <div className="divider" />
                  <label>
                    EVENT TYPE
                    <select
                      value={eventType}
                      onChange={event => {
                        const value = event.target.value as ScenarioEvent["type"];
                        setEventType(value);
                        setMagnitude(
                          value === "DEMAND_CHANGE"
                            ? 48
                            : value === "ENVIRONMENT_CHANGE"
                            ? 0.5
                            : value === "ROUTE_DELAY"
                            ? 24
                            : 0
                        );
                      }}
                    >
                      {[
                        "ROUTE_UNAVAILABLE",
                        "ROUTE_DELAY",
                        "DEMAND_CHANGE",
                        "ENVIRONMENT_CHANGE",
                        "LOAD_CHANGE",
                        "REST_CHANGE",
                        "CONNECTIVITY_LOSS",
                        "CONNECTIVITY_RESTORE",
                      ].map(type => (
                        <option key={type}>{type}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    EVENT TARGET
                    <select
                      value={eventTarget}
                      onChange={event => setEventTarget(event.target.value)}
                    >
                      {eventTargets.map(target => (
                        <option key={target}>{target}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    MAGNITUDE
                    <input
                      type="number"
                      min="0"
                      max={eventType === "ENVIRONMENT_CHANGE" ? 1 : undefined}
                      step="any"
                      disabled={[
                        "ROUTE_UNAVAILABLE",
                        "CONNECTIVITY_LOSS",
                        "CONNECTIVITY_RESTORE",
                      ].includes(eventType)}
                      value={magnitude}
                      onChange={event => setMagnitude(Number(event.target.value))}
                    />
                  </label>
                  <div className="button-row">
                    <button
                      className="secondary-button"
                      disabled={!whatIf || !!busy}
                      onClick={() => void appendEvent()}
                    >
                      INJECT EVENT
                    </button>
                    <button
                      className="primary-button"
                      disabled={!whatIf || !baseline || !!busy}
                      onClick={() => void runWhatIf()}
                    >
                      RE-SIMULATE
                    </button>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* VIEW: TOOL REGISTRY */}
          {view === "tools" && (
            <section className="mt-4">
              <ToolRegistryPanel
                unavailableTools={unavailableTools}
                onToggleUnavailable={toggleUnavailableTool}
              />
            </section>
          )}

          {/* VIEW: FACTSHEET EVIDENCE */}
          {view === "evidence" && (
            <section className="mt-4">
              <FactSheetPanel
                factSheet={
                  (
                    activeRun?.result as unknown as {
                      fact_sheet?: import("@/lib/types").FactSheet;
                    }
                  )?.fact_sheet
                }
              />
            </section>
          )}

          {/* VIEW: AUDIT TRACE */}
          {view === "audit" && (
            <section className="mt-4">
              <AuditTracePanel
                auditTrace={
                  (
                    activeRun?.result as unknown as {
                      audit_trace?: import("@/lib/types").AuditTrace;
                    }
                  )?.audit_trace
                }
              />
            </section>
          )}

          {/* VIEW: CONFIDENCE CONTROL */}
          {view === "confidence" && (
            <section className="mt-4">
              <ConfidencePanel
                confidence={
                  (
                    activeRun?.result as unknown as {
                      confidence?: import("@/lib/types").ConfidenceAssessment;
                    }
                  )?.confidence
                }
              />
            </section>
          )}

          {/* VIEW: ASYNC JOB RUNNER */}
          {view === "jobs" && (
            <section className="mt-4">
              <AsyncJobPanel
                scenarioId={active?.id || null}
                onJobCompleted={loadJobRun}
                unavailableTools={unavailableTools}
              />
            </section>
          )}

          {/* VIEW: DECISION & RESULTS */}
          {view === "results" && (
            <section id="results" className="results-section">
              <div className="section-heading">
                <div>
                  <div className="eyebrow">MODULE: DECISION-RESULTS</div>
                  <h2>Backend Forecast &amp; Human Authorization</h2>
                </div>
                <span className="run-id">
                  {activeRun
                    ? `${activeRun.run_id} · ${activeRun.result.samples} SAMPLES`
                    : "NO IMMUTABLE RUN SELECTED"}
                </span>
              </div>
              {activeRun ? (
                <Results
                  run={activeRun}
                  comparison={comparison}
                  decision={decision}
                  decisionRoute={decisionRoute}
                  setDecisionRoute={setDecisionRoute}
                  decisionNote={decisionNote}
                  setDecisionNote={setDecisionNote}
                  onDecision={() => void recordDecision()}
                />
              ) : (
                <div className="empty-state">
                  Run a saved scenario to populate route, readiness, supply, uncertainty, and
                  comparison outputs. This interface never fabricates a forecast.
                </div>
              )}
            </section>
          )}
        </main>
        <footer>
          PROJECT MAYA · SYNTHETIC SIMULATION AND PLANNER ANNOTATION ONLY · SATQUERY-AI
          ARCHITECTURE · API {health}
        </footer>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: string;
  detail: string;
  tone?: string;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function PanelHeader({ code, title }: { code: string; title: string }) {
  return (
    <div className="panel-header">
      <span>{code}</span>
      <h2>{title}</h2>
      <b>● LIVE DATA</b>
    </div>
  );
}

function Impact({
  label,
  value,
  detail,
  color,
}: {
  label: string;
  value: string;
  detail: string;
  color: string;
}) {
  return (
    <div className="impact">
      <span>{label}</span>
      <strong className={color}>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function SyntheticMap({
  routes,
  selected,
}: {
  routes: Scenario["routes"];
  selected?: string;
}) {
  return (
    <div className="synthetic-map">
      <svg viewBox="0 0 760 340" role="img" aria-label="Synthetic route network from origin to destination">
        <defs>
          <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
            <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#243244" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="760" height="340" fill="url(#grid)" />
        <path d="M40 270 Q180 110 350 210 T720 85" fill="none" stroke="#192735" strokeWidth="42" />
        <path d="M40 270 Q190 250 355 115 T720 85" fill="none" stroke="#192735" strokeWidth="26" />
        {routes.map((route, index) => (
          <path
            key={route.id}
            d={
              index === 0
                ? "M80 275 C190 240 290 215 390 185 S585 120 690 75"
                : index === 1
                ? "M80 275 C230 310 290 300 420 270 S590 135 690 75"
                : "M80 275 C170 180 240 105 350 125 S560 225 690 75"
            }
            fill="none"
            stroke={routeColor(index)}
            strokeOpacity={selected && selected !== route.id ? 0.25 : 0.85}
            strokeWidth={selected === route.id ? 5 : 2.5}
            strokeDasharray={index === 2 ? "7 8" : undefined}
          />
        ))}
        <circle cx="80" cy="275" r="10" fill="#70d7ff" />
        <circle cx="690" cy="75" r="11" fill="#4be277" />
        <text x="55" y="310" fill="#9aaaba" fontSize="12">
          ORIGIN
        </text>
        <text x="655" y="55" fill="#9aaaba" fontSize="12">
          DESTINATION
        </text>
      </svg>
      <div className="map-stamp">SYNTHETIC TOPOLOGY // NO LIVE GIS // API ROUTES: {routes.length}</div>
    </div>
  );
}

function Results({
  run,
  comparison,
  decision,
  decisionRoute,
  setDecisionRoute,
  decisionNote,
  setDecisionNote,
  onDecision,
}: {
  run: Run;
  comparison: Comparison | null;
  decision: Decision | null;
  decisionRoute: string;
  setDecisionRoute: (value: string) => void;
  decisionNote: string;
  setDecisionNote: (value: string) => void;
  onDecision: () => void;
}) {
  const feasible = run.result.options.filter(option => option.route.feasible);
  const selected =
    run.result.options.find(
      option => option.route.route_id === run.result.selected_route_id
    ) ?? run.result.options[0];
  return (
    <div className="results-grid">
      <div className="route-results panel">
        <PanelHeader code="MOD-05" title="Candidate Route Outputs" />
        {run.result.options.map((option, index) => (
          <article
            className={`route-output ${
              option.route.route_id === run.result.selected_route_id ? "recommended" : ""
            }`}
            key={option.route.route_id}
          >
            <div>
              <span className="route-index" style={{ color: routeColor(index) }}>
                0{index + 1}
              </span>
              <strong>{option.route.route_id}</strong>
              <small>
                {option.route.feasible ? "FEASIBLE" : "INFEASIBLE"} ·{" "}
                {option.route.drivers[0] || "Backend-scored candidate"}
              </small>
            </div>
            <dl>
              <div>
                <dt>ETA</dt>
                <dd>{summary(option.route.eta_hours, "h")}</dd>
              </div>
              <div>
                <dt>SUCCESS</dt>
                <dd>{percent(option.route.success_probability)}</dd>
              </div>
              <div>
                <dt>SCORE</dt>
                <dd>{number(option.route.score, 3)}</dd>
              </div>
            </dl>
            <button className="inspect-button" onClick={() => setDecisionRoute(option.route.route_id)}>
              CHOOSE
            </button>
          </article>
        ))}
        {!run.result.options.length && (
          <div className="empty-state">No candidate options returned by API.</div>
        )}
      </div>
      <div className="detail-results">
        <div className="panel">
          <PanelHeader code="MOD-06" title="Supply &amp; Readiness Detail" />
          {selected ? (
            <>
              <div className="detail-banner">
                <span>API RECOMMENDATION</span>
                <strong>{run.result.selected_route_id || "NO FEASIBLE ROUTE"}</strong>
              </div>
              {selected.supply_forecast.map(forecast => (
                <div className="forecast" key={forecast.node_id}>
                  <div>
                    <span>{forecast.node_id} · MINIMUM STOCK</span>
                    <strong>{summary(forecast.minimum_stock)}</strong>
                  </div>
                  <div>
                    <span>CRITICAL / STOCKOUT</span>
                    <strong>
                      {percent(forecast.critical_probability)} / {percent(forecast.stockout_probability)}
                    </strong>
                  </div>
                  <div>
                    <span>TIME TO CRITICAL</span>
                    <strong>{summary(forecast.time_to_critical_hours, "h")}</strong>
                  </div>
                </div>
              ))}
              {selected.readiness.map(item => (
                <div className="readiness-row" key={item.resource_id}>
                  <span>{item.resource_id} READINESS</span>
                  <strong>
                    {number(item.score, 0)} / 100 · {item.state}
                  </strong>
                  <div className="readiness-bar">
                    <i style={{ width: `${Math.max(0, Math.min(100, item.score))}%` }} />
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div className="empty-state">No option detail available.</div>
          )}
        </div>
        {comparison && (
          <div className="panel comparison">
            <PanelHeader code="MOD-07" title="Baseline → What-If Differential" />
            <table>
              <thead>
                <tr>
                  <th>METRIC</th>
                  <th>BEFORE</th>
                  <th>AFTER</th>
                  <th>DELTA</th>
                </tr>
              </thead>
              <tbody>
                {comparison.changes.map(change => (
                  <tr key={change.metric}>
                    <th>{change.metric.replaceAll("_", " ")}</th>
                    <td>{String(change.before ?? "—")}</td>
                    <td>{String(change.after ?? "—")}</td>
                    <td
                      className={
                        change.delta != null && change.delta > 0 ? "warning" : "nominal"
                      }
                    >
                      {change.delta == null ? "—" : number(change.delta, 3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <ul>
              {comparison.explanation.map((line, index) => (
                <li key={index}>{line}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="panel decision-panel">
          <PanelHeader code="MOD-08" title="Human Planner Decision" />
          <p>
            Record a feasible simulated option and rationale. This creates an annotation receipt
            only; it never dispatches or executes movement.
          </p>
          <div className="decision-form">
            <label>
              FEASIBLE ROUTE
              <select
                value={decisionRoute}
                onChange={event => setDecisionRoute(event.target.value)}
              >
                <option value="">Select route</option>
                {feasible.map(option => (
                  <option key={option.route.route_id}>{option.route.route_id}</option>
                ))}
              </select>
            </label>
            <label>
              RATIONALE
              <textarea
                rows={3}
                maxLength={1000}
                value={decisionNote}
                onChange={event => setDecisionNote(event.target.value)}
                placeholder="Why does this simulated option fit the planning intent?"
              />
            </label>
            <button
              className="primary-button"
              disabled={!decisionRoute || !decisionNote.trim()}
              onClick={onDecision}
            >
              STORE DECISION RECEIPT
            </button>
          </div>
          {decision && (
            <div className="receipt">
              <strong>✓ RECEIPT {decision.id}</strong>
              <span>
                {decision.route_id} · {decision.created_at}
              </span>
              <p>{decision.note}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
