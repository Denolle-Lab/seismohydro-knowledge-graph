# Contributing

## Domain review

Vocabulary entries in `ontology/vocab/` start with `status: seed`. To review one, correct it and set `status: reviewed` in a pull request. Hydrology entries were drafted without a hydrologist and need the most attention.

Scale ranges on methods and sensors must cite a source in `scale.source`. Please leave a range empty rather than give an uncited number.

A coupling mechanism in `ontology/coupling/mechanisms.yaml` ends in one of two states: `reviewed`, with OpenAlex work IDs in `evidence`, or `unsupported`.

## Code

```bash
uv sync
make check
```

`make check` runs lint, offline tests, and ontology and fixture graph validation. Tests must not call live APIs; use `httpx.MockTransport`, as in `tests/test_budget.py`.

## Rules that CI enforces

- No abstract text in any published table. Offsets only. Test fixtures use synthetic text.
- Every L2 and L3 edge has a work ID, character offsets, extractor version, confidence and tier.
- Raw data is never uploaded as a workflow artifact.

## Spending money

Anything that calls a metered API goes through `BudgetGuard` and reads its cap from `config/budget.yaml`. Paste the manifest's `usd_spent` into the pull request that used the result.

## Numbers in documentation

State where each number came from: the data, the query or command, the date, and whether it was rerun or only read from a record.
