# Roadmap

The end product is a ranked, evidence-linked map of opportunities between seismology and hydrology, published with its graph and its evaluation. Acceptance thresholds below are proposals, to be adjusted as we learn. `roadmap/milestones.yaml` holds the same plan in a form that `scripts/bootstrap_github.py` turns into GitHub milestones and issues.

## Milestones

The order matters. The discovery pass in M3 samples using a score computed in M2. The gold set in M4 can't be annotated until M3 freezes the schema, and part of it comes from the M2 citation graph. Surveying existing ontologies can start at any time.

| Milestone | Delivers | Done when | API cost |
|---|---|---|---|
| M0 Scaffold | Repo structure, metered client, schema, fixture graph, CI | CI passes on the first push | $0 |
| M1 Scope and ingest | Adjudicated scope, about 1M works, coverage by journal and era | At least 95% recall on 50 hand-picked canary DOIs, and at least 90% precision on 200 random works per set | About $2 |
| M2 Bibliographic graph | L0 graph, cross-domain citation flow by year, work-level interdisciplinarity score | Edge counts reconcile with `referenced_works`, in-corpus citation share is reported, and the score is stable under resampling | $0 |
| M3 Discovery and ontology | Open extraction on 4,000 abstracts, saturation curves, merged concepts, frozen node types and predicates, sourced scale ranges | New concepts per 100 abstracts is near flat in each stratum; one seismologist and one hydrologist have reviewed it; mappings validate | About $1 to $2 |
| M4 Extraction | Vocabulary matching on all works, 300-abstract gold set, Haiku 5.5 checked against it, then run on a subset, scored statistical edges | Double annotation with kappa reported; entity precision at least 0.85 and relation precision at least 0.75 in each domain; graph-quality scores reported | About $7 to $11 |
| M5 Coupling layer | Mechanisms with evidence, variable crosswalk, unified graph | Each seed mechanism has reviewed evidence or is marked unsupported | $0 |
| M6 Opportunity map | Scores for the four opportunity classes, holdout test, expert panel | Beats preferential attachment at the 2015 cutoff, canaries recovered, panel ratings reported | Under $1 |
| M7 Release and automation | Zenodo DOI, public explorer, scheduled refresh, manuscript | Clean release rebuild from a tag, and one refresh cycle under its cap | About $1 per quarter |

## What each milestone has to answer

**M1.** Does the scope hold? The seed scope is a measured starting point and has not been audited. The main checks are how much earthquake engineering and water treatment leak in, how much of the application sets is off topic, and whether abstract coverage differs by journal. If one major hydrology journal lacks abstracts, hydrology will look under-studied for reasons that have nothing to do with science.

**M2.** How much do the two fields cite each other, and has that changed? This is the first scientific result, and it needs no LLM. M2 also scores each work on how much it spans the fields, from how its references split, which vocabularies it mixes, and who cites it. Seismohydrology is then measured rather than assumed from a keyword intersection, which also tests whether it is a coherent field at all.

**M3.** What nodes and edges does the literature itself support? Hand-seeded concepts would mostly return what we put in, so open extraction comes before the schema is frozen. Saturation curves decide how large the vocabulary needs to be. The [100-paper starter set](docs/starter-set-100.md) can pilot this before the full run. The pass also tests the 18 proposed node types and shows how many of the hand-written seeds appear bottom-up. SWEET and the CSDMS Standard Names cover seismic phenomena and quantities, but we have not found formal coverage of seismological methods or sensors, so that part probably has to be built here.

**M4.** Is Haiku 5.5 good enough? It is the chosen extractor, and the gold set checks it against the thresholds. If it fails, Sonnet 5.5 and Opus 5.5 run on the gold set only (about $3.50), and moving bulk extraction to either one is a separate decision. The gold set is mostly bridge papers, but it keeps single-domain strata because a missed mention in one field later looks like a research gap.

