# Maya Project Quality Gate and Verification Makefile
.PHONY: ci lint typecheck test openapi regression frontend-build frontend-test clean

# Root quality gate running all checks
ci: lint typecheck openapi test regression frontend-test frontend-build
	@echo "=================================================="
	@echo "  ALL QUALITY GATE CHECKS PASSED FOR PROJECT MAYA "
	@echo "=================================================="

# Linting
lint:
	@echo "Running backend lint (ruff)..."
	cd backend && .venv/bin/ruff check app tests
	@echo "Running frontend lint (eslint)..."
	cd frontend && npm run lint

# Typechecking
typecheck:
	@echo "Running backend typecheck (mypy)..."
	cd backend && .venv/bin/mypy app
	@echo "Running frontend typecheck (tsc)..."
	cd frontend && npm run typecheck

# OpenAPI contract export & validation
openapi:
	@echo "Exporting and validating frozen OpenAPI contract..."
	cd backend && .venv/bin/python scripts/export_openapi.py
	@test -f openapi.json
	@test -f backend/openapi.json
	@echo "OpenAPI contract validated successfully."

# Unit and API tests
test:
	@echo "Running backend pytest suite..."
	cd backend && .venv/bin/pytest

# Simulation regression tests
regression:
	@echo "Running simulation regression & agentic pattern tests..."
	cd backend && .venv/bin/pytest tests/test_agentic_patterns.py tests/test_domain_simulation.py -v

# Frontend tests
frontend-test:
	@echo "Running frontend unit & offline tests..."
	cd frontend && npm test

# Frontend build
frontend-build:
	@echo "Building Next.js frontend app..."
	cd frontend && npm run build

clean:
	rm -f backend/maya.db
	rm -rf backend/.pytest_cache backend/.ruff_cache backend/.mypy_cache
	rm -rf frontend/.next
