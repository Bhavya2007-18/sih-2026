"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

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
          [77.5771, 34.1526], [77.72, 33.95], [77.95, 34.25], [78.18, 34.02], [78.1345, 35.1378],
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
          [77.5771, 34.1526], [77.85, 34.75], [78.0, 34.9], [78.1345, 35.1378],
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
          [77.5771, 34.1526], [77.68, 34.45], [77.92, 34.8], [78.1345, 35.1378],
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

const RISK_COLORS: Record<string, string> = {
  LOW: "#4be277",
  MEDIUM: "#ffba61",
  HIGH: "#ff7183",
  CRITICAL: "#ff7183",
};

interface MayaMapProps {
  scenarioId?: string;
  selectedRouteId?: string;
  onSelectRoute?: (routeId: string) => void;
  isOnline?: boolean;
}

export default function MayaMap({
  scenarioId = "demo-ladakh-001",
  selectedRouteId,
  onSelectRoute,
  isOnline = true,
}: MayaMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const layersRef = useRef<{ routes: any[]; markers: any[] }>({ routes: [], markers: [] });

  const [mapData, setMapData] = useState<ScenarioMapPayload>(FALLBACK_MAP_DATA);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [layersVisibility, setLayersVisibility] = useState({
    routes: true,
    nodes: true,
    events: true,
  });

  // Fetch scenario map data
  useEffect(() => {
    let ignore = false;
    async function load() {
      if (!isOnline) { setMapData(FALLBACK_MAP_DATA); return; }
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

  // Initialize Leaflet map ONCE
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let cancelled = false;

    async function init() {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");

      if (cancelled || !containerRef.current || mapRef.current) return;

      // Handle re-mounts / React strict mode container reuse
      if ((containerRef.current as any)._leaflet_id) {
        (containerRef.current as any)._leaflet_id = null;
      }

      const map = L.map(containerRef.current, {
        center: [34.65, 77.85],
        zoom: 8,
        zoomControl: false,
        attributionControl: true,
      });

      // Clean dark GIS map layer (Esri World Dark Gray Base - 100% clean, keyless, watermark-free, no flag placeholders)
      const customTileUrl = process.env.NEXT_PUBLIC_MAP_TILE_URL;

      let tileUrl = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}";
      let attribution = '&copy; <a href="https://www.esri.com/">Esri</a>, USGS, NOAA, OpenStreetMap';
      let subdomains: string | string[] = "abc";

      if (customTileUrl) {
        tileUrl = customTileUrl;
        attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
      }

      L.tileLayer(tileUrl, {
        attribution,
        subdomains,
        maxZoom: 16,
      }).addTo(map);

      L.control.zoom({ position: "topright" }).addTo(map);

      if (cancelled) {
        map.remove();
        return;
      }

      mapRef.current = map;
      setMapLoaded(true);
    }
    init();

    return () => {
      cancelled = true;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Redraw overlays when data / selection / visibility changes
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;

    async function drawOverlays() {
      const L = (await import("leaflet")).default;
      const map = mapRef.current;

      // Remove previous overlays
      layersRef.current.routes.forEach(l => l.remove());
      layersRef.current.markers.forEach(m => m.remove());
      layersRef.current = { routes: [], markers: [] };

      const { routes, nodes, events, origin, destination } = mapData;

      // ── ROUTE POLYLINES ──────────────────────────────────────────────
      if (layersVisibility.routes) {
        routes.forEach(route => {
          const color = ROUTE_COLORS[route.id] ?? "#70d7ff";
          const isSelected = selectedRouteId === route.id;
          const dimmed = selectedRouteId && !isSelected;

          // Shadow / glow for selected
          if (isSelected) {
            const glow = L.polyline(
              route.geometry.coordinates.map(([lng, lat]) => [lat, lng] as [number, number]),
              { color: "#ffffff", weight: 10, opacity: 0.12, interactive: false }
            ).addTo(map);
            layersRef.current.routes.push(glow);
          }

          const polyline = L.polyline(
            route.geometry.coordinates.map(([lng, lat]) => [lat, lng] as [number, number]),
            {
              color,
              weight: isSelected ? 5 : 3,
              opacity: dimmed ? 0.25 : 0.9,
              dashArray: route.id === "route-c" ? "8 6" : undefined,
            }
          );

          polyline.on("click", () => onSelectRoute?.(route.id));
          polyline.on("mouseover", function (e) {
            const popup = L.popup({ closeButton: false, offset: [0, -4] })
              .setLatLng(e.latlng)
              .setContent(`
                <div style="font-family:'JetBrains Mono',monospace;font-size:11px;padding:6px 8px;background:#101722;color:#dfe7f1;border:1px solid ${color};min-width:160px;">
                  <strong style="color:${color};display:block;margin-bottom:3px;">${route.name}</strong>
                  <div>ETA: <b style="color:#4be277;">${route.eta.formatted}</b></div>
                  <div>RESILIENCE: <b style="color:#ffba61;">${Math.round(route.resilience * 100)}%</b></div>
                  <div>RISK: <b style="color:${RISK_COLORS[route.risk_level] ?? '#dfe7f1'};">${route.risk_level}</b></div>
                  <div style="margin-top:4px;color:#8796a8;font-size:9px;">Click to select route</div>
                </div>
              `)
              .openOn(map);
            layersRef.current.routes.push(popup);
          });

          polyline.addTo(map);
          layersRef.current.routes.push(polyline);
        });
      }

      // ── MARKERS ──────────────────────────────────────────────────────
      function makeIcon(color: string, size = 14) {
        return L.divIcon({
          html: `<div style="width:${size}px;height:${size}px;background:${color};border:2px solid #090e17;border-radius:50%;box-shadow:0 0 8px ${color};"></div>`,
          className: "",
          iconSize: [size, size],
          iconAnchor: [size / 2, size / 2],
        });
      }

      function makeLabelIcon(color: string, label: string) {
        return L.divIcon({
          html: `
            <div style="display:flex;flex-direction:column;align-items:center;gap:3px;">
              <div style="width:14px;height:14px;background:${color};border:2px solid #090e17;border-radius:50%;box-shadow:0 0 10px ${color};"></div>
              <span style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;color:${color};background:rgba(9,14,23,0.92);padding:1px 4px;border:1px solid ${color};white-space:nowrap;">${label}</span>
            </div>`,
          className: "",
          iconSize: [90, 34],
          iconAnchor: [45, 8],
        });
      }

      if (layersVisibility.nodes) {
        // Origin
        const origMarker = L.marker([origin.lat, origin.lng], {
          icon: makeLabelIcon("#70d7ff", "ORIGIN: LEH"),
        }).addTo(map);
        layersRef.current.markers.push(origMarker);

        // Destination
        const destMarker = L.marker([destination.lat, destination.lng], {
          icon: makeLabelIcon("#4be277", "DEST: KARAKORAM"),
        }).addTo(map);
        layersRef.current.markers.push(destMarker);

        // Logistics nodes
        nodes.forEach(node => {
          const col = node.status === "DEGRADED" ? "#ffba61" : "#8796a8";
          const m = L.marker([node.lat, node.lng], { icon: makeIcon(col, 9) })
            .bindTooltip(`<span style="font-family:'JetBrains Mono',monospace;font-size:10px;">${node.name} [${node.status}]</span>`, { className: "maya-tooltip" })
            .addTo(map);
          layersRef.current.markers.push(m);
        });
      }

      // Disruption events
      if (layersVisibility.events) {
        events.forEach(evt => {
          const evtIcon = L.divIcon({
            html: `
              <div style="display:flex;flex-direction:column;align-items:center;gap:3px;">
                <div style="width:13px;height:13px;background:#ff7183;border:2px solid #090e17;transform:rotate(45deg);box-shadow:0 0 8px #ff7183;"></div>
                <span style="font-family:'JetBrains Mono',monospace;font-size:8px;font-weight:700;color:#ff7183;background:rgba(30,10,15,0.95);padding:1px 4px;border:1px solid #ff7183;white-space:nowrap;">⚠ ${evt.name}</span>
              </div>`,
            className: "",
            iconSize: [120, 32],
            iconAnchor: [60, 8],
          });
          const m = L.marker([evt.lat, evt.lng], { icon: evtIcon })
            .bindTooltip(evt.details ?? evt.name, { className: "maya-tooltip" })
            .addTo(map);
          layersRef.current.markers.push(m);
        });
      }

      // Fit bounds to scenario
      try {
        const allLatLngs = [
          [origin.lat, origin.lng] as [number, number],
          [destination.lat, destination.lng] as [number, number],
          ...nodes.map(n => [n.lat, n.lng] as [number, number]),
          ...routes.flatMap(r =>
            r.geometry.coordinates.map(([lng, lat]) => [lat, lng] as [number, number])
          ),
        ];
        map.fitBounds(L.latLngBounds(allLatLngs), { padding: [30, 30], maxZoom: 10 });
      } catch { /* ignore */ }
    }

    drawOverlays();
  }, [mapData, mapLoaded, selectedRouteId, layersVisibility, onSelectRoute]);

  const fitScenario = async () => {
    if (!mapRef.current) return;
    const L = (await import("leaflet")).default;
    const { routes, nodes, origin, destination } = mapData;
    const all = [
      [origin.lat, origin.lng] as [number, number],
      [destination.lat, destination.lng] as [number, number],
      ...nodes.map(n => [n.lat, n.lng] as [number, number]),
      ...routes.flatMap(r => r.geometry.coordinates.map(([lng, lat]) => [lat, lng] as [number, number])),
    ];
    mapRef.current.fitBounds(L.latLngBounds(all), { padding: [30, 30], maxZoom: 10 });
  };

  const resetView = () => {
    mapRef.current?.setView([34.65, 77.85], 8);
  };

  return (
    <div className="maya-map-wrapper" style={{ position: "relative", width: "100%" }}>
      {/* Leaflet CSS workaround for icon paths */}
      <style>{`
        .leaflet-container { background: #080e17 !important; font-family: 'JetBrains Mono', monospace; }
        .leaflet-tile-pane { filter: brightness(0.85) saturate(1.1); }
        .leaflet-control-attribution { background: rgba(9,14,23,0.85) !important; color: #637488 !important; font-family: 'JetBrains Mono', monospace; font-size: 8px; }
        .leaflet-control-attribution a { color: #70d7ff !important; }
        .leaflet-bar a { background: #181d28 !important; color: #70d7ff !important; border-color: #293544 !important; }
        .leaflet-bar a:hover { background: #202735 !important; }
        .maya-tooltip { background: #101722 !important; border: 1px solid #293544 !important; color: #dfe7f1 !important; font-family: 'JetBrains Mono', monospace; font-size: 10px; border-radius: 0; padding: 4px 8px; }
        .maya-tooltip::before { display: none; }
        .leaflet-popup-content-wrapper { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0; border-radius: 0; }
        .leaflet-popup-tip { display: none; }
        .leaflet-popup-content { margin: 0; }
      `}</style>

      {/* Toolbar */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"8px 12px", background:"#101722", borderBottom:"1px solid #293544", fontFamily:"'JetBrains Mono',monospace", fontSize:"10px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
          <span style={{ color:"#70d7ff", fontWeight:700 }}>SYNTHETIC SCENARIO</span>
          <span style={{ color:"#8796a8" }}>|</span>
          <span style={{ color:"#4be277" }}>REAL BASEMAP · WORLD MAP</span>
          <span style={{ padding:"2px 6px", background: isOnline ? "#102319" : "#2a141c", color: isOnline ? "#4be277" : "#ff7183", border:`1px solid ${isOnline ? "#265e3b" : "#703140"}`, fontWeight:600 }}>
            {isOnline ? "LIVE" : "OFFLINE — CACHED"}
          </span>
        </div>
        <div style={{ display:"flex", gap:"6px" }}>
          <button onClick={fitScenario} style={{ background:"#202735", color:"#70d7ff", border:"1px solid #38556a", padding:"4px 8px", fontSize:"9px", fontWeight:600, cursor:"pointer" }}>FIT SCENARIO</button>
          <button onClick={resetView} style={{ background:"#202735", color:"#dfe7f1", border:"1px solid #293544", padding:"4px 8px", fontSize:"9px", fontWeight:600, cursor:"pointer" }}>RESET VIEW</button>
        </div>
      </div>

      {/* Layer toggles */}
      <div style={{ display:"flex", gap:"12px", padding:"5px 12px", background:"#0a1019", borderBottom:"1px solid #293544", fontFamily:"'JetBrains Mono',monospace", fontSize:"9px", color:"#8796a8" }}>
        <span>LAYERS:</span>
        {(["routes","nodes","events"] as const).map(key => (
          <label key={key} style={{ display:"inline-flex", alignItems:"center", gap:"4px", cursor:"pointer" }}>
            <input type="checkbox" checked={layersVisibility[key]} onChange={e => setLayersVisibility(p => ({ ...p, [key]: e.target.checked }))} />
            <span style={{ color: key==="routes" ? "#70d7ff" : key==="nodes" ? "#4be277" : "#ff7183" }}>{key.toUpperCase()}</span>
          </label>
        ))}
      </div>

      {/* Map container */}
      <div ref={containerRef} className="synthetic-map" style={{ width:"100%", height:"560px", background:"#080e17" }} />
    </div>
  );
}
