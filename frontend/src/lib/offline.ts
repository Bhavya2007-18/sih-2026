import { KINDS, type DataRecord, type LocalState, type Outcome, type Payload, type QueueEntry, type Update } from "./types";

export const STORAGE_KEY = "maya-local-prototype-v1";

function validUnicode(value: string): void {
  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(++i);
      if (!(next >= 0xdc00 && next <= 0xdfff)) throw new Error("Unpaired Unicode surrogate is not UTF-8 compatible.");
    } else if (code >= 0xdc00 && code <= 0xdfff) throw new Error("Unpaired Unicode surrogate is not UTF-8 compatible.");
  }
}

// Python sort_keys=True compares Unicode codepoints, not UTF-16 code units.
function compareKeys(a: string, b: string): number {
  const aa = Array.from(a, c => c.codePointAt(0)!);
  const bb = Array.from(b, c => c.codePointAt(0)!);
  for (let i = 0; i < Math.min(aa.length, bb.length); i++) if (aa[i] !== bb[i]) return aa[i] - bb[i];
  return aa.length - bb.length;
}

/** Exact compact, recursively sorted JSON, matching Python ensure_ascii=False.
 * Direct serialization avoids JS's forced numeric object-key ordering.
 * Protocol restricts numbers to safe finite integers and strings to valid UTF-8.
 */
export function canonical(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "boolean") return String(value);
  if (typeof value === "string") { validUnicode(value); return JSON.stringify(value); }
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value)) throw new Error("Sync numbers must be finite safe integers; no floating point payloads.");
    return String(value);
  }
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (typeof value === "object" && Object.getPrototypeOf(value) === Object.prototype) {
    const obj = value as Record<string, unknown>;
    return `{${Object.keys(obj).sort(compareKeys).map(key => `${canonical(key)}:${canonical(obj[key])}`).join(",")}}`;
  }
  throw new Error("Only plain JSON values are supported by the integrity protocol.");
}

export function parsePayload(text: string): Payload {
  const value: unknown = JSON.parse(text);
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Payload/patch must be a JSON object.");
  for (const item of Object.values(value)) {
    if (item !== null && !["string", "boolean", "number"].includes(typeof item)) throw new Error("Record payload values must be scalar (string, integer, boolean, null).");
  }
  canonical(value); // also validates safe integers and Unicode
  return value as Payload;
}

export async function digest(update: Omit<Update, "payload_hash"> | Update): Promise<string> {
  const { event_id, record_id, device_id, base_version, base_payload, patch, created_at } = update;
  const bytes = new TextEncoder().encode(canonical({ event_id, record_id, device_id, base_version, base_payload, patch, created_at }));
  if (!globalThis.crypto?.subtle) throw new Error("Web Crypto unavailable: use localhost/127.0.0.1 (secure context).");
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, "0")).join("");
}

export async function makeUpdate(record: DataRecord, patch: Payload, deviceId: string): Promise<Update> {
  parsePayload(JSON.stringify(patch));
  if (!Object.keys(patch).length) throw new Error("Patch must change at least one field.");
  const content = {
    event_id: crypto.randomUUID(), record_id: record.id, device_id: deviceId,
    base_version: record.version, base_payload: { ...record.payload }, patch: { ...patch }, created_at: new Date().toISOString(),
  };
  return { ...content, payload_hash: await digest(content) };
}

export const outstanding = (entry: QueueEntry) => !entry.resolvedBy && ["PENDING", "CONFLICT", "INVALID"].includes(entry.status);
export const pendingEntries = (state: LocalState) => state.queue.filter(entry => entry.status === "PENDING" && !entry.resolvedBy);

export function localPayload(state: LocalState, record: DataRecord): Payload {
  return state.queue.filter(entry => entry.update.record_id === record.id && outstanding(entry)).reduce(
    (payload, entry) => ({ ...payload, ...entry.update.patch }), { ...record.payload },
  );
}

export function log(state: LocalState, phase: string, message: string): LocalState {
  return { ...state, journal: [...state.journal, { at: new Date().toISOString(), phase, message }].slice(-80) };
}

export function enqueue(state: LocalState, update: Update): LocalState {
  if (state.queue.some(entry => entry.update.event_id === update.event_id)) throw new Error("Event already exists locally.");
  return log({ ...state, queue: [...state.queue, { update, status: "PENDING" }] }, "localwrite", `Queued ${update.event_id} against v${update.base_version}. Durable local write; not synced.`);
}

