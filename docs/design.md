# Design

## The problem

Seismology and hydrology each have rich methods, their own ontologies and sensors, and governing equations that do not look alike: elastic wave propagation is hyperbolic and runs from milliseconds to hours, while groundwater and unsaturated flow are parabolic and run from hours to decades. Yet both act on the same subsurface. Water changes wave speeds, loads the crust and triggers earthquakes; earthquakes change permeability, well levels and streamflow; rivers generate seismic noise. The graph needs to keep each field intact and still represent that shared system.

## Four layers

| Layer | Nodes | Edges | Built from |
|---|---|---|---|
| L0 Bibliographic | Work, Author, Institution, Source, Topic | cites, authored, affiliated_with, published_in, has_topic | OpenAlex |
| L1 Domain vocabularies | Sensor, Observable, Dataset, StateVariable, Compartment, Process, Hazard, Task, Method, PhysicalModel, Software, ResearchApproach, Gap, Setting, Region, Event, DecisionDomain, Decision (defined in `docs/node-types.md`) | broader, proxy_for, typical_approach, and mappings in `ontology/mappings/` | Curated, then mined with human approval |
| L2 Literature assertions | L0 and L1 nodes | mentions, uses_method, measures, responds_to | Vocabulary matching and LLM extraction |
| L3 Coupling | CouplingMechanism | supports_mechanism, plus links to variables and compartments | Curated, with evidence from L2 |

The classes are shared. The instances stay in separate files for each domain, so seismology and hydrology keep their own terms. A concept like hydraulic head is a hydrology entry that maps to the shared variable pore pressure. It does not get rewritten as pore pressure.

## How the physics stay unified

We do not merge equations. Each `PhysicalModel` stays its own node, with its equation class recorded. Models connect only through these:

