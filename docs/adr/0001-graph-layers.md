# ADR 0001: Four graph layers

**Status:** accepted, 2026-11-03.

**Context.** Bibliographic facts, curated concepts, claims extracted from text and physical couplings differ in how far they can be trusted and how often they change.

**Decision.** Separate L0 (bibliographic), L1 (domain vocabularies), L2 (literature assertions) and L3 (coupling). Every edge records its layer and tier, and every L2 and L3 edge has provenance.

**Consequences.** A low-confidence LLM claim cannot be confused with a citation. Any layer can be rebuilt without the others, so we can compare vocabulary-only graphs against LLM graphs in the holdout test. Queries that cross layers must filter on them.
