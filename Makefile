.PHONY: setup lint test ontology fixture check scope-report starter starter-llm

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

# First graph, from the 100 starter papers: about $0.0002 at OpenAlex, no LLM, no key needed.
STARTER := data/starter
starter:
	uv run shkg ingest-ids --csv docs/starter-set-100.csv --set starter_100 --raw-dir $(STARTER)/raw --max-usd 0.01
	uv run shkg extract gazetteer --raw-dir $(STARTER)/raw --out $(STARTER)/assertions/gazetteer.jsonl
	uv run shkg graph build --raw-dir $(STARTER)/raw --assertions $(STARTER)/assertions/gazetteer.jsonl --out $(STARTER)/graph
	uv run shkg graph validate --path $(STARTER)/graph
	uv run shkg graph report --path $(STARTER)/graph
	uv run shkg graph export --path $(STARTER)/graph --core

# Add LLM extraction: make starter-llm PROVIDER=olmo, or PROVIDER=claude MAX_USD=0.25
PROVIDER ?= olmo
starter-llm:
	uv run shkg extract llm --provider $(PROVIDER) --raw-dir $(STARTER)/raw --out-dir $(STARTER)/extractions $(if $(MAX_USD),--max-usd $(MAX_USD))