- **StateVariable.** Pore pressure, saturation, effective stress, mass load, strain, permeability, porosity, ice content. These live in `ontology/vocab/shared.yaml`.
- **Compartment.** Snowpack, vadose zone, saturated zone, river channel, fault zone, crust, frozen ground.
- **CouplingMechanism.** Forcing variables, response variables, direction, constitutive link (Biot, Gassmann, elastic loading Green's functions), compartments, and evidence.
- **ScaleRange on Method and Sensor.** Depth, frequency, footprint and time resolution, each with a cited source.

An opportunity is proposed only where scales overlap. Without that filter, a graph would happily suggest that a teleseismic method can resolve soil moisture in one field plot.

## Corpus

OpenAlex subfields cannot define the corpus, and topic labels are only one signal. See `docs/scoping-2026-11-03.md`. Scope is a curated list of topics, journals and keywords in `config/scope.yaml`.

| Set type | Purpose | Ingested? |
|---|---|---|
| Core (`seismology_core`, `hydrology_core`) | The two disciplines | Yes |
| Bridge (three sets combining both fields' terms) | Work already between the fields | Yes, and first in line for the LLM |
| Application (four sets: water management, disaster management, landslides, subsurface operations, each crossed with both fields' keywords) | Evidence for Decision and Hazard nodes | Yes, with the LLM on a 20% sample |
| Audit | Measures contamination | No |

Earthquake engineering is out of the core and allowed in bridge and application sets. Water treatment and water chemistry are out. Snow, soil moisture and permafrost enter through compartments and bridge queries, not the full cryosphere topics.

## Discovering nodes and edges

The hand-written seeds are hypotheses, because a graph constrained to them would mostly return what we put in (ADR 0006). Discovery comes before the schema is frozen, in M3.

**What "best represents" means.** Candidate graphs are scored on these. Targets are proposals, and none has been run on this corpus.

| Criterion | Test | Target |
|---|---|---|
| Coverage | Share of works with at least 2 concepts, by domain and era, abstracts and titles scored separately | Set after the first run |
| Saturation | New concepts per 100 additional abstracts | Near flat before freezing |
| Stability | Do nodes and communities recur under bootstrap resampling? | Adjusted Rand index above about 0.8 |
| Specificity | Does a concept separate works, unlike "data" or "model"? | Drop generic terms |
| Prediction | Graph at year T predicts new links by T+5 | Beats preferential attachment |
| Expert validity | Seismologist and hydrologist review of a sample | Precision thresholds from M4 |

**Nodes.** Candidates come from OpenAlex keywords, noun phrases, existing ontologies, and open LLM extraction on 4,000 abstracts (1,000 each from seismology, hydrology, high-scoring bridge works and application sets). Local embeddings group synonyms such as "dv/v" and "seismic velocity change", and a person approves the merges. Log-odds across the corpora assign each concept to seismology, hydrology or shared. Terms that mean different things in each field stay split, such as "discharge", "stage", "storage" and "attenuation". The pass also shows how many hand-written seeds appear bottom-up, which measures their bias.

**Seismohydrology.** The 9,533-work keyword intersection only finds papers already using both fields' words. Instead, each work gets a continuous score from how its references split between the fields (a participation coefficient or Rao-Stirling diversity), whether it mixes both vocabularies, and whether both fields cite it. Seismohydrology concepts are those enriched in high-scoring works relative to both parent fields.

**Edges.** Three kinds, kept separate because they mean different things:

| Kind | Method | Means | Cost |
|---|---|---|---|
| Association | Concept co-occurrence (NPMI), bibliographic coupling and co-citation, tested against a null with false-discovery control, then reduced with a disparity-filter backbone | These topics travel together | Local |
| Typed claim | LLM extraction using predicates derived from the open pass, about 8 to 12 | This work says X measures or responds to Y | See `ROADMAP.md` |
| Physical coupling | Curated, with a named constitutive link | This physics connects them | Reviewer time |

A typed claim is accepted only with at least two works from independent author groups, so one prolific group can't manufacture a consensus. Negative results are kept. The first two kinds describe what people wrote and the third describes the physics. An opportunity is often a mismatch between them.

**Gold set.** It comes after the schema is frozen, because its labels depend on the node types, and it is split as in `config/extraction.yaml`. It is mostly bridge papers, with single-domain strata because a missed mention in one field later looks like a research gap, and hard negatives to test false positives.

## Extraction tiers

Each tier handles only what the one before it cannot.

| Tier | Work | Scope | Cost |
|---|---|---|---|
| 0 | OpenAlex topics, keywords, citations, related works | All | About $1 |
| 1 | Vocabulary matching on titles and abstracts | All | Local |
| 2 | Local embeddings for entity linking and deduplication | Concepts and bridge works | Local |
| 3 | LLM batches with prompt caching, with output constrained to the schema frozen after discovery | Bridge works, 5% core sample, 20% application sample | See `ROADMAP.md` |
| 4 | Human review through pull requests | Vocabulary and L3 | Reviewer time |

About 40% of core works have no abstract (`docs/scoping-2026-11-03.md`), so citations and titles must carry those works.

## Finding opportunities (M6)

| Class | Definition |
|---|---|
| O1 Observational substitution | A hydrologic variable is needed and sparsely observed; a seismic method is sensitive to it at the right depth and timescale; few works link them |
| O2 Method transfer | A method is mature in one domain, on a problem class that also exists in the other, where it is rarely used. Includes approach imbalance: for the same task and variable, one field works mostly data-driven and the other mostly model-driven |
| O3 Coupling gap | A mechanism has literature on one side only, or in one direction only |
| O4 Community gap | High semantic similarity with low citation flow between author communities; Swanson-style A-B-C closure from literature-based discovery |

Low counts have three explanations: scarce science, missing abstracts and different words for the same thing. Only the first is an opportunity, so coverage normalization and vocabulary expansion come before any gap is reported.

## Testing against false positives

- **Time-sliced holdout.** Build the graph at cutoffs 2010, 2015 and 2020, predict unlinked concept pairs, and test them against the next five years.
- **Baseline.** Preferential attachment (degree product). A score that does not beat it gets dropped.
- **Canaries.** Ambient-noise velocity change with groundwater, and river seismics, must rank highly from a cutoff before those fields grew.
- **Leakage.** The holdout cuts the graph at a date, but an LLM trained later may extract with knowledge of the future. Compare vocabulary-only graphs against LLM graphs at the same cutoff.
- **Expert panel.** Domain experts from both sides rate the top 50 blind.

## Storage

Parquet tables are the store of record, queried with DuckDB. There is no database server. `nodes.parquet`, `edges.parquet` and `work_sets.parquet` are the published tables, and their columns are in `src/seismohydro_kg/graph/schema.py`.

| Table | Columns |
|---|---|
| nodes | node_id, node_type, layer, label, domain, attrs (JSON) |
| edges | source, target, edge_type, layer, work_id, char_start, char_end, extractor_version, confidence, tier |
| work_sets | work_id, set_name |

Decisions behind this are in `docs/adr/`.
