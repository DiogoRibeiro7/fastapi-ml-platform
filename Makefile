.PHONY: install run test lint format typecheck train docker-up docker-down

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload

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

docker-up:
	docker compose up --build

docker-down:
	docker compose down --remove-orphans
