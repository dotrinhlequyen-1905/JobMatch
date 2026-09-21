.PHONY: dev stop migrate test lint

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

stop:
	docker compose down

migrate:
	docker compose exec backend alembic upgrade head

migrate-create:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

test:
	docker compose exec backend pytest

lint-backend:
	docker compose exec backend ruff check .

lint-frontend:
	docker compose exec frontend npm run lint
