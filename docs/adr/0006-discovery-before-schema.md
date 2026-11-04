# ADR 0006: Discover nodes and edges before freezing the schema

**Status:** accepted, 2026-11-03.

**Context.** The first scaffold seeded concepts by hand and constrained the LLM to that schema. A graph built that way mostly returns what was put in, and cannot show that a term, a node type or a relation is missing. Its target of 150 to 300 concepts per domain was also a guess.

**Decision.** Candidates come from four independent sources: OpenAlex keywords, noun phrases, existing ontologies, and open LLM extraction on 4,000 stratified abstracts. Synonyms are merged with local embeddings and human approval. Each concept is assigned to seismology, hydrology or shared by its enrichment across the corpora, and terms with different meanings in each field stay split. Predicates are derived by clustering verbs from the open pass and frozen at about 8 to 12. Saturation curves decide when the vocabulary is large enough. Seismohydrology is defined by a work-level score from M2, not by a keyword intersection.

Edges come in three kinds, kept separate: statistical associations, typed claims supported by at least two works from independent author groups, and curated physical couplings. The first two describe what people wrote and the third describes the physics. Candidate graphs are scored on coverage, saturation, stability, specificity, prediction and expert validity (`docs/design.md`).

**Alternative considered.** Microsoft GraphRAG. It is built for answering questions over text and does not address which nodes and edges represent a literature. It also keeps raw text in its output tables, records no character offsets, and merges entities only on exact title and type. Its query layer is not needed for now and could be revisited after M5 through its "bring your own graph" mode.

**Consequences.** M3 now depends on M2, and the gold set depends on both, so annotation starts later. Discovery adds about $1 to $2. The schema in `ontology/schema/` and the seeds in `ontology/vocab/` are hypotheses until M3 tests them. The metrics and methods named here have not yet been run on this corpus, and thresholds need the first real run.
