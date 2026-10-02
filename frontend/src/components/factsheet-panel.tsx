"use client";

import type { FactSheet } from "@/lib/types";

interface Props {
  factSheet?: FactSheet | null;
}

export default function FactSheetPanel({ factSheet }: Props) {
  if (!factSheet) {
    return (
      <div className="panel p-4">
        <div className="panel-header">
          <span>MOD-10 // EVIDENCE_LAYER</span>
          <h2>FactSheet &amp; Evidence Layer</h2>
          <b>● COMPUTED PROOF</b>
        </div>
        <div className="empty-state mt-3">
          No FactSheet generated yet. Run a baseline or what-if simulation to inspect true computed outputs.
        </div>
      </div>
    );
  }

  const entries = Object.entries(factSheet.facts);

  return (
    <div className="panel flex flex-col gap-4 p-4">
      <div className="panel-header">
        <span>MOD-10 // EVIDENCE_LAYER</span>
        <h2>FactSheet &amp; Evidence Layer</h2>
        <b>● COMPUTED PROOF ({entries.length} FACTS)</b>
      </div>

      <div className="flex items-center justify-between text-label-sm font-label-sm text-outline p-2 bg-surface-container-lowest border border-outline-variant/20">
        <span>GENERATED AT: <strong className="text-secondary">{factSheet.generated_at}</strong></span>
        <span>EVIDENCE ENGINE: <strong className="text-primary">EVIDENCE_LAYER v1.0.0</strong></span>
      </div>

      {/* Facts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        {entries.map(([key, fact]) => (
          <div key={key} className="p-3 bg-surface-container-low border-l-2 border-primary flex flex-col justify-between gap-1">
            <div className="flex items-center justify-between text-label-sm">
              <span className="text-outline uppercase font-semibold">{fact.label}</span>
              <span className="px-1.5 py-0.2 bg-surface-container text-secondary text-[10px] font-mono">
                {fact.source_tool}
              </span>
            </div>
            <div className="font-data-mono-lg text-data-mono-lg text-on-surface truncate">
              {fact.value == null ? "—" : String(fact.value)}
              {fact.unit && <span className="text-body-sm text-outline ml-1 font-normal">{fact.unit}</span>}
            </div>
            <div className="text-[10px] font-mono text-outline-variant truncate">Key: {key}</div>
          </div>
        ))}
      </div>

      {/* Assumptions Ledger */}
      {factSheet.assumptions.length > 0 && (
        <div className="p-3 bg-surface-container-lowest border border-outline-variant/30 flex flex-col gap-2">
          <span className="font-label-sm text-label-sm text-tertiary uppercase tracking-wider font-semibold">
            SYNTHETIC DOMAIN ASSUMPTIONS ({factSheet.assumptions.length})
          </span>
          <ul className="list-disc pl-5 text-body-sm text-on-surface-variant space-y-1">
            {factSheet.assumptions.slice(0, 5).map((line, idx) => (
              <li key={idx}>{line}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
