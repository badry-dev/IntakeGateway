.PHONY: dev worker scheduler fmt lint typecheck test test-cov test-fe audit build-docker up down

# ── Dev servers ───────────────────────────────────────────────────────────────
dev:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	cd backend && celery -A app.workers.celery_app.celery_app worker --loglevel=INFO --pool=solo --concurrency=1

scheduler:
	cd backend && python app/services/scheduler.py

# ── Code quality ──────────────────────────────────────────────────────────────
fmt:
	cd backend && ruff format app/ tests/

lint:
	cd backend && ruff check app/ tests/
	cd frontend && npm run lint

typecheck:
	cd frontend && npx tsc --noEmit

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	cd backend && python -m pytest tests/ -v

test-cov:
	cd backend && python -m pytest tests/ \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=50 \
		-v
	@echo "Coverage report: backend/htmlcov/index.html"

test-fe:
	cd frontend && npm test -- --run

# ── Security ──────────────────────────────────────────────────────────────────
audit:
	cd backend && pip-audit -r requirements.txt
	cd frontend && npm audit --audit-level=high

# ── Docker ────────────────────────────────────────────────────────────────────
build-docker:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down
