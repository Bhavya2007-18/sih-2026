"use client";

import React, { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { api } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface MapRouteData {
  id: string;
  name: string;
  geometry: { type: "LineString"; coordinates: [number, number][] };
  eta: { hours: number; formatted: string };
  resilience: number;
  risk_level: string;
}

export interface MapNodeData {
  id: string;
  name: string;
  lat: number;
  lng: number;
  status: string;
}

export interface MapEventData {
  id: string;
  name: string;
  type: string;
  lat: number;
  lng: number;
  severity: string;
  details?: string;
}

export interface ScenarioMapPayload {
  scenario_id: string;
  scope: string;
  origin: { id: string; name: string; lat: number; lng: number };
  destination: { id: string; name: string; lat: number; lng: number };
  nodes: MapNodeData[];
  routes: MapRouteData[];
  events: MapEventData[];
}

// ─── Fallback data ─────────────────────────────────────────────────────────────

const FALLBACK_MAP_DATA: ScenarioMapPayload = {
  scenario_id: "demo-ladakh-001",
  scope: "synthetic scenario / cached",
  origin: { id: "orig-1", name: "Leh Supply Depot", lat: 34.1526, lng: 77.5771 },
  destination: { id: "dest-1", name: "Karakoram Forward Post", lat: 35.1378, lng: 78.1345 },
  nodes: [
    { id: "node-1", name: "Kharu Staging Post", lat: 33.95, lng: 77.72, status: "OPERATIONAL" },
    { id: "node-2", name: "Tangtse Checkpoint", lat: 34.02, lng: 78.18, status: "DEGRADED" },
    { id: "node-3", name: "Saser Pass Relay", lat: 34.75, lng: 77.85, status: "OPERATIONAL" },
  ],
  routes: [
    {
      id: "route-a",
      name: "Route A (Primary Axis)",
      geometry: {
        type: "LineString",
        coordinates: [
          [77.5771, 34.1526],
          [77.72, 33.95],
          [77.95, 34.25],
          [78.18, 34.02],
          [78.1345, 35.1378],
        ],
      },
      eta: { hours: 6.8, formatted: "6.8 h" },
      resilience: 0.74,
      risk_level: "MEDIUM",
    },
    {
      id: "route-b",
      name: "Route B (High Pass Bypass)",
      geometry: {
        type: "LineString",
        coordinates: [
          [77.5771, 34.1526],
          [77.85, 34.75],
          [78.0, 34.9],
          [78.1345, 35.1378],
        ],
      },
      eta: { hours: 7.4, formatted: "7.4 h" },
      resilience: 0.81,
      risk_level: "LOW",
    },
    {
      id: "route-c",
      name: "Route C (Direct Valley Express)",
      geometry: {
        type: "LineString",
        coordinates: [
          [77.5771, 34.1526],
          [77.68, 34.45],
          [77.92, 34.8],
          [78.1345, 35.1378],
        ],
      },
      eta: { hours: 5.9, formatted: "5.9 h" },
      resilience: 0.61,
      risk_level: "HIGH",
    },
  ],
  events: [
    {
      id: "evt-disrupt-1",
      name: "Landslide Blockade",
      type: "DISRUPTION",
      lat: 34.45,
      lng: 77.68,
      severity: "CRITICAL",
      details: "Active pass obstruction reported",
    },
  ],
};

const ROUTE_COLORS: Record<string, string> = {
  "route-a": "#70d7ff",
  "route-b": "#4be277",
  "route-c": "#ffba61",
};

// ─── Node/Event pin colours ────────────────────────────────────────────────────

function nodeColor(status: string): { bg: string; border: string } {
  if (status === "OPERATIONAL") return { bg: "#134e2c", border: "#4be277" };
  if (status === "DEGRADED") return { bg: "#785600", border: "#ffba61" };
  return { bg: "#6e1d24", border: "#ff7183" };
}

function badgeColors(badge: string): { bg: string; color: string } {
  if (badge === "CRITICAL" || badge === "HIGH") return { bg: "#ffebee", color: "#c62828" };
  if (badge === "OPERATIONAL" || badge === "LOW") return { bg: "#e8f5e9", color: "#2e7d32" };
  return { bg: "#fff8e1", color: "#f57f17" };
}

// ─── SVG marker factory (returns a data-URI for use as Leaflet DivIcon) ────────

function makeSvgIcon(fill: string, stroke: string, scale = 1): string {
  const w = Math.round(24 * scale);
  const h = Math.round(32 * scale);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 24 32">
    <path d="M12 0C5.373 0 0 5.373 0 12c0 9 12 20 12 20S24 21 24 12C24 5.373 18.627 0 12 0z"
      fill="${fill}" stroke="${stroke}" stroke-width="2"/>
    <circle cx="12" cy="12" r="4" fill="#ffffff"/>
  </svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface MayaMapProps {
  scenarioId?: string;
  selectedRouteId?: string;
  onSelectRoute?: (routeId: string) => void;
  isOnline?: boolean;
}

// ─── Main component ───────────────────────────────────────────────────────────
// Leaflet is browser-only; we guard against SSR by mounting only on the client.

export default function MayaMap({
  scenarioId = "demo-ladakh-001",
  selectedRouteId,
  onSelectRoute,
  isOnline = true,
}: MayaMapProps) {
  const [mounted, setMounted] = useState(false);
  const [mapData, setMapData] = useState<ScenarioMapPayload>(FALLBACK_MAP_DATA);
  const [layersVisibility, setLayersVisibility] = useState({ routes: true, nodes: true, events: true });
  const [activeInfo, setActiveInfo] = useState<{
    lat: number;
    lng: number;
    title: string;
    subtitle?: string;
    badge?: string;
    details?: string;
  } | null>(null);

  // Refs for programmatic map control (set after MapContainer mounts)
  const mapRef = useRef<import("leaflet").Map | null>(null);

  // Mount guard — ensures Leaflet only runs in the browser
  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch scenario data
  useEffect(() => {
    let ignore = false;
    async function load() {
      if (!isOnline) {
        setMapData(FALLBACK_MAP_DATA);
        return;
      }
      try {
        const fetched = await api<ScenarioMapPayload>(
          `/scenarios/${encodeURIComponent(scenarioId)}/map`
        );
        if (!ignore) setMapData(fetched);
      } catch {
        if (!ignore) setMapData(FALLBACK_MAP_DATA);
      }
    }
    load();
    return () => { ignore = true; };
  }, [scenarioId, isOnline]);

  // Formatted routes — coordinates flipped from GeoJSON [lng,lat] to Leaflet [lat,lng]
  const formattedRoutes = useMemo(() => {
    return mapData.routes.map(r => ({
      ...r,
      positions: r.geometry.coordinates.map(([lng, lat]) => [lat, lng] as [number, number]),
      color: ROUTE_COLORS[r.id] || "#70d7ff",
      isSelected: r.id === selectedRouteId,
    }));
  }, [mapData.routes, selectedRouteId]);

  // Fit map to all points
  const handleFit = useCallback(() => {
    const m = mapRef.current;
    if (!m) return;
    // dynamic import to avoid SSR issues with leaflet
    import("leaflet").then(L => {
      const bounds = L.latLngBounds([]);
      bounds.extend([mapData.origin.lat, mapData.origin.lng]);
      bounds.extend([mapData.destination.lat, mapData.destination.lng]);
      mapData.nodes.forEach(n => bounds.extend([n.lat, n.lng]));
      mapData.events.forEach(e => bounds.extend([e.lat, e.lng]));
      mapData.routes.forEach(r =>
        r.geometry.coordinates.forEach(([lng, lat]) => bounds.extend([lat, lng]))
      );
      m.fitBounds(bounds, { padding: [50, 50] });
    });
  }, [mapData]);

  const handleReset = useCallback(() => {
    mapRef.current?.setView([34.65, 77.85], 8);
  }, []);

  if (!mounted) {
    // SSR / pre-hydration placeholder — same dimensions as the map
    return (
      <div
        style={{
          width: "100%",
          height: "620px",
          background: "#080e17",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#4be277",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "11px",
          letterSpacing: ".08em",
        }}
      >
        INITIALISING MAP…
      </div>
    );
  }

  // Lazy-load react-leaflet components only on the client
  return <LeafletMap
    mapData={mapData}
    formattedRoutes={formattedRoutes}
    layersVisibility={layersVisibility}
    setLayersVisibility={setLayersVisibility}
    activeInfo={activeInfo}
    setActiveInfo={setActiveInfo}
    mapRef={mapRef}
    isOnline={isOnline}
    onSelectRoute={onSelectRoute}
    handleFit={handleFit}
    handleReset={handleReset}
  />;
}

// ─── Inner component (client-only, loaded after mount guard) ──────────────────

import "leaflet/dist/leaflet.css";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";
import L from "leaflet";

// Leaflet's default icon asset path is broken in bundlers — fix it once
if (typeof window !== "undefined") {
  // @ts-expect-error _getIconUrl is an internal Leaflet method
  delete L.Icon.Default.prototype._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
    iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
    shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  });
}

