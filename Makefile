.PHONY: test test-all lint typecheck check fmt test-integration

test:
	uv run pytest -x -q

test-all:
	uv run pytest -v --cov=sdlc_control_plane

lint:
	uv run ruff check src/ tests/

typecheck:
	uv run mypy src/

check: lint typecheck test

test-integration:
	uv run pytest -m integration -v --override-ini="addopts="

fmt:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/