**M5.** Which mechanisms have real support? The 11 seeds in `ontology/coupling/mechanisms.yaml` come with raw keyword counts and no precision check.

**M6.** Do the predictions beat a trivial baseline on literature that has already appeared? If not, the method changes before anyone reads the ranked list.

## Costs

Rates are from the [OpenAlex price list](https://help.openalex.org/access/example-costs/), and corpus counts are from `docs/scoping-2026-11-03.md`.

**OpenAlex.** Costs below are upper bounds, because sets can overlap and a work repeated across sets is downloaded twice.

| Sets | Works | Calls | Cost |
|---|---|---|---|
| Core | 913,778 | 9,138 list | $0.91 |
| Bridge | 23,998 | 241 search | $0.24 |
| Application, crossed with keywords | 70,520 | 706 search | $0.71 |
| Total | 1,008,296 | | $1.86 |

A free key allows $1 per day, so the first download takes two days and resumes on its own.

**LLM extraction.** Haiku 5.5 is the chosen model; the other rows show what a fallback would cost. Token counts of 1,850 input and 400 output per abstract are assumptions, to be replaced with measurements at M4, and they assume no thinking tokens, so Haiku runs with thinking disabled unless the gold set says otherwise. Prices are list prices with the 50% batch discount. Opus 5.5 cannot disable thinking, so its figures are lower bounds.

The subset is about 55k abstracts: up to about 18k bridge, about 27k from a 5% core sample, and about 10k from a 20% application sample. The full corpus is about 614k.

| Model | Per abstract | Subset (about 55k) | All abstracts (about 614k) |
|---|---|---|---|
| Haiku 5.5 | $0.00019 | $11 | $118 |
| Haiku 5.5, with prompt caching | $0.00013 | $7 | $77 |
| Sonnet 5.5 | $0.0039 | $212 | $2,364 |
| Opus 5.5 | at least $0.0077 | at least $424 | at least $4,728 |

The caching row assumes about 1,500 of the 1,850 input tokens are a shared prefix read at 0.1 times the input price, with the batch discount stacking on top. Check the real hit rate in the first batch. The discovery pass adds about $0.80 for 4,000 abstracts, perhaps double because open extraction returns more.

Full text is out of the first pass. OpenAlex charges $0.01 per TEI XML file, so the top 500 bridge papers would cost $5. M4 decides whether abstracts are too thin for methods.

## Automation

| Stage | How it runs | Human gate |
|---|---|---|
| Lint, tests, schema and fixture checks | `ci.yml` on every push and pull request | Pull request review |
| Monthly refresh, trailing 24 months | `refresh.yml` | Off until `ENABLE_SCHEDULED_RUNS` is set to `true` |
| Quarterly full rebuild, after the OpenAlex snapshot date | `rebuild.yml` | Off until `ENABLE_SCHEDULED_RUNS` is set to `true` |
| LLM extraction | `extract.yml`, manual dispatch only | Required reviewer on the `paid-runs` environment |
| Vocabulary and mechanism changes | Pull requests on `ontology/` | Domain reviewer. LLM proposals never merge on their own |
| Release | `release.yml` on a tag | Whoever pushes the tag |

The free tier blocks `from_updated_date` and `from_created_date`, which return HTTP 429. That is why refresh uses a trailing publication window, and why works updated without a new publication date only change at the quarterly rebuild.

A full rebuild costs more than the $1 free daily budget and a CI runner cannot resume on a later day, so `rebuild.yml` needs a small [prepaid balance](https://help.openalex.org/access/pricing/), about $1 per quarter. The first ingest can run on a laptop over two days instead.

## Before automation goes live

1. Add `OPENALEX_API_KEY` as a repository secret.
2. Create the `paid-runs` environment with a required reviewer, and add `ANTHROPIC_API_KEY` to it at M3.
3. Set the repository variable `ENABLE_SCHEDULED_RUNS` to `true` once M1 has passed.
4. Enable the Zenodo integration for the repository before the first tagged release.
