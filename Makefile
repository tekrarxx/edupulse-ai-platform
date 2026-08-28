.PHONY: up down logs migrate test test-api test-web lint format seed

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec api alembic upgrade head

test: test-api test-web

test-api:
	docker compose exec api pytest

test-web:
	docker compose exec web npm test

lint:
	docker compose exec api ruff check .
	docker compose exec web npm run lint

format:
	docker compose exec api ruff format .

seed:
	@echo "No seed data yet — curriculum seeding starts in Phase 3 (P2)."
