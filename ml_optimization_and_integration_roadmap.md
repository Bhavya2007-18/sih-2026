# SIH26251: Indian Army - Predictive Logistics & Forward Supply Chain
## Implementation Roadmap: ML, Optimization, and End-to-End Integration

---

### Part 1: Member 1 (ML) — Forecasting & Risk Engine
**Focus:** Demand prediction, shortage alerting, anomaly detection, and route risk scoring.

- [ ] **Phase 1: Baseline Models & Data Ingestion (Days 1–3)**
  - [ ] Set up ML script structure (`/ml_models` folder, pandas, scikit-learn, statsmodels/Prophet).
  - [ ] Build historical data loaders that pull time-series consumption logs from the PostgreSQL database per forward base and supply class (Rations, POL, Ammo, Medical).
  - [ ] Train baseline demand forecasting models (e.g., Exponential Smoothing, ARIMA, or lightweight gradient boosting regressors) to output 7-day and 14-day forward consumption predictions.

- [ ] **Phase 2: Shortage & Days of Supply (DOS) Engine (Days 4–6)**
  - [ ] Implement the Days of Supply (DOS) calculation logic: $\text{DOS} = \frac{\text{Current Stock}}{\text{Predicted Daily Consumption Rate}}$.
  - [ ] Build automated alert thresholds (e.g., $\text{DOS} < 3$ days triggers "Critical Shortage", $\text{DOS} \in [3, 5]$ days triggers "Warning").
  - [ ] Develop an anomaly detection script to flag sudden, abnormal consumption spikes caused by unexpected operational tempo changes.

- [ ] **Phase 3: Route & Environmental Risk Scoring (Days 7–9)**
  - [ ] Build a heuristic/ML scoring function that evaluates route vulnerability based on synthetic weather indexes (snowstorms, heavy rain/landslides), terrain difficulty, and historical disruption frequency.
  - [ ] Output a composite risk score (`Low`, `Medium`, `Critical`) for every transit leg in the network topology.

- [ ] **Phase 4: API Serialization & Model Serving (Days 10–12)**
  - [ ] Package ML inference logic into clean Python functions/classes that the Backend member can easily import or expose via FastAPI endpoints.
  - [ ] Optimize inference latency to ensure real-time response when the frontend requests updated forecasts.

---

### Part 2: Member 2 (Optimization) — Recommendation & Decision Engine
**Focus:** Multi-depot inventory allocation, vehicle load matching, route optimization, and explanation generation.

- [ ] **Phase 1: Constraint Formulation & Solver Setup (Days 1–3)**
  - [ ] Install and configure optimization libraries (e.g., Google OR-Tools, PuLP, or NetworkX for graph routing).
  - [ ] Define mathematical constraints for the logistics network:
    - *Supply constraint:* Depot inventory cannot exceed available stock.
    - *Demand constraint:* Forward base shortfalls must be satisfied.
    - *Capacity constraint:* Transport vehicle/load weight limits.

- [ ] **Phase 2: The Recommendation Matrix Engine (Days 4–6)**
  - [ ] Build the core allocation algorithm matching forward base shortages to optimal source depots.
  - [ ] Implement multi-objective scoring balancing distance, transit time, inventory availability, and route risk scores (from the ML layer).

- [ ] **Phase 3: Alternative Routing & ETA Calculator (Days 7–9)**
  - [ ] Implement shortest-path algorithms (e.g., Dijkstra's / A* via NetworkX) to calculate primary routes and secondary/alternative fallback paths.
  - [ ] Compute dynamic Estimated Time of Arrival (ETA) deltas based on terrain and weather delays.

- [ ] **Phase 4: Explainable AI "Why" Generator (Days 10–12)**
  - [ ] Build a rule-based or template-driven text generator that translates solver decisions into plain-language justification cards (e.g., *"Recommended Depot C instead of Depot A because Route A is flagged for landslide risk, saving 4 hours despite a slightly longer distance"*).
  - [ ] Integrate optimization output payloads cleanly with FastAPI endpoints.

---

### Part 3: Phase 6 — End-to-End Integration & Polish (Days 13–15)
**Focus:** System-wide integration, demo scenario staging, and final pitch alignment for the entire team.

- [ ] **Team Integration & End-to-End Wiring (Days 13–14)**
  - [ ] **Full Stack Hookup:** Connect Next.js frontend UI components to FastAPI live inference loops ($\text{Dashboard} \rightarrow \text{Backend} \rightarrow \text{ML/Optimization} \rightarrow \text{Frontend UI}$).
  - [ ] **What-If Simulator Pipeline Test:** Verify that toggling a simulation parameter on the frontend successfully triggers the backend state-forking sandbox and instantly updates map risk states and shortage metrics.
  - [ ] **Docker Compose Verification:** Run a full local build via `docker-compose up` to ensure PostgreSQL, FastAPI, and Next.js spin up smoothly on a clean machine without environment errors.

- [ ] **Demo Scenario Staging & Polish (Day 15)**
  - [ ] **Pre-Baked Demo State:** Seed the database with a striking, high-impact scenario ready for judges (e.g., High-altitude mountain pass Route A blocked by a synthetic blizzard, causing a critical ammunition and ration shortage at Forward Base B, automatically resolved by the engine via alternative Route C).
  - [ ] **UI Polish & Error Handling:** Add loading skeletons, clean toast notifications, and ensure zero console errors during live interaction.
  - [ ] **Pitch & Presentation Alignment:** Align the frontend dashboard views directly with the pitch deck narrative ($\text{Predict} \rightarrow \text{Optimize} \rightarrow \text{Simulate} \rightarrow \text{Recommend}$). Practice the live demo flow.