# ADR 0007: Extraction models plug in behind one interface

**Status:** accepted, 2026-11-05, at the PI's request. Amends ADR 0004, which named Haiku 5.5 as the extractor.

**Context.** Haiku 5.5 is cheap but sends text to a provider and charges for every rerun. The lab has GPUs, and open models such as OLMo 3 would keep text local and make reruns free. Neither model's accuracy on this corpus is known. Comparing them is only fair if both get the same prompt and the same checks.

**Decision.** `extract/providers/` holds one adapter per kind of model behind a small `Provider` interface: send a request with a JSON schema, return parsed output, token counts and cost. There are two adapters, `claude` (official SDK) and `openai_compatible` (any local server, such as vLLM). `config/extraction.yaml` names the providers, and `--provider` picks one. Adapters do not touch vocabularies, offsets or graphs. `extract/llm.py` applies the same rules to every model:

- A claim needs a quote found verbatim in the text. Offsets are computed from it and the quote is discarded, so a model can't invent provenance and text doesn't reach the output.
- Edges only join known concepts. New terms go to `proposals.jsonl` for human review.
- Confidence is a fixed placeholder until the gold set scores the model.

Accuracy decides between models, measured on the M4 gold set per node type and predicate. GraphRAG stays out, as decided in ADR 0006.

**Consequences.** Adding a model takes one adapter, or only a config entry if it has an OpenAI-compatible server. Extractor version includes the provider, model and a hash of the prompt, so edges from different models stay distinguishable, and a changed prompt starts a new output directory. Whatever listens at a local `base_url` receives abstract text, so on a shared machine the server needs its own port and a key. Real-time calls are limited to 1,000 works for metered models, because they cost twice the batch price. Bulk runs on Claude still need Message Batches in M4.
