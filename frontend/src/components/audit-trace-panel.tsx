"use client";

import type { AuditTrace } from "@/lib/types";

interface Props {
  auditTrace?: AuditTrace | null;
}

export default function AuditTracePanel({ auditTrace }: Props) {
  if (!auditTrace) {
    return (
      <div className="panel p-4">
        <div className="panel-header">
          <span>MOD-11 // AUDIT_TRACE</span>
          <h2>Policy Execution Audit Trace</h2>
          <b>● REPRODUCIBLE REASONING</b>
        </div>
        <div className="empty-state mt-3">
          No audit trace available. Run a simulation to generate a full policy graph audit log.
        </div>
      </div>
    );
  }

  return (
    <div className="panel flex flex-col gap-4 p-4">
      <div className="panel-header">
        <span>MOD-11 // AUDIT_TRACE</span>
        <h2>Policy Execution Audit Trace</h2>
        <b className={auditTrace.status === "DEGRADED" ? "text-tertiary" : "text-primary"}>
          ● {auditTrace.status} ({auditTrace.entries.length} ENTRIES)
        </b>
      </div>

      <div className="flex items-center justify-between text-label-sm font-label-sm text-outline p-2 bg-surface-container-lowest border border-outline-variant/20">
        <span>POLICY ID: <strong className="text-secondary">{auditTrace.policy_id}</strong></span>
        <span>STATUS: <strong className={auditTrace.status === "DEGRADED" ? "text-tertiary" : "text-primary"}>{auditTrace.status}</strong></span>
      </div>

      {/* Audit Timeline */}
      <div className="flex flex-col gap-2">
        {auditTrace.entries.map(entry => (
          <div
            key={entry.sequence}
            className={`p-3 bg-surface-container-low border-l-2 flex flex-col gap-1.5 ${
              entry.status === "FAILED"
                ? "border-error"
                : entry.status === "DEGRADED"
                ? "border-tertiary"
                : "border-primary"
            }`}
          >
            <div className="flex items-center justify-between text-label-sm font-label-sm">
              <div className="flex items-center gap-2">
                <span className="px-1.5 py-0.5 bg-surface-container-high text-outline font-bold">
                  #{entry.sequence}
                </span>
                <span className="text-on-surface font-semibold uppercase">{entry.event}</span>
                {entry.tool_name && (
                  <span className="px-1.5 py-0.2 bg-primary/10 text-primary border border-primary/20">
                    {entry.tool_name}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-1.5 py-0.2 font-bold ${
                    entry.status === "SUCCESS"
                      ? "text-primary"
                      : entry.status === "DEGRADED"
                      ? "text-tertiary"
                      : entry.status === "FAILED"
                      ? "text-error"
                      : "text-secondary"
                  }`}
                >
                  {entry.status}
                </span>
                <span className="text-outline text-[11px]">{entry.at}</span>
              </div>
            </div>

            {/* Inputs & Outputs Summary */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono mt-1">
              {Object.keys(entry.inputs).length > 0 && (
                <div className="p-2 bg-surface-container-lowest border border-outline-variant/20">
                  <span className="text-outline uppercase font-semibold block mb-1">Inputs:</span>
                  <pre className="text-on-surface-variant overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(entry.inputs, null, 2)}
                  </pre>
                </div>
              )}
              {Object.keys(entry.outputs).length > 0 && (
                <div className="p-2 bg-surface-container-lowest border border-outline-variant/20">
                  <span className="text-outline uppercase font-semibold block mb-1">Outputs:</span>
                  <pre className="text-on-surface-variant overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(entry.outputs, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            {/* Warnings */}
            {entry.warnings.length > 0 && (
              <div className="text-[11px] text-tertiary bg-tertiary-container/10 p-1.5 border border-tertiary/20">
                ⚠️ {entry.warnings.join(" | ")}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
