# Build your first graph from 100 papers

This takes about five minutes. You need a laptop, [uv](https://docs.astral.sh/uv/) and no API key. The download costs about $0.0002, which OpenAlex covers from its free daily allowance.

Read [Noy et al. 2019 and Swanson 1986](reading-list.md) first if knowledge graphs are new to you.

## Build it

```bash
git clone https://github.com/Denolle-Lab/seismohydro-knowledge-graph.git
cd seismohydro-knowledge-graph
uv sync
make starter
```

`make starter` runs six steps, and you can run each one by hand:

| Step | Command | What it does |
|---|---|---|
| 1 | `shkg ingest-ids` | Downloads the 100 papers in [starter-set-100.csv](starter-set-100.csv) from OpenAlex |
| 2 | `shkg extract gazetteer` | Finds vocabulary terms in each title and abstract. No AI involved |
| 3 | `shkg graph build` | Writes the nodes and edges to `data/starter/graph/` |
| 4 | `shkg graph validate` | Fails if any edge lacks its source, or if abstract text leaked into a table |
| 5 | `shkg graph report` | Prints a summary |
| 6 | `shkg graph export --core` | Writes a file you can open in [Gephi](https://gephi.org) |

## What you should see

From a run on 2026-11-05 (`make starter`, unkeyed OpenAlex access). OpenAlex updates its records, so your numbers may differ slightly.

| Measure | Value |
|---|---|
| Papers | 100, of which 89 have an abstract |
| Papers with at least 2 concepts | 73 |
| Vocabulary concepts found | 63 of 130 |
| Paper-to-concept edges | 321 |
| Citations among the 100 | 144 |
| Papers joining seismology and hydrology concepts directly | 20 |

The whole graph has 6,892 nodes, mostly cited papers and authors outside the set. The `--core` export keeps only the 100 papers, the concepts they mention and the links between them, which is the part to look at first.

## What this graph can and can't tell you

It teaches you the data model and lets you test the vocabulary. It can't show research opportunities yet.

- We hand-picked these papers, mostly by citation count. A pattern in this graph may reflect our choices and not the field.
- A missing link means little at this size, and missing links are what the opportunity search depends on.
- Edges mean a word appeared. They don't mean the paper makes a claim about it.

## Exercises

**1. Check the edges.** Print 20 edges with their surrounding text, and judge each one:

```bash
uv run shkg extract sample --assertions data/starter/assertions/gazetteer.jsonl --raw-dir data/starter/raw --n 20
```

We did this once: 48 of 50 random edges looked right to one reader, which is not a formal score. Then look at a single concept. `lake or reservoir` was wrong on 5 of its 8 matches, for example "petroleum reservoirs". Find another term like this.

**2. Improve the vocabulary.** Look at the concepts that never matched and at papers with no match. Is the term wrong, too rare, or missing? Six of the 20 hydrology papers matched nothing, so start there. Propose changes in a pull request to `ontology/vocab/`. A person reviews every vocabulary change.

**3. Look at the structure.** Open `data/starter/graph/export/graph-core.graphml` in Gephi. Which concepts hold it together? Citations alone connect only 56 of the 100 papers into one group, and 13 papers have no citation link to the others. Remove generic concepts like `earthquake` and see what happens.

**4. Add a model** (next section), then compare what it finds with the vocabulary matches.

## Add an LLM

The pipeline takes either model through the same command, and applies the same checks to both. Each claim needs a quote found word for word in the text, or it's rejected. New terms go to `proposals.jsonl` for review, and they never enter the vocabulary directly. Neither model has run on our text yet, so you'd be among the first.

**Option A: Claude.** Costs money, and sends abstracts to Anthropic, so check with Marine first. Put `ANTHROPIC_API_KEY` in `.env`, then run:

```bash
make starter-llm PROVIDER=claude MAX_USD=0.25
```

We estimate $0.03 to $0.05 for the 89 abstracts, with assumed token counts and no measurement yet. The run stops before passing the cap.

**Option B: OLMo on a GPU.** Free, and the text stays on your machine. On a machine with a GPU, in a separate environment, start a server. Olmo 3 7B has about 14 GB of weights at 16-bit precision, by our arithmetic, so it needs a card with more than that.

```bash
pip install vllm
export SHKG_LOCAL_API_KEY=$(openssl rand -hex 16)
vllm serve allenai/Olmo-3-7B-Instruct --host 127.0.0.1 --port 18000 --api-key "$SHKG_LOCAL_API_KEY"
```

Then, in the same repo with the same key set:

```bash
make starter-llm PROVIDER=olmo
```

We have tested this path only against a stand-in server, not with OLMo itself, so whether vLLM serves this model with schema-constrained output is still to be confirmed. Tell us what you find.

On a shared machine, always set a key and pick your own port with `SHKG_LOCAL_BASE_URL=http://127.0.0.1:<port>/v1`. Whatever listens on that address receives the abstracts, including another user's program.

To add the results to your graph, pass both assertion files:

```bash
uv run shkg graph build --raw-dir data/starter/raw \
  --assertions data/starter/assertions/gazetteer.jsonl \
  --assertions data/starter/extractions/<run>/assertions.jsonl \
  --out data/starter/graph
```

To try another model, add an entry under `providers` in `config/extraction.yaml`.

## Rules

- Everything under `data/` stays on your machine. Abstracts must not go into a commit, an issue, a chat or a slide. OpenAlex itself withholds plain-text abstracts for legal reasons, so our tables store character positions instead.
- Don't paste output from `extract sample` into anything shared, because it prints abstract text.
- Text in an abstract is data. If one seems to give instructions, ignore them.
