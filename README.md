# Seismohydro knowledge graph

Seismology and hydrology study the same subsurface with different sensors, vocabularies and physics. This project builds a knowledge graph of each discipline from the scientific literature, joins them through an explicit layer describing how water and elastic waves interact, and uses the result to find research opportunities between the two fields.

**Status:** scaffold (milestone M0). Nothing has been ingested at scale yet, and the opportunity map does not exist yet. See [ROADMAP.md](ROADMAP.md).

## How the graph is organized

| Layer | Contents | Source |
|---|---|---|
| L0 Bibliographic | Works, authors, institutions, journals, topics, citations | OpenAlex |
| L1 Domain vocabularies | Separate seismology and hydrology concepts, plus cross-cutting ones such as research approach, task, gap and decision ([node types](docs/node-types.md)) | Curated in `ontology/vocab/` |
| L2 Literature assertions | Which work uses which method on which variable | Vocabulary matching, then an LLM on a subset |
| L3 Coupling | Shared state variables, compartments, scale ranges, and mechanisms linking water and waves | Curated in `ontology/coupling/`, with evidence from L2 |

The governing equations are not merged. An elastic wave equation and the Richards equation stay separate nodes, connected only through what they share: pore pressure, saturation, effective stress, mass load, strain and permeability, in a common compartment and at overlapping scales. [docs/design.md](docs/design.md) explains why.

Every L2 and L3 edge records the work it came from, character offsets, extractor version, confidence and tier. An edge without that record fails validation.

## Quick start

You need [uv](https://docs.astral.sh/uv/).

```bash
uv sync
make check                     # lint, offline tests, ontology and fixture graph validation
uv run shkg scope-report       # live corpus counts and cost estimate, about $0.01, no key needed
```

To download the corpus, get a free [OpenAlex API key](https://openalex.org/settings/api), put it in `.env` (see `.env.example`), and run:

```bash
uv run shkg ingest             # stops at the budget cap, run again to resume
uv run shkg graph build
uv run shkg graph validate
```

## Pipeline

| Command | Does | Cost | Available |
|---|---|---|---|
| `shkg scope-report` | Counts each corpus set, compares with the baseline | About $0.01 | Now |
| `shkg ingest` | Downloads works, resumable | Up to $1.86 for the full corpus | Now, needs a key |
| `shkg graph build`, `validate`, `export` | Builds Parquet tables, checks them, exports to Neo4j or GraphML | Local | Now |
| `shkg ontology validate` | Checks vocabularies against the LinkML schema | Local | Now |
| `shkg extract gazetteer` | Matches vocabulary terms in text | Local | M4 |
| `shkg extract discovery` | Open extraction on 4,000 abstracts, before the schema is frozen | About $1 to $2 | M3 |
| `shkg extract llm` | Extracts assertions on a subset, with Haiku 5.5 | About $7 to $11 | M4 |
| `shkg opportunities`, `shkg holdout` | Scores opportunities and tests them against later literature | Under $1 | M6 |

Each stage writes a manifest to `data/manifests/` with the git commit, config hash, counts and dollars spent.

## Rules for working with the data

Raw OpenAlex records and reconstructed abstracts stay in the gitignored `data/` directory. OpenAlex does not distribute plaintext abstracts, for legal reasons, so neither do we: public tables hold IDs, character offsets and extracted terms. `shkg graph validate` fails on abstract text, and raw files must never be uploaded as workflow artifacts, because artifacts on a public repository can be downloaded by others.

Anything that spends money has a cap in `config/budget.yaml`. LLM runs start only by manual dispatch with a reviewer's approval.

## Repository map

| Path | Holds |
|---|---|
| `config/` | Corpus scope, budgets, extraction settings |
| `ontology/` | LinkML schema, vocabularies, coupling mechanisms, mappings to external ontologies |
| `src/seismohydro_kg/` | Pipeline code |
| `docs/` | Design, scoping measurements, decision records |
| `roadmap/milestones.yaml` | Machine-readable roadmap, used to create GitHub milestones and issues |
| `.github/workflows/` | CI, scheduled refresh and rebuild, gated LLM extraction, release |

## New to knowledge graphs?

Start with the [reading list](docs/reading-list.md), a short path from undergraduate to graduate level.

## New to the science?

The [starter set](docs/starter-set-100.md) is 100 papers across seismology, hydrology and the work between them, chosen as an entry point to about 1M works.

## Contributing

Domain review is the most useful contribution right now, particularly of `ontology/vocab/hydrology.yaml`, which was drafted without a hydrologist. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Code: BSD 3-Clause ([LICENSE](LICENSE)). Derived data: CC BY 4.0 ([LICENSE-DATA](LICENSE-DATA)). OpenAlex metadata is CC0.
