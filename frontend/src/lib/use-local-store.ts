"use client";

import { useEffect, useRef, useState } from "react";
import { decodeState, emptyState, log, STORAGE_KEY } from "./offline";
import type { LocalState } from "./types";
import { message } from "./api";

export function useLocalStore() {
  const [state, setState] = useState<LocalState | null>(null);
  const [storageError, setStorageError] = useState("");
  const current = useRef<LocalState | null>(null);
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const loaded = raw ? log(decodeState(raw), "cache", "Restored browser cache and durable queue after page load.") : emptyState(crypto.randomUUID());
      localStorage.setItem(STORAGE_KEY, JSON.stringify(loaded));
      current.current = loaded;
      // Initial client hydration reads an external browser store unavailable to SSR.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState(loaded);
    } catch (error) { setStorageError(message(error)); }
  }, []);
  function commit(update: (state: LocalState) => LocalState) {
    if (!current.current) throw new Error("Local store unavailable. No data was changed.");
    const next = update(current.current);
    // Save first. A quota/security failure must not masquerade as a durable write.
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); }
    catch (error) { setStorageError(message(error)); throw new Error(`Browser persistence failed: ${message(error)}. Change not committed locally.`); }
    current.current = next;
    setState(next);
    setStorageError("");
    return next;
  }
  return { state, current, commit, storageError };
}
