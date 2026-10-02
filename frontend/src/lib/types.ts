// Mirrors backend/app/models.py. Prediction and comparison calculations stay on the API.
export interface Summary { median: number; p10: number; p90: number }
export interface ScenarioEvent {
  id: string;
  type: "ROUTE_DELAY" | "ROUTE_UNAVAILABLE" | "DEMAND_CHANGE" | "ENVIRONMENT_CHANGE" | "LOAD_CHANGE" | "REST_CHANGE" | "CONNECTIVITY_LOSS" | "CONNECTIVITY_RESTORE";
  target: string; magnitude: number; start_hour: 0;
}
export interface Scenario {
  id: string; name: string; version: number; seed: number; start_time: string;
  horizon_hours: number; step_hours: number; origin: string; destination: string;
  nodes: { id: string; name: string }[];
  routes: { id: string; origin: string; destination: string; capacity: number; environment_stress: number; altitude_stress: number; segments: { id: string; distance_km: number; nominal_hours: number; available?: boolean; time_variation_fraction?: number; disruption_probability?: number; disruption_delay_hours?: number }[] }[];
  resources: { id: string; resource_type: string; capacity: number; load: number; operating_hours: number; rest_hours: number; base_readiness?: number }[];
  stock_nodes: { node_id: string; stock: number; reserved_stock: number; daily_consumption: number; demand_variation_fraction: number; safety_threshold: number; critical_threshold: number; scheduled_inbound: { id: string; quantity: number; departure_hour: number }[] }[];
  events: ScenarioEvent[]; assumptions: string[]; connectivity_online: boolean;
  readiness_config?: Record<string, number>; scoring?: Record<string, number>;
}
export interface Readiness {
  resource_id: string; score: number; state: "GREEN" | "AMBER" | "RED"; feasible: boolean;
  time_to_threshold_hours: number | null; factor_contributions: Record<string, number>;
  timeline: { hour: number; score: number }[];
}
export interface StockForecast {
  node_id: string;
  stock_timeline: { hour: number; stock: Summary; days_of_supply: Summary | null }[];
  minimum_stock: Summary; shortage_quantity: Summary;
  time_to_critical_hours: Summary | null; critical_probability: number; critical_date: string | null;
  time_to_stockout_hours: Summary | null; stockout_probability: number; stockout_date: string | null;
  safety_threshold: number; critical_threshold: number; notes: string[];
}
export interface RouteResult {
  route_id: string; distance_km: number; nominal_hours: number; eta_hours: Summary | null;
  success_probability: number; resilience_score: number; feasible: boolean; score: number; drivers: string[];
}
export interface Option { route: RouteResult; readiness: Readiness[]; supply_forecast: StockForecast[] }
export interface Run {
  run_id: string; created_at: string; scenario: Scenario;
  result: {
    scenario_id: string; seed: number; samples: number; selected_route_id: string | null;
    options: Option[]; route_results: RouteResult[]; readiness_results: Readiness[];
    supply_forecast: StockForecast[]; assumptions: string[]; uncertainty: Record<string, string>;
     data_resilience: Record<string, string | boolean>;
  };
}
export interface Comparison {
  baseline_id: string; what_if_id: string;
  changes: { metric: string; before: string | number | boolean | null; after: string | number | boolean | null; delta: number | null }[];
  explanation: string[];
}
export interface Decision { id: string; run_id: string; route_id: string; note: string; created_at: string }
export const KINDS = ["manifest", "inventory_update", "delivery_status", "resource_status", "scenario_event"] as const;
export type RecordKind = typeof KINDS[number];
export type Scalar = string | number | boolean | null;
export type Payload = Record<string, Scalar>;
export interface DataRecord { id: string; scenario_id: string; kind: RecordKind; version: number; payload: Payload; updated_at: string }
export interface Update {
  event_id: string; record_id: string; device_id: string; base_version: number;
  base_payload: Payload; patch: Payload; payload_hash: string; created_at: string;
}
export interface Outcome {
  event_id: string; status: "ACCEPTED" | "DUPLICATE" | "CONFLICT" | "INVALID";
  record?: DataRecord | null; conflicting_fields: string[]; missing_fields: string[]; message: string;
}
export interface QueueEntry {
  update: Update; status: "PENDING" | Outcome["status"];
  outcome?: Outcome; resolvedBy?: string;
}
export interface LocalState {
  schema: 1; deviceId: string; draft: string;
  scenarios: Record<string, Scenario>; runs: Record<string, Run>; records: Record<string, DataRecord>;
  queue: QueueEntry[]; decisions: Decision[]; comparison: Comparison | null;
  activeScenarioId: string | null; baselineId: string | null; activeRunId: string | null;
  journal: { at: string; phase: string; message: string }[];
}

// Declarative Tool Registry
export interface ToolSpec {
  name: string;
  category: string;
  inputs: string[];
  outputs: string[];
  schema: Record<string, string>;
  availability: "AVAILABLE" | "DEGRADED" | "UNAVAILABLE";
  fallback: string | null;
  version: string;
}

// FactSheet / Evidence Layer
export interface Fact {
  value: string | number | boolean | null;
  unit?: string | null;
  source_tool: string;
  label: string;
}

export interface FactSheet {
  generated_at: string;
  facts: Record<string, Fact>;
  warnings: string[];
  assumptions: string[];
}

// Confidence Assessment
export interface ConfidenceAssessment {
  status: "NOMINAL" | "DEGRADED" | "BLOCKED";
  score: number;
  factors: Record<string, number>;
  cap?: number | null;
  degraded_reasons: string[];
  interpretation: string;
}

// Audit Trace
export interface AuditEntry {
  sequence: number;
  event: string;
  policy_id: string;
  tool_name?: string | null;
  status: "STARTED" | "SUCCESS" | "DEGRADED" | "FAILED" | "RESULT";
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  warnings: string[];
  assumptions: string[];
  at: string;
}

export interface AuditTrace {
  policy_id: string;
  status: "SUCCESS" | "DEGRADED" | "FAILED";
  entries: AuditEntry[];
  warnings: string[];
  assumptions: string[];
}

export interface ToolExecution {
  tool_name: string;
  tool_version: string;
  status: "SUCCESS" | "DEGRADED" | "FAILED";
  started_at: string;
  execution_time_ms: number;
  inputs: Record<string, unknown>;
  outputs: string[];
  warnings: string[];
  assumptions: string[];
  fallback_used: boolean;
}

// Execution Events & Async Job Architecture
export interface ExecutionEvent {
  event:
    | "simulation_queued"
    | "simulation_started"
    | "route_completed"
    | "readiness_completed"
    | "forecast_completed"
    | "uncertainty_completed"
    | "reconciliation_completed"
    | "warning"
    | "result_ready"
    | "simulation_failed";
  at: string;
  status: "QUEUED" | "RUNNING" | "SUCCESS" | "DEGRADED" | "FAILED";
  progress: number;
  tool_name?: string | null;
  message?: string | null;
}

export interface SimulationJob {
  job_id: string;
  scenario_id: string;
  samples: number;
  status: "QUEUED" | "RUNNING" | "SUCCEEDED" | "DEGRADED" | "FAILED";
  progress: number;
  created_at: string;
  updated_at: string;
  run_id?: string | null;
  error?: string | null;
  events: ExecutionEvent[];
}

export interface StructuredToolOutput {
  status: "success" | "degraded" | "failed";
  data: Record<string, unknown>;
  warnings: string[];
  assumptions: string[];
  confidence: Record<string, unknown>;
  execution_time_ms: number;
}
