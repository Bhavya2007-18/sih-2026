Phase 1: Project Setup & Core Shell (Days 1–2)
Focus: Establish the Next.js project structure, design system, and global layout.
[ ] Initialize Repository & UI Framework: Set up Next.js (App Router), Tailwind CSS, and icon libraries (e.g., Lucide React).
[ ] Design System & Theme: Establish a Military/Defense C2 (Command & Control) aesthetic—dark mode by default, high-contrast text, slate/zinc color palettes, and distinct status color codes (Emerald for secure, Amber for warning, Red for critical/high risk).
[ ] App Layout & Navigation: Build the core layout shell containing a collapsible sidebar navigation (Dashboard, Supply Nodes, Risk Matrix, Simulator, Logs) and a top navbar displaying system clock, active sector status, and system alerts ticker.
Phase 2: GIS Map & Strategic Overview (Days 3–6)
Focus: Build the macro-level command center map and network visualization.
[ ] Interactive Vector Map Integration: Integrate a mapping library (e.g., Mapbox GL JS, Leaflet, or Deck.gl) styled with a custom dark/tactical map theme.
[ ] Node & Route Rendering: Plot Tier-1 Depots, Tier-2 Hubs, and Tier-3 Forward Bases onto the map using custom icons or color-coded status markers. Render supply transit paths (routes) between nodes.
[ ] Risk Heatmaps & Overlays: Add toggleable map layers for route risk (e.g., red overlays on blocked or high-risk mountain passes) and weather disruptions.
[ ] Quick-Glance KPI Cards: Build top-level summary metrics cards on the dashboard view:
Total Active Convoys
Critical Supply Shortages (FOBs at risk)
Average Network Supply Health (%)
Active Route Disruptions
Phase 3: Tactical Drill-Down & Recommendation Engine UI (Days 7–9)
Focus: Build the micro-level decision UI that answers "What to move, where, when, and why."
[ ] Forward Base Detail Drawer/Modal: When a user clicks a map node or table row, open a detailed panel showing:
Current inventory levels across supply classes (Rations, Fuel, Ammunition, Medical).
7-day predicted consumption vs. current stock (Days of Supply remaining).
[ ] The Recommendation Card UI: Display the AI-generated supply recommendation clearly:
Target: Forward Base B
Action: Recommended replenishment (e.g., +500 units from Depot A).
ETA & Route: Estimated delivery time and alternative route choices.
[ ] Explainable AI "Why" Box: Build a dedicated UI block detailing the reasoning behind the recommendation (e.g., "Lower predicted delay/risk on Route C").
[ ] Actionable Workflow Buttons: Add interactive "Approve Recommendation" and "Override / Modify Allocation" buttons that trigger API confirmation calls.
Phase 4: The What-If Simulator Interface (Days 10–12)
Focus: Build the interactive sandbox where judges can stress-test the system.
[ ] Simulator Control Panel: Design a side panel or modal containing interactive sliders, toggles, and dropdown inputs for scenario testing:
Demand Surge Slider: (e.g., $+10\%$ to $+50\%$ operational tempo spike at a specific base).
Route Blockage Toggle: Checkboxes to disable specific transit legs (e.g., "Close Mountain Pass Route A").
Delay Injector: Number input to add unexpected transit delays (e.g., $+48$ hours).
[ ] Scenario Execution & Comparison View: Build a trigger button ("Run Simulation") that sends parameters to the FastAPI backend and displays side-by-side or cascading visual impact updates (e.g., highlighting newly failing nodes in red).
Phase 5: API Integration, State Management & Polish (Days 13–15)
Focus: Connecting frontend components to the live backend, handling loading states, and demo prep.
[ ] API Client Setup: Configure Axios or native fetch utilities to connect Next.js smoothly to FastAPI endpoints (/api/nodes, /api/forecast, /api/recommendations, /api/simulate).
[ ] Real-time / Polling State: Implement state management (React Query or Zustand) to fetch and refresh telemetry data cleanly.
[ ] UI Polish & Error Handling: Add skeleton loaders, toast notifications for "Recommendation Approved", and graceful error handling if backend inference fails.
[ ] Demo Scenario Pre-sets: Build quick-action preset buttons in the UI for the final pitch presentation (e.g., "Load Demo Scenario: High-Altitude Pass Washout + Ammunition Surge").

