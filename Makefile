.PHONY: setup lint test ontology fixture check scope-report

setup:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest

ontology:
	uv run shkg ontology validate

fixture:
	uv run shkg graph build --fixture
	uv run shkg graph validate --fixture

check: lint test ontology fixture

# Live call against OpenAlex, about $0.01.
scope-report:
	uv run shkg scope-report
