"use client";

import { useEffect, useState } from "react";
import { api, message } from "@/lib/api";
import type { SimulationJob } from "@/lib/types";

interface Props {
  scenarioId: string | null;
  onJobCompleted: (runId: string) => void;
  unavailableTools: string[];
}

export default function AsyncJobPanel({ scenarioId, onJobCompleted, unavailableTools }: Props) {
  const [job, setJob] = useState<SimulationJob | null>(null);
  const [samples, setSamples] = useState(500);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function startAsyncJob() {
    if (!scenarioId) return;
    try {
      setLoading(true);
      setError("");
      const created = await api<SimulationJob>("/simulations/jobs", {
        scenario_id: scenarioId,
        samples,
        unavailable_tools: unavailableTools,
      });
      setJob(created);
    } catch (err) {
      setError(message(err));
    } finally {
      setLoading(false);
    }
  }

  // Poll job status until complete
  useEffect(() => {
    if (!job || job.status === "SUCCEEDED" || job.status === "DEGRADED" || job.status === "FAILED") {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await api<SimulationJob>(`/simulations/jobs/${job.job_id}`);
        setJob(updated);
        if (updated.run_id && (updated.status === "SUCCEEDED" || updated.status === "DEGRADED")) {
          onJobCompleted(updated.run_id);
        }
      } catch (err) {
        setError(message(err));
      }
    }, 800);

    return () => clearInterval(interval);
  }, [job, onJobCompleted]);

  return (
    <div className="panel flex flex-col gap-4 p-4">
      <div className="panel-header">
        <span>MOD-13 // ASYNC_JOB_RUNNER</span>
        <h2>Async Simulation Job &amp; Real-Time Event Stream</h2>
        <b>● POST /simulations/jobs</b>
      </div>

      <p className="text-body-sm text-outline-variant">
        Dispatch 1,000-sample heavy simulations asynchronously. Monitor execution state changes and event stream in real-time without blocking the user interface.
      </p>

      {/* Control Row */}
      <div className="flex items-center gap-3 p-3 bg-surface-container-lowest border border-outline-variant/30">
        <div className="flex items-center gap-2 flex-1">
          <label className="font-label-sm text-label-sm text-outline uppercase whitespace-nowrap">
            MONTE CARLO SAMPLES:
          </label>
          <input
            type="number"
            min={10}
            max={1000}
            value={samples}
            onChange={e => setSamples(Number(e.target.value))}
            className="w-32 bg-surface-container font-mono text-sm px-2 py-1 border border-outline-variant/40"
          />
        </div>

        <button
          type="button"
          disabled={!scenarioId || loading || (!!job && job.status === "RUNNING")}
          onClick={() => void startAsyncJob()}
          className="px-4 py-2 bg-primary hover:bg-primary-container text-on-primary-container font-label-md text-label-md font-bold uppercase tracking-wider transition-all disabled:opacity-50"
        >
          {loading ? "QUEUEING..." : "DISPATCH ASYNC JOB (1,000 RUNS)"}
        </button>
      </div>

      {error && <div className="toast error-toast">⚠️ {error}</div>}

      {/* Active Job Dashboard */}
      {job && (
        <div className="flex flex-col gap-3 p-3 bg-surface-container-low border border-outline-variant/30">
          <div className="flex items-center justify-between font-label-sm text-label-sm">
            <span>
              JOB ID: <strong className="text-secondary">{job.job_id}</strong>
            </span>
            <span
              className={`px-2 py-0.5 font-bold uppercase ${
                job.status === "SUCCEEDED"
                  ? "text-primary bg-primary/10 border border-primary/20"
                  : job.status === "DEGRADED"
                  ? "text-tertiary bg-tertiary/10 border border-tertiary/20"
                  : job.status === "FAILED"
                  ? "text-error bg-error/10 border border-error/20"
                  : "text-secondary animate-pulse"
              }`}
            >
              {job.status} ({job.progress}%)
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full h-2 bg-surface-container-highest overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                job.status === "FAILED" ? "bg-error" : job.status === "DEGRADED" ? "bg-tertiary" : "bg-primary"
              }`}
              style={{ width: `${job.progress}%` }}
            />
          </div>

          {/* Event Stream Table */}
          <div className="flex flex-col gap-1.5 mt-2">
            <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
              REAL-TIME EXECUTION EVENT STREAM ({job.events.length} EVENTS)
            </span>
            <div className="max-h-60 overflow-y-auto border border-outline-variant/20 divide-y divide-outline-variant/20 font-mono text-xs">
              {job.events.map((evt, idx) => (
                <div key={idx} className="p-2 flex items-center justify-between bg-surface-container-lowest">
                  <div className="flex items-center gap-2">
                    <span className="text-outline">[{evt.at.split("T")[1]?.slice(0, 8) || evt.at}]</span>
                    <span className="text-primary font-bold uppercase">{evt.event}</span>
                    {evt.tool_name && (
                      <span className="px-1 py-0.2 text-[10px] bg-surface-container-high text-secondary">
                        {evt.tool_name}
                      </span>
                    )}
                  </div>
                  <span className="text-outline-variant">{evt.message || `Progress ${evt.progress}%`}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
