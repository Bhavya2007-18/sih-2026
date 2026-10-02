"use client";

import type { ConfidenceAssessment } from "@/lib/types";

interface Props {
  confidence?: ConfidenceAssessment | null;
}

export default function ConfidencePanel({ confidence }: Props) {
  if (!confidence) {
    return (
      <div className="panel p-4">
        <div className="panel-header">
          <span>MOD-12 // CONFIDENCE_ENGINE</span>
          <h2>Confidence &amp; Uncertainty Control</h2>
          <b>● SCORE EVALUATION</b>
        </div>
        <div className="empty-state mt-3">
          No confidence evaluation available. Run a simulation run to compute execution quality scores.
        </div>
      </div>
    );
  }

  const scorePct = Math.round(confidence.score * 100);

  return (
    <div className="panel flex flex-col gap-4 p-4">
      <div className="panel-header">
        <span>MOD-12 // CONFIDENCE_ENGINE</span>
        <h2>Confidence &amp; Uncertainty Control</h2>
        <b className={confidence.status === "DEGRADED" ? "text-tertiary" : "text-primary"}>
          ● {confidence.status} ({scorePct}%)
        </b>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Score Card */}
        <div className="p-4 bg-surface-container-low border-l-2 border-primary flex flex-col justify-between h-32">
          <span className="font-label-sm text-label-sm text-outline uppercase">Confidence Quality Score</span>
          <div className="font-data-mono-lg text-headline-xl text-primary font-bold">{scorePct}%</div>
          <div className="text-[11px] text-outline-variant">
            {confidence.cap != null ? `Capped at ${Math.round(confidence.cap * 100)}% (Uncalibrated Synthetic Model)` : "Uncapped baseline"}
          </div>
        </div>

        {/* Status & Interpretation */}
        <div className="md:col-span-2 p-4 bg-surface-container-low flex flex-col justify-between h-32">
          <div className="flex items-center justify-between">
            <span className="font-label-sm text-label-sm text-outline uppercase">Execution Assessment</span>
            <span
              className={`px-2 py-0.5 font-label-sm font-bold uppercase ${
                confidence.status === "NOMINAL"
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : confidence.status === "DEGRADED"
                  ? "bg-tertiary/10 text-tertiary border border-tertiary/20"
                  : "bg-error/10 text-error border border-error/20"
              }`}
            >
              {confidence.status}
            </span>
          </div>
          <p className="text-body-sm text-on-surface-variant">{confidence.interpretation}</p>
        </div>
      </div>

      {/* Factor Breakdown Grid */}
      <div className="flex flex-col gap-2">
        <span className="font-label-sm text-label-sm text-secondary uppercase tracking-wider font-semibold">
          EVALUATION FACTORS ({Object.keys(confidence.factors).length})
        </span>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2">
          {Object.entries(confidence.factors).map(([factor, value]) => {
            const valPct = Math.round(value * 100);
            return (
              <div key={factor} className="p-2.5 bg-surface-container-lowest border border-outline-variant/30 flex flex-col gap-1">
                <span className="text-[10px] font-mono text-outline uppercase truncate">{factor.replaceAll("_", " ")}</span>
                <span className={`font-data-mono-md text-data-mono-md ${valPct < 50 ? "text-tertiary" : "text-primary"}`}>
                  {valPct}%
                </span>
                <div className="w-full h-1 bg-surface-container-highest overflow-hidden">
                  <div
                    className={`h-full ${valPct < 50 ? "bg-tertiary" : "bg-primary"}`}
                    style={{ width: `${valPct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Degraded Reasons */}
      {confidence.degraded_reasons.length > 0 && (
        <div className="p-3 bg-surface-container-lowest border border-tertiary/30 flex flex-col gap-1.5">
          <span className="font-label-sm text-label-sm text-tertiary uppercase font-semibold">
            DEGRADATION &amp; AUDIT REASONS
          </span>
          <ul className="list-disc pl-5 text-body-sm text-on-surface-variant space-y-1">
            {confidence.degraded_reasons.map((reason, idx) => (
              <li key={idx}>{reason}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