// Small hook-based component that syncs the Leaflet map instance into a ref
function MapRefSync({ mapRef }: { mapRef: React.MutableRefObject<L.Map | null> }) {
  const map = useMap();
  useEffect(() => { mapRef.current = map; }, [map, mapRef]);
  return null;
}

interface LeafletMapProps {
  mapData: ScenarioMapPayload;
  formattedRoutes: ReturnType<typeof Array.prototype.map>;
  layersVisibility: { routes: boolean; nodes: boolean; events: boolean };
  setLayersVisibility: React.Dispatch<React.SetStateAction<{ routes: boolean; nodes: boolean; events: boolean }>>;
  activeInfo: { lat: number; lng: number; title: string; subtitle?: string; badge?: string; details?: string } | null;
  setActiveInfo: React.Dispatch<React.SetStateAction<LeafletMapProps["activeInfo"]>>;
  mapRef: React.MutableRefObject<L.Map | null>;
  isOnline: boolean;
  onSelectRoute?: (routeId: string) => void;
  handleFit: () => void;
  handleReset: () => void;
}

function LeafletMap({
  mapData,
  formattedRoutes,
  layersVisibility,
  setLayersVisibility,
  activeInfo,
  setActiveInfo,
  mapRef,
  isOnline,
  onSelectRoute,
  handleFit,
  handleReset,
}: LeafletMapProps) {
  return (
    <div style={{ position: "relative", width: "100%", background: "#080e17", fontFamily: "'JetBrains Mono', monospace" }}>

      {/* ── Header Toolbar ──────────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
          padding: "8px 12px",
          background: "#101722",
          borderBottom: "1px solid #293544",
          fontSize: "10px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <span style={{ color: "#70d7ff", fontWeight: 700 }}>OPENSTREETMAP PLATFORM</span>
          <span style={{ color: "#4be277", display: "inline-flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#4be277", display: "inline-block" }} />
            SDK: react-leaflet · OSM tiles
          </span>
          <span
            style={{
              padding: "2px 6px",
              background: isOnline ? "#102319" : "#2a141c",
              color: isOnline ? "#4be277" : "#ff7183",
              border: `1px solid ${isOnline ? "#265e3b" : "#703140"}`,
              fontWeight: 600,
            }}
          >
            {isOnline ? "LIVE TELEMETRY" : "OFFLINE — CACHED"}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <button
            onClick={handleFit}
            style={{
              background: "#202735",
              color: "#70d7ff",
              border: "1px solid #38556a",
              padding: "4px 8px",
              fontSize: "9px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            FIT SCENARIO
          </button>
          <button
            onClick={handleReset}
            style={{
              background: "#202735",
              color: "#dfe7f1",
              border: "1px solid #293544",
              padding: "4px 8px",
              fontSize: "9px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            RESET VIEW
          </button>
        </div>
      </div>

      {/* ── Layers Bar ──────────────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "5px 12px",
          background: "#0a1019",
          borderBottom: "1px solid #293544",
          fontSize: "9px",
          color: "#8796a8",
        }}
      >
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <span>LAYERS:</span>
          {(["routes", "nodes", "events"] as const).map(key => (
            <label
              key={key}
              style={{ display: "inline-flex", alignItems: "center", gap: "4px", cursor: "pointer" }}
            >
              <input
                type="checkbox"
                checked={layersVisibility[key]}
                onChange={e => setLayersVisibility(p => ({ ...p, [key]: e.target.checked }))}
              />
              <span
                style={{
                  color: key === "routes" ? "#70d7ff" : key === "nodes" ? "#4be277" : "#ff7183",
                }}
              >
                {key.toUpperCase()}
              </span>
            </label>
          ))}
        </div>
        <span style={{ color: "#627385" }}>
          SCENARIO: <span style={{ color: "#dfe7f1" }}>{mapData.scenario_id}</span>
        </span>
      </div>

      {/* ── Map Canvas ──────────────────────────────────────────────────── */}
      <MapContainer
        center={[34.65, 77.85]}
        zoom={8}
        style={{ width: "100%", height: "560px" }}
        // Dark-mode filter applied via className below
        className="maya-leaflet-map"
      >
        <MapRefSync mapRef={mapRef} />

        {/* OpenStreetMap dark-compatible tile layer (CartoDB Dark Matter — no key needed) */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
          maxZoom={19}
        />

        {/* ── Routes ────────────────────────────────────────────────── */}
        {layersVisibility.routes &&
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (formattedRoutes as any[]).map((r) => (
            <Polyline
              key={r.id}
              positions={r.positions}
              pathOptions={{
                color: r.color,
                opacity: r.isSelected ? 1.0 : 0.65,
                weight: r.isSelected ? 6 : 3,
              }}
              eventHandlers={{
                click: () => {
                  onSelectRoute?.(r.id);
                  const mid = r.positions[Math.floor(r.positions.length / 2)] as [number, number];
                  setActiveInfo({
                    lat: mid[0],
                    lng: mid[1],
                    title: r.name,
                    subtitle: `ETA: ${r.eta.formatted} · RESILIENCE: ${(r.resilience * 100).toFixed(0)}%`,
                    badge: r.risk_level,
                    details: `Route ID: ${r.id.toUpperCase()}`,
                  });
                },
              }}
            />
          ))}

        {/* ── Nodes (origin, destination, staging) ──────────────────── */}
        {layersVisibility.nodes && (
          <>
            {/* Origin */}
            <Marker
              position={[mapData.origin.lat, mapData.origin.lng]}
              icon={L.icon({
                iconUrl: makeSvgIcon("#0066cc", "#70d7ff", 1.15),
                iconSize: [28, 37],
                iconAnchor: [14, 37],
                popupAnchor: [0, -37],
              })}
              eventHandlers={{
                click: () =>
                  setActiveInfo({
                    lat: mapData.origin.lat,
                    lng: mapData.origin.lng,
                    title: `[ORIGIN] ${mapData.origin.name}`,
                    subtitle: "Primary Logistics Base",
                    badge: "ORIGIN",
                    details: `Coordinates: ${mapData.origin.lat.toFixed(4)}, ${mapData.origin.lng.toFixed(4)}`,
                  }),
              }}
            >
              <Popup>{mapData.origin.name}</Popup>
            </Marker>

            {/* Destination */}
            <Marker
              position={[mapData.destination.lat, mapData.destination.lng]}
              icon={L.icon({
                iconUrl: makeSvgIcon("#0d7337", "#4be277", 1.25),
                iconSize: [30, 40],
                iconAnchor: [15, 40],
                popupAnchor: [0, -40],
              })}
              eventHandlers={{
                click: () =>
                  setActiveInfo({
                    lat: mapData.destination.lat,
                    lng: mapData.destination.lng,
                    title: `[DESTINATION] ${mapData.destination.name}`,
                    subtitle: "Target Forward Position",
                    badge: "DESTINATION",
                    details: `Coordinates: ${mapData.destination.lat.toFixed(4)}, ${mapData.destination.lng.toFixed(4)}`,
                  }),
              }}
            >
              <Popup>{mapData.destination.name}</Popup>
            </Marker>

            {/* Staging Nodes */}
            {mapData.nodes.map(node => {
              const { bg, border } = nodeColor(node.status);
              return (
                <Marker
                  key={node.id}
                  position={[node.lat, node.lng]}
                  icon={L.icon({
                    iconUrl: makeSvgIcon(bg, border, 0.9),
                    iconSize: [22, 29],
                    iconAnchor: [11, 29],
                    popupAnchor: [0, -29],
                  })}
                  eventHandlers={{
                    click: () =>
                      setActiveInfo({
                        lat: node.lat,
                        lng: node.lng,
                        title: node.name,
                        subtitle: `Status: ${node.status}`,
                        badge: node.status,
                        details: `ID: ${node.id} · Lat: ${node.lat.toFixed(4)} Lng: ${node.lng.toFixed(4)}`,
                      }),
                  }}
                >
                  <Popup>{node.name}</Popup>
                </Marker>
              );
            })}
          </>
        )}

        {/* ── Events / Disruptions ──────────────────────────────────── */}
        {layersVisibility.events &&
          mapData.events.map(event => (
            <Marker
              key={event.id}
              position={[event.lat, event.lng]}
              icon={L.icon({
                iconUrl: makeSvgIcon("#8a1c27", "#ff7183", 1.0),
                iconSize: [24, 32],
                iconAnchor: [12, 32],
                popupAnchor: [0, -32],
              })}
              eventHandlers={{
                click: () =>
                  setActiveInfo({
                    lat: event.lat,
                    lng: event.lng,
                    title: `⚠️ ${event.name}`,
                    subtitle: `Type: ${event.type} · Severity: ${event.severity}`,
                    badge: event.severity,
                    details: event.details || "No additional intel reported",
                  }),
              }}
            >
              <Popup>{event.name}</Popup>
            </Marker>
          ))}
      </MapContainer>

      {/* ── Info Panel (replaces Google InfoWindow) ─────────────────────── */}
      {activeInfo && (
        <div
          style={{
            position: "absolute",
            bottom: "16px",
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 1000,
            background: "#101722",
            border: "1px solid #38556a",
            borderRadius: "4px",
            padding: "12px 14px",
            minWidth: "220px",
            maxWidth: "340px",
            boxShadow: "0 6px 24px rgba(0,0,0,0.7)",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "11px",
            color: "#dfe7f1",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
            <div style={{ fontWeight: 700, fontSize: "12px", marginBottom: "4px" }}>
              {activeInfo.title}
            </div>
            <button
              onClick={() => setActiveInfo(null)}
              style={{
                background: "transparent",
                border: "none",
                color: "#8796a8",
                cursor: "pointer",
                fontSize: "14px",
                lineHeight: 1,
                padding: 0,
                flexShrink: 0,
              }}
              aria-label="Close info panel"
            >
              ✕
            </button>
          </div>
          {activeInfo.subtitle && (
            <div style={{ color: "#8796a8", marginBottom: "6px", fontSize: "10px" }}>
              {activeInfo.subtitle}
            </div>
          )}
          {activeInfo.badge && (() => {
            const { bg, color } = badgeColors(activeInfo.badge);
            return (
              <span
                style={{
                  display: "inline-block",
                  padding: "2px 6px",
                  borderRadius: "3px",
                  background: bg,
                  color,
                  fontWeight: 600,
                  fontSize: "10px",
                  marginBottom: "4px",
                }}
              >
                {activeInfo.badge}
              </span>
            );
          })()}
          {activeInfo.details && (
            <div style={{ color: "#627385", fontSize: "10px", marginTop: "4px" }}>
              {activeInfo.details}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
