.PHONY: dev up down test api-spec
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
up:
	docker compose up --build -d
down:
	docker compose down
test:
	cd backend && python -m pytest -q
	cd frontend && npm run build
api-spec:
	python scripts/export_api.py
