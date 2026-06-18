.PHONY: install run worker test lint format typecheck train evaluate docker-up docker-down

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload

worker:
	python scripts/run_worker.py

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy app

train:
	python scripts/train_model.py

evaluate:
	python scripts/evaluate_model.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down --remove-orphans
