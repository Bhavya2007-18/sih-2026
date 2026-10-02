"use client";

import { useEffect, useState } from "react";
import { api, message } from "@/lib/api";
import type { ToolSpec } from "@/lib/types";

interface Props {
  unavailableTools: string[];
  onToggleUnavailable: (toolName: string) => void;
}

export default function ToolRegistryPanel({ unavailableTools, onToggleUnavailable }: Props) {
  const [tools, setTools] = useState<ToolSpec[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function loadTools() {
      try {
        setLoading(true);
        const data = await api<ToolSpec[]>("/tools");
        if (!cancelled) setTools(data);
      } catch (err) {
        if (!cancelled) setError(message(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void loadTools();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="panel flex flex-col gap-4 p-4">
      <div className="panel-header">
        <span>MOD-09 // TOOL_REGISTRY</span>
        <h2>Declarative Tool Registry &amp; Policy DAG</h2>
        <b>● DETERMINISTIC GRAPH</b>
      </div>

      <p className="text-body-sm text-outline-variant">
        Every simulation module in Maya is registered declaratively with explicit inputs, outputs, schemas, and fallbacks.
        Toggle availability to test degraded execution and deterministic fallback activation.
      </p>

      {/* Policy DAG Visualization */}
      <div className="p-3 bg-surface-container-lowest border border-outline-variant/30 flex flex-col gap-2">
        <span className="font-label-sm text-label-sm text-secondary uppercase tracking-wider font-semibold">
          POLICY EXECUTION DAG (maya.synthetic.simulation v1.0.0)
        </span>
        <div className="flex flex-wrap items-center gap-2 text-label-sm font-label-sm">
          <span className="px-2 py-1 bg-surface-container-high text-primary border border-primary/20">
            1. route_simulator
          </span>
          <span className="text-outline">→</span>
          <span className="px-2 py-1 bg-surface-container-high text-primary border border-primary/20">
            2. readiness_predictor
          </span>
          <span className="text-outline">→</span>
          <span className="px-2 py-1 bg-surface-container-high text-primary border border-primary/20">
            3. stock_forecaster
          </span>
          <span className="text-outline">→</span>
          <span className="px-2 py-1 bg-surface-container-high text-primary border border-primary/20">
            4. uncertainty_engine
          </span>
          <span className="text-outline">→</span>
          <span className="px-2 py-1 bg-surface-container-high text-secondary border border-secondary/20">
            5. evidence_layer
          </span>
          <span className="text-outline">→</span>
          <span className="px-2 py-1 bg-surface-container-high text-tertiary border border-tertiary/20">
            6. confidence_engine
          </span>
        </div>
      </div>

      {loading && <div className="text-label-sm text-outline animate-pulse">Loading tool registry from /api/tools...</div>}
      {error && <div className="toast error-toast">Failed to load tool registry: {error}</div>}

      {/* Tool Table */}
      {!loading && !error && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-label-sm font-label-sm border-collapse">
            <thead>
              <tr className="border-b border-outline-variant/30 text-outline uppercase">
                <th className="p-2">Tool Name</th>
                <th className="p-2">Category</th>
                <th className="p-2">Inputs</th>
                <th className="p-2">Outputs</th>
                <th className="p-2">Fallback Target</th>
                <th className="p-2">Version</th>
                <th className="p-2 text-right">Simulated Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/20">
              {tools.map(tool => {
                const isUnavailable = unavailableTools.includes(tool.name);
                return (
                  <tr key={tool.name} className={isUnavailable ? "bg-error-container/10" : undefined}>
                    <td className="p-2 font-bold text-on-surface flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${isUnavailable ? "bg-error" : "bg-primary"}`} />
                      {tool.name}
                    </td>
                    <td className="p-2 text-secondary">{tool.category}</td>
                    <td className="p-2 text-outline-variant">{tool.inputs.join(", ")}</td>
                    <td className="p-2 text-outline-variant">{tool.outputs.join(", ")}</td>
                    <td className="p-2 text-tertiary">{tool.fallback || "None"}</td>
                    <td className="p-2 text-outline">v{tool.version}</td>
                    <td className="p-2 text-right">
                      {tool.fallback ? (
                        <button
                          type="button"
                          onClick={() => onToggleUnavailable(tool.name)}
                          className={`px-2 py-0.5 font-label-sm uppercase transition-colors ${
                            isUnavailable
                              ? "bg-error text-on-error font-bold"
                              : "bg-surface-container-high hover:bg-surface-container text-primary border border-primary/20"
                          }`}
                        >
                          {isUnavailable ? "FORCE DEGRADED" : "AVAILABLE"}
                        </button>
                      ) : (
                        <span className="px-2 py-0.5 bg-surface-container-high text-outline">CORE AVAILABLE</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
