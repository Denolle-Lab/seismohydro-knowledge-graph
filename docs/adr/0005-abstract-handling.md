# ADR 0005: Abstracts stay local, public tables hold offsets

**Status:** accepted, 2026-11-03.

**Context.** OpenAlex ships abstracts only as inverted indexes and states that it does not ship plaintext "for legal reasons". Publishers hold copyright on much of this text. This repository is public, and artifacts on a public repository can be downloaded by others.

**Decision.** Raw records and reconstructed abstracts stay in gitignored `data/`. Published tables hold IDs, character offsets and extracted terms. Gold annotations store offsets and rehydrate locally. `check_no_abstract_text` rejects forbidden columns and overlong cells, and rejects exact abstract fragments when given the abstracts to compare with. Workflows upload graph tables and manifests only, never raw data.

**Consequences.** Anyone reproducing the graph or checking evidence has to fetch abstracts from OpenAlex. Offsets can go stale if an upstream abstract changes, and `rehydrate` detects the cases where they no longer fit. Short extracted terms are published, on the view that they are facts and not substantial quotation. That view has had no legal review, so please raise it before a large public release. Abstracts sent to an LLM provider leave our machines under that provider's data terms, which M4 should check.