export function applyOutcomes(state: LocalState, outcomes: Outcome[]): LocalState {
  let next = { ...state, records: { ...state.records }, queue: [...state.queue] };
  for (const outcome of outcomes) {
    const index = next.queue.findIndex(entry => entry.update.event_id === outcome.event_id);
    if (index < 0) continue;
    const old = next.queue[index];
    // An unresolved conflict is never silently transformed into a successful receipt.
    if (old.status === "CONFLICT" && (outcome.status === "ACCEPTED" || outcome.status === "DUPLICATE")) continue;
    next.queue[index] = { ...old, status: outcome.status, outcome };
    if (outcome.record) {
      const cached = Object.hasOwn(next.records, outcome.record.id) ? next.records[outcome.record.id] : undefined;
      if (!cached || cached.version <= outcome.record.version) next.records[outcome.record.id] = outcome.record;
    }
    next = log(next, outcome.status === "CONFLICT" ? "conflict" : outcome.status === "INVALID" ? "integrity" : "reconcile", `${outcome.event_id}: ${outcome.status}. ${outcome.message}`);
  }
  return next;
}

export function rebase(state: LocalState, originalId: string, resolution: Update): LocalState {
  const original = state.queue.find(entry => entry.update.event_id === originalId);
  if (!original || original.status !== "CONFLICT" || original.resolvedBy) throw new Error("Select an unresolved conflict.");
  if (resolution.event_id === originalId || resolution.record_id !== original.update.record_id) throw new Error("Resolution requires a new event for the same record.");
  const current = state.records[resolution.record_id];
  if (!current || resolution.base_version !== current.version || canonical(resolution.base_payload) !== canonical(current.payload)) throw new Error("Rebase requires the current server snapshot.");
  const next = enqueue(state, resolution);
  return log({ ...next, queue: next.queue.map(entry => entry.update.event_id === originalId ? { ...entry, resolvedBy: resolution.event_id } : entry) }, "reconcile", `Planner rebased ${originalId} into NEW ${resolution.event_id}; original conflict retained as audit, not marked synced.`);
}

export function emptyState(deviceId: string): LocalState {
  return { schema: 1, deviceId, draft: "", scenarios: {}, runs: {}, records: {}, queue: [], decisions: [], comparison: null, activeScenarioId: null, baselineId: null, activeRunId: null, journal: [] };
}

function isObject(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

// Fail closed on a corrupt/foreign store; don't silently replace the user's queue.
export function decodeState(raw: string): LocalState {
  const s: unknown = JSON.parse(raw);
  if (!isObject(s) || s.schema !== 1 || typeof s.deviceId !== "string" || typeof s.draft !== "string" || !isObject(s.scenarios) || !isObject(s.runs) || !isObject(s.records) || !Array.isArray(s.queue) || !Array.isArray(s.decisions) || !Array.isArray(s.journal)) throw new Error("Unrecognized/corrupt local cache. Existing data is preserved; export it before resetting.");
  for (const key of ["baselineId", "activeRunId", "activeScenarioId"]) if (s[key] !== null && typeof s[key] !== "string") throw new Error("Corrupt cached selection.");
  for (const value of Object.values(s.records)) {
    if (!isObject(value) || typeof value.id !== "string" || typeof value.scenario_id !== "string" || !KINDS.includes(value.kind as DataRecord["kind"]) || !Number.isSafeInteger(value.version) || (value.version as number) < 1 || typeof value.updated_at !== "string") throw new Error("Corrupt cached record.");
    parsePayload(JSON.stringify(value.payload));
  }
  for (const entry of s.queue) {
    if (!isObject(entry) || !isObject(entry.update) || !["PENDING", "ACCEPTED", "DUPLICATE", "CONFLICT", "INVALID"].includes(String(entry.status))) throw new Error("Corrupt queue entry.");
    const u = entry.update;
    if (![u.event_id, u.record_id, u.device_id, u.created_at, u.payload_hash].every(v => typeof v === "string") || !Number.isSafeInteger(u.base_version) || (u.base_version as number) < 1 || !/^[a-f0-9]{64}$/.test(String(u.payload_hash))) throw new Error("Corrupt update envelope.");
    parsePayload(JSON.stringify(u.base_payload)); parsePayload(JSON.stringify(u.patch));
  }
  for (const scenario of Object.values(s.scenarios)) if (!isObject(scenario) || typeof scenario.id !== "string" || !Array.isArray(scenario.routes) || !Array.isArray(scenario.stock_nodes) || !Array.isArray(scenario.resources)) throw new Error("Corrupt scenario cache.");
  for (const run of Object.values(s.runs)) if (!isObject(run) || typeof run.run_id !== "string" || !isObject(run.result) || !Array.isArray(run.result.options)) throw new Error("Corrupt run cache.");
  return s as unknown as LocalState;
}
