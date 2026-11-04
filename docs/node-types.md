# Node types

These definitions are for annotators, reviewers and extraction prompts. Each type has a boundary test, because the hard part of labeling a paper is deciding between neighboring types. The classes are in `ontology/schema/seismohydro.linkml.yaml`, and seed instances are in `ontology/vocab/`.

All of this is a proposal for review in M3. Types that annotators can't apply consistently, or that abstracts rarely mention, should be dropped or curated by hand.

## Observing the system

| Type | Definition | Boundary test | Examples |
|---|---|---|---|
| **Sensor** | A physical instrument or platform that records a signal | Can you deploy, install or launch it? | Broadband seismometer, DAS, piezometer, stream gauge, GNSS, GRACE |
| **Observable** | A quantity measured or derived from a record | Is it reported from a record, even if it stands in for something else? Link it to what it stands for with `proxy_for` | dv/v, seismic noise power, streamflow, well water level |
| **Dataset** | A named collection of records, or the network or archive that provides them | Could you download it or request it by name? | FDSN archives, USGS NWIS |

## Describing the system

| Type | Definition | Boundary test | Examples |
|---|---|---|---|
| **StateVariable** | A physical quantity describing the system, measurable directly or not. Includes slowly varying material properties | Would it have a value even with no instrument present? | Pore pressure, saturation, soil moisture, hydraulic head, permeability, strain |
| **Compartment** | A part of the Earth system where water resides or moves and elastic waves can act | Can you point to where it is in a cross section? | Surface water (river channel, lake or reservoir, wetland), groundwater (saturated zone, vadose zone), snowpack, frozen ground, fault zone |
| **Process** | A physical mechanism or change through time, described without regard to harm | Does it name something happening, with no reference to damage? | Recharge, infiltration, pore pressure diffusion, bedload transport, earthquake rupture |
| **Hazard** | A process considered for its potential harm to people, property or ecosystems | Is the study concerned with harm or risk? If not, use Process | Flood, drought, landslide, liquefaction, ground shaking |

Soil moisture is a StateVariable located in the vadose zone, not a compartment. The word "groundwater" can mean the system or the water in it: tag the compartment `shared:groundwater`, and use a state variable such as `hydro:groundwater_storage` or `hydro:hydraulic_head` when a quantity is meant.

## Doing the science

| Type | Definition | Boundary test | Examples |
|---|---|---|---|
| **Task** | The inferential goal of a study | What is the study trying to find out, regardless of how? | Detection, monitoring, forecasting, parameter estimation, imaging, attribution, downscaling |
| **Method** | A procedure applied to data or to a model to produce a result | Could you write its steps as an algorithm? | Ambient-noise cross-correlation, baseflow separation, data assimilation, LSTM rainfall-runoff |
| **PhysicalModel** | A mathematical statement of physics, independent of code or data | Can you write it as equations? | Elastic wave equation, Richards equation, Darcy's law, Gassmann fluid substitution |
| **Software** | A named code that implements a method or model | Does it have a repository or a release? | MODFLOW, ParFlow, SPECFEM, ObsPy |
| **ResearchApproach** | Whether data, governing equations or both produce the main result | See below | Data-driven, model-driven, hybrid |

A neural network is a Method, not a PhysicalModel, however well it fits.

## Data-driven and model-driven research

ResearchApproach is judged on the **main result of a study**, not on its tools or the words its authors use. "Data-driven" often just means machine learning in abstracts, and it means different things across the two fields. Ask two questions:

1. Are governing equations solved or imposed in producing the main result?
2. Do records constrain the estimate that is the main result, beyond setting up or checking a model?

| Equations? | Records constrain the result? | Value | Examples |
|---|---|---|---|
| No | Yes | **Data-driven** | Regressing dv/v on rainfall, LSTM streamflow prediction, deep-learning phase picking, baseflow separation |
| Yes | No | **Model-driven** | Forward wave simulation, a poroelastic analytical solution, MODFLOW scenario runs with fixed parameters |
| Yes | Yes | **Hybrid** | Full waveform inversion, ensemble Kalman filtering, physics-informed networks, fitting a poroelastic model to dv/v |

Cases annotators should expect to argue about:

- **A calibrated process model used for scenarios** is model-driven: the equations produce the result, and calibration only sets it up. If the calibrated parameters are themselves the result, the study is hybrid.
- **A measurement study that interprets its result with physics afterward** is data-driven, unless a physical model is actually fitted.
- **Surrogates trained only on simulations** are model-driven, since no records constrain them. If they are also trained on observations, they are hybrid.
- **Reviews and method papers** with no single main result get no approach value.

Each work gets one primary value through a `uses_approach` edge. A Method can carry a `typical_approach`, but the value on the work takes precedence. For example, data assimilation is typically hybrid.

This axis is separate from the kind of evidence. A data-driven study can run on simulated data, and a model-driven study can be checked against field data. Evidence type (observation, lab, simulation, theory) will be an attribute on claims, and isn't implemented yet.

**Why it matters for opportunities.** It extends the O2 method transfer class. For the same task and variable, one field may work mostly data-driven while the other remains mostly model-driven, and that imbalance suggests what could transfer. It also shows hybrid methods where one field already has both ingredients and hasn't combined them.

## Context and value

| Type | Definition | Boundary test | Examples |
|---|---|---|---|
| **Gap** | A kind of limitation or unmet need stated in the literature | Does the paper say something can't yet be done or remains unknown? | Sparse observations, poor depth resolution, non-uniqueness, scale mismatch, no field validation |
| **Setting** | A kind of environment where a study could be repeated | Could it exist in many places? | Karst terrain, arid basin, agricultural basin, mountain catchment |
| **Region** | A named geographic place | Could you find it on a map by name? | California Central Valley |
| **Event** | A specific occurrence with a date and a place | Does it have a date? | 2011 Tohoku-oki earthquake |
| **DecisionDomain** | A sector of human decisions that research can serve | Is it a broad area of practice? | Water resource management, disaster management, subsurface energy and storage operations |
| **Decision** | A specific choice someone must make, with stateable information needs | Could you name who decides and how soon they need to know? | Groundwater allocation, flood warning, dam safety assessment, fluid injection regulation |

"Application" is deliberately not a type, because it is too vague to annotate consistently. Split it into the Task (monitoring) and the Decision it serves (groundwater allocation).

Gap instances here are categories. A useful gap also needs a subject and a place, such as sparse observations of soil moisture in an arid basin. That requires a reified record joining several nodes, which M3 still has to design.

Decision requirements such as latency and accuracy stay empty until they have a cited source. Abstracts will probably rarely state them, so Decision may end up as a short curated list and not an extracted type.

## Relationships between types

| Edge | From | To | Status |
|---|---|---|---|
| `broader` | Any concept | Parent concept | Built, curated |
| `proxy_for` | Observable | StateVariable | Built, curated seeds |
| `typical_approach` | Method | ResearchApproach | Built, curated seeds |
| `uses_approach`, `uses_method_on`, `addresses_task`, `measures`, `reports_gap`, `studied_in`, `informs_decision` | Work or concept | Concept | Proposed, from extraction in M4 |
