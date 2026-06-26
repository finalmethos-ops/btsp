.PHONY: help up down logs backend frontend test lint format migrate

help:
	@echo "BTSP commands"
	@echo "  make up        Start local stack"
	@echo "  make down      Stop local stack"
	@echo "  make logs      Tail stack logs"
	@echo "  make test      Run backend and frontend tests"
	@echo "  make lint      Run lint checks"
	@echo "  make migrate   Run database migrations"

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend:
	cd backend && uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest
	cd frontend && npm test -- --run

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint

format:
	cd backend && ruff format app tests
	cd frontend && npm run format

migrate:
	cd backend && alembic upgrade head
