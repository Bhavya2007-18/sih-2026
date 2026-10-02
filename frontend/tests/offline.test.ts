import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { test } from "node:test";
import { applyOutcomes, canonical, decodeState, digest, emptyState, enqueue, localPayload, makeUpdate, outstanding, parsePayload, pendingEntries, rebase } from "../src/lib/offline";
import type { DataRecord, Outcome } from "../src/lib/types";

const record: DataRecord = { id: "r-1", scenario_id: "demo", kind: "inventory_update", version: 1, payload: { node_id: "lake", stock: 50, note: "initial" }, updated_at: "2026-10-02T00:00:00Z" };
function initial() { return { ...emptyState("device-a"), records: { [record.id]: record } }; }

test("canonical recursive key sorting preserves integer-like keys and UTF-8, matches Python bytes/hash", async () => {
  const u = {
    event_id: "event-a", record_id: "r-1", device_id: "device-a", base_version: 1,
    base_payload: { "2": "two", "10": "ten", "\u{10000}": "supplementary", "\ue000": "BMP", note: "café 湖\n\"", stock: 50, node_id: "lake" },
    patch: { note: "Été", stock: 42, flag: true, nothing: null }, created_at: "2026-10-02T00:00:00Z",
  };
  const input = JSON.stringify(u);
  const python = execFileSync("python3", ["-c", "import sys,json,hashlib; x=json.loads(sys.stdin.read()); s=json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False); print(s); print(hashlib.sha256(s.encode('utf-8')).hexdigest())"], { input, encoding: "utf8" }).trimEnd().split("\n");
  assert.equal(canonical(u), python[0]);
  assert.equal(await digest(u), python[1]);
  assert.equal(canonical({ z: [{ b: 2, a: 1 }], a: 0 }), '{"a":0,"z":[{"a":1,"b":2}]}');
});

test("unsafe/floating/non-scalar payloads and malformed Unicode rejected", () => {
  for (const text of ['{"stock":1.5}', '{"stock":9007199254740992}', '{"stock":{}}', '[]']) assert.throws(() => parsePayload(text));
  assert.throws(() => canonical(NaN)); assert.throws(() => canonical("\ud800"));
  assert.deepEqual(parsePayload('{"stock":42,"note":"café","flag":true,"empty":null}'), { stock: 42, note: "café", flag: true, empty: null });
});

test("offline localwrite survives JSON reload with base/version/hash and local overlay", async () => {
  const update = await makeUpdate(record, { stock: 42 }, "device-a");
  const before = enqueue(initial(), update);
  const restored = decodeState(JSON.stringify(before));
  assert.equal(pendingEntries(restored).length, 1);
  assert.deepEqual(localPayload(restored, record), { ...record.payload, stock: 42 });
  assert.equal(restored.records[record.id].payload.stock, 50);
  assert.equal(restored.queue[0].update.base_version, 1);
  assert.equal(restored.queue[0].update.payload_hash, await digest(update));
  assert.equal(restored.journal.at(-1)?.phase, "localwrite");
});

test("accepted field merge preserves concurrent independent fields and duplicate receipt is safe", async () => {
  const update = await makeUpdate(record, { stock: 42 }, "device-a");
  const current = { ...record, version: 3, payload: { ...record.payload, stock: 42, note: "other replica" } };
  const accepted: Outcome = { event_id: update.event_id, status: "ACCEPTED", record: current, conflicting_fields: [], missing_fields: [], message: "Merged" };
  const merged = applyOutcomes(enqueue(initial(), update), [accepted]);
  assert.equal(pendingEntries(merged).length, 0);
  assert.equal(merged.records[record.id].payload.note, "other replica");
  const duplicate = applyOutcomes(merged, [{ ...accepted, status: "DUPLICATE" }]);
  assert.equal(duplicate.queue.length, 1);
  assert.equal(duplicate.queue[0].status, "DUPLICATE");
});

test("conflict remains queued after reload; resolution is a new event/current base, audit retained", async () => {
  const update = await makeUpdate(record, { stock: 42 }, "device-a");
  const server = { ...record, version: 2, payload: { ...record.payload, stock: 39 } };
  const outcome: Outcome = { event_id: update.event_id, status: "CONFLICT", record: server, conflicting_fields: ["stock"], missing_fields: [], message: "Changed by other replica" };
  const conflicted = decodeState(JSON.stringify(applyOutcomes(enqueue(initial(), update), [outcome])));
  assert.equal(conflicted.queue.filter(outstanding).length, 1);
  assert.equal(pendingEntries(conflicted).length, 0);
  const forgedWinner = applyOutcomes(conflicted, [{ ...outcome, status: "ACCEPTED" }]);
  assert.equal(forgedWinner.queue[0].status, "CONFLICT");
  const resolution = await makeUpdate(server, { stock: 41 }, "device-a");
  const rebased = rebase(conflicted, update.event_id, resolution);
  assert.equal(rebased.queue[0].status, "CONFLICT");
  assert.equal(rebased.queue[0].resolvedBy, resolution.event_id);
  assert.equal(rebased.queue[1].status, "PENDING");
  assert.equal(rebased.queue[1].update.base_payload.stock, 39);
  assert.equal(rebased.queue.filter(outstanding).length, 1);
  const accepted = applyOutcomes(rebased, [{ ...outcome, event_id: resolution.event_id, status: "ACCEPTED", record: { ...server, version: 3, payload: { ...server.payload, stock: 41 } } }]);
  assert.equal(accepted.queue.filter(outstanding).length, 0);
  assert.equal(accepted.queue[0].status, "CONFLICT");
  assert.throws(() => rebase(conflicted, update.event_id, { ...resolution, base_version: 1 }));
});

test("tampered updates detect hash mismatch and INVALID stays outstanding", async () => {
  const update = await makeUpdate(record, { stock: 42 }, "device-a");
  const tampered = { ...update, patch: { stock: 99 } };
  assert.notEqual(tampered.payload_hash, await digest(tampered));
  const invalid = applyOutcomes(enqueue(initial(), tampered), [{ event_id: update.event_id, status: "INVALID", conflicting_fields: [], missing_fields: [], message: "Integrity mismatch" }]);
  assert.equal(invalid.queue.filter(outstanding).length, 1);
  assert.equal(decodeState(JSON.stringify(invalid)).queue[0].status, "INVALID");
});

test("foreign/broken cache fails closed without discarding queue", () => {
  assert.throws(() => decodeState('{"schema":2}'));
  assert.throws(() => decodeState(JSON.stringify({ ...initial(), queue: [{ update: {} }] })));
});
