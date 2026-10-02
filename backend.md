Phase 1: Database Schema & Architecture Setup (Days 1–2)
Focus: Establish the relational database structure to support nodes, inventory classes, time-series telemetry, and routes.
[ ] PostgreSQL Setup & Connection: Initialize PostgreSQL database (local or Docker) and configure connection pooling via SQLAlchemy or SQLModel/Tortoise ORM.
[ ] Core Database Models Design:
Nodes: ID, name, tier (Central Depot, Regional Hub, Forward Base), coordinates (lat/lng), sector sector.
Inventory: Node ID, supply class (Class I Rations, Class III POL, Class V Ammo, Class VIII Medical), current stock, capacity, safety threshold.
Routes: Source ID, target ID, distance, base transit time, terrain type, current risk status (Open, Warning, Blocked).
TelemetryLogs: Timestamp, node ID, consumption rate, weather condition index, operational tempo multiplier.
[ ] Database Migration Scripts: Set up Alembic for smooth schema migrations.
Phase 2: Synthetic Data & Digital Twin Generator (Days 3–4)
Focus: Build the data pipeline that seeds realistic time-series data to power the ML and simulation layers.
[ ] Topography & Topology Seed Script: Write a Python script to populate the database with a realistic network topology (e.g., 2 Central Depots, 4 Regional Hubs, 10 Forward Bases).
[ ] Historical Time-Series Generator: Generate past 30-day synthetic logs for daily consumption rates, incorporating realistic noise, weekend dips, and weather variance.
[ ] Dynamic Scenario Seeder: Create modular script functions to inject baseline disruptions (e.g., sudden weather warnings closing a mountain pass route).
Phase 3: FastAPI Core & REST Endpoints (Days 5–6)
Focus: Build the high-performance async API layer to serve frontend requests and handle system telemetry.
[ ] FastAPI Project Structure: Set up modular routers (/nodes, /inventory, /routes, forecast, simulation).
[ ] Core CRUD Endpoints:
GET /api/nodes: Fetch all network nodes with their current inventory and health status.
GET /api/nodes/{id}: Detailed drill-down for a specific forward base (inventory breakdown, incoming convoys).
GET /api/routes: Fetch transit legs, distances, and current risk scores.
[ ] Pydantic Validation Schemas: Define strict request/response validation models to ensure clean data contracts with the frontend team.
Phase 4: ML Inference & Optimization API Integration (Days 7–9)
Focus: Wrap the ML forecasting models and optimization solvers into clean API endpoints.
[ ] Forecasting Endpoint (/api/forecast): Connect ML demand models to compute 7-day and 14-day requirements per forward base based on historical logs.
[ ] Recommendation Engine API (/api/recommendations): Implement the logic that evaluates stock deficiencies vs. Days of Supply (DOS) and outputs:
What to move, where, when, and why.
Automated source depot pairing using distance/risk heuristics.
[ ] Explainable AI Justification Builder: Generate the structured "Why" strings for recommendations (e.g., factoring route risk scores and ETA penalties).
Phase 5: The What-If Simulation Engine (Days 10–12)
Focus: Build the state-forking backend logic to handle real-time stress tests.
[ ] Simulation Router (/api/simulate): Accept incoming simulation override parameters from the frontend:
Demand spikes (percentage increase on specific nodes).
Route blockages (disabling specific transit edges).
Transit delays (adding hours to specific routes).
[ ] State-Forking Sandbox Logic: Build an in-memory or transactional sandbox pipeline that recalculates shortages, cascades bottlenecks through connected nodes, and generates fallback routing paths without permanently corrupting live database states.
[ ] Simulation Response Payload: Return comparison payloads showing "Before vs. After" impact metrics (e.g., new critical stockout count, delayed deliveries).
Phase 6: Integration, Dockerization & Polish (Days 13–15)
Focus: Containerize the backend stack, optimize query performance, and run end-to-end integration tests.
[ ] Docker & Docker Compose: Create a clean Dockerfile for FastAPI and a docker-compose.yml file combining PostgreSQL and FastAPI for effortless one-command deployment during judging.
[ ] CORS & Middleware Setup: Configure CORS properly to allow seamless communication with the Next.js frontend.
[ ] Performance & Error Handling: Add global exception handlers, request logging, and optimize database queries with proper indexing.
[ ] Live Demo Seeding: Pre-bake database states and simulation presets so the backend instantly returns high-impact data when judges trigger test scenarios.

