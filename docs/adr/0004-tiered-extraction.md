# ADR 0004: Tiered extraction, with the LLM on a subset

**Status:** accepted, 2026-11-03. Haiku 5.5 chosen by the PI the same day, subject to the gold-set check in M4.

**Context.** Running an LLM on every abstract would cost an estimated $118 on Haiku 5.5, and at least $4,728 on Opus 5.5 (assumed token counts, `ROADMAP.md`). Much of the value sits in a small share of works: 9,533 works match both fields' keywords, out of about 1M.

**Decision.** Metadata first, then vocabulary matching, then local embeddings. The LLM runs only on bridge works, a 5% stratified core sample and a 20% sample of the application sets, through batches with prompt caching, with output constrained to the schema frozen after the discovery pass (ADR 0006). New terms go to a review queue and never directly into a vocabulary. The extractor is Haiku 5.5, checked against a 300-abstract gold set. If it fails the thresholds, larger models run on the gold set only, and changing the bulk model is a new decision. Full text stays out unless M4 finds abstracts too thin.

**Consequences.** The first graph costs about $7 to $11 in LLM calls on Haiku 5.5, assuming thinking stays disabled. It would cost about $424 or more if only Opus 5.5 met the thresholds. Core works outside the sample have vocabulary matches only, so analysis must account for different extraction depth across tiers. About 40% of core works have no abstract and rely on titles and citations.
