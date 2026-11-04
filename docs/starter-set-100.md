# Starter set: 100 papers

A manageable entry point to about 1M works: 100 papers covering seismology, hydrology, the work between them, and the decisions and hazards they serve. Use it to learn the fields, to pilot the discovery pass in M3, and to give reviewers something concrete to react to. The same list with OpenAlex IDs is in [starter-set-100.csv](starter-set-100.csv).

This is a curated sample for coverage, not a statistical sample of the literature, so it should not be used to estimate how common anything is.

## How it was chosen

1. `scripts/starter_candidates.py` pulled 480 candidates on 2026-11-03: the top-cited works, all-time and since 2016, for each coupling mechanism and core topic, and the top-cited works for each application set.
2. Papers were chosen by screening titles for relevance and coverage. Nobody has read the abstracts or papers for this selection, and it awaits review by a seismologist and a hydrologist.
3. Citation-ranked keyword queries missed well-known work, so 13 papers were added from memory as known landmarks, and each was confirmed by DOI in OpenAlex. The CSV marks them in `selected_from`. A 14th, Bettinelli et al. (2008) on Himalayan seasonal seismicity, was dropped because the DOI tried resolved to a different paper, and it may be worth adding once its DOI is confirmed.

## Known limits

- **Citation rank** favors older papers, reviews and methods, so recent and niche work is underrepresented. Citation counts are from 2026-11-03.
- **Query quality varied.** The river seismics query mostly returned igneous provinces and basin geology, so that group relies on known landmarks.
- **Data assimilation.** Its query surfaced no seismic velocity assimilation work among the top-cited results, so the two papers here are from hydrology. That may be a real gap, but it hasn't been tested.
- **Disaster management.** Its top-cited results are mostly social science, so only one paper comes from that query. The other hazard papers come from the landslide and flood results, and one early warning review was added as a known landmark.
- **Selection by one reader.** Screening was done by an AI assistant, and a domain expert would likely change some choices. The list includes a paper by the project's PI that surfaced through the citation query.

## Seismology (20)

| Year | Title | Venue | DOI |
|---|---|---|---|
| 1944 | Frequency of earthquakes in California* | Bulletin of the Seismological Society of America | [10.1785/bssa0340040185](https://doi.org/10.1785/bssa0340040185) |
| 1970 | Tectonic stress and the spectra of seismic shear waves from earthquakes | Journal of Geophysical Research Atmospheres | [10.1029/jb075i026p04997](https://doi.org/10.1029/jb075i026p04997) |
| 1978 | Friction of rocks | Pure and Applied Geophysics | [10.1007/bf00876528](https://doi.org/10.1007/bf00876528) |
| 1978 | Automatic earthquake recognition and timing from single traces | Bulletin of the Seismological Society of America | [10.1785/bssa0680051521](https://doi.org/10.1785/bssa0680051521) |
| 1979 | A moment magnitude scale | Journal of Geophysical Research Atmospheres | [10.1029/jb084ib05p02348](https://doi.org/10.1029/jb084ib05p02348) |
| 1981 | Preliminary reference Earth model | Physics of The Earth and Planetary Interiors | [10.1016/0031-9201(81)90046-7](https://doi.org/10.1016/0031-9201(81)90046-7) |
| 1991 | Traveltimes for global earthquake location and phase identification | Geophysical Journal International | [10.1111/j.1365-246x.1991.tb06724.x](https://doi.org/10.1111/j.1365-246x.1991.tb06724.x) |
| 1999 | Multichannel analysis of surface waves | Geophysics | [10.1190/1.1444590](https://doi.org/10.1190/1.1444590) |
| 2003 | Long-Range Correlations in the Diffuse Seismic Coda | Science | [10.1126/science.1078551](https://doi.org/10.1126/science.1078551) |
| 2005 | High-Resolution Surface-Wave Tomography from Ambient Seismic Noise | Science | [10.1126/science.1108339](https://doi.org/10.1126/science.1108339) |
| 2007 | Processing seismic ambient noise data to obtain reliable broad-band surface wave dispersion measurements | Geophysical Journal International | [10.1111/j.1365-246x.2007.03374.x](https://doi.org/10.1111/j.1365-246x.2007.03374.x) |
| 2009 | An overview of full-waveform inversion in exploration geophysics | Geophysics | [10.1190/1.3238367](https://doi.org/10.1190/1.3238367) |
| 2016 | Connecting slow earthquakes to huge earthquakes | Science | [10.1126/science.aaf1512](https://doi.org/10.1126/science.aaf1512) |
| 2017 | Fiber‐Optic Network Observations of Earthquake Wavefields | Geophysical Research Letters | [10.1002/2017gl075722](https://doi.org/10.1002/2017gl075722) |
| 2018 | PhaseNet: A Deep-Neural-Network-Based Seismic Arrival Time Picking Method | Geophysical Journal International | [10.1093/gji/ggy423](https://doi.org/10.1093/gji/ggy423) |
| 2018 | Convolutional neural network for earthquake detection and location | Science Advances | [10.1126/sciadv.1700578](https://doi.org/10.1126/sciadv.1700578) |
| 2019 | Illuminating seafloor faults and ocean dynamics with dark fiber distributed acoustic sensing | Science | [10.1126/science.aay5881](https://doi.org/10.1126/science.aay5881) |
| 2020 | Earthquake transformer—an attentive deep-learning model for simultaneous earthquake detection and phase picking | Nature Communications | [10.1038/s41467-020-17591-w](https://doi.org/10.1038/s41467-020-17591-w) |
| 2022 | Deep-learning seismology | Science | [10.1126/science.abm4470](https://doi.org/10.1126/science.abm4470) |
| 2022 | Physics‐Informed Neural Networks (PINNs) for Wave Propagation and Full Waveform Inversions | Journal of Geophysical Research Solid Earth | [10.1029/2021jb023120](https://doi.org/10.1029/2021jb023120) |

## Hydrology (20)

| Year | Title | Venue | DOI |
|---|---|---|---|
| 1931 | CAPILLARY CONDUCTION OF LIQUIDS THROUGH POROUS MEDIUMS | Physics | [10.1063/1.1745010](https://doi.org/10.1063/1.1745010) |
| 1935 | The relation between the lowering of the Piezometric surface and the rate and duration of discharge of a well using ground‐water storage | Transactions American Geophysical Union | [10.1029/tr016i002p00519](https://doi.org/10.1029/tr016i002p00519) |
| 1955 | On kinematic waves I. Flood movement in long rivers | Proceedings of the Royal Society of London A Mathematical and Physical Sciences | [10.1098/rspa.1955.0088](https://doi.org/10.1098/rspa.1955.0088) |
| 1961 | Isotopic Variations in Meteoric Waters | Science | [10.1126/science.133.3465.1702](https://doi.org/10.1126/science.133.3465.1702) |
| 1970 | River flow forecasting through conceptual models part I — A discussion of principles | Journal of Hydrology | [10.1016/0022-1694(70)90255-6](https://doi.org/10.1016/0022-1694(70)90255-6) |
| 1975 | Dynamics of Fluids in Porous Media | Soil Science | [10.1097/00010694-197508000-00022](https://doi.org/10.1097/00010694-197508000-00022) |
| 1979 | A physically based, variable contributing area model of basin hydrology / Un modèle à base physique de zone d'appel variable de l'hydrologie du bassin versant | Hydrological Sciences Bulletin | [10.1080/02626667909491834](https://doi.org/10.1080/02626667909491834) |
| 1980 | A Closed‐form Equation for Predicting the Hydraulic Conductivity of Unsaturated Soils | Soil Science Society of America Journal | [10.2136/sssaj1980.03615995004400050002x](https://doi.org/10.2136/sssaj1980.03615995004400050002x) |
| 2002 | Interactions between groundwater and surface water: the state of the science | Hydrogeology Journal | [10.1007/s10040-001-0170-8](https://doi.org/10.1007/s10040-001-0170-8) |
| 2004 | The Global Land Data Assimilation System | Bulletin of the American Meteorological Society | [10.1175/bams-85-3-381](https://doi.org/10.1175/bams-85-3-381) |
| 2009 | Decomposition of the mean squared error and NSE performance criteria: Implications for improving hydrological modelling | Journal of Hydrology | [10.1016/j.jhydrol.2009.08.003](https://doi.org/10.1016/j.jhydrol.2009.08.003) |
| 2009 | A Multiscalar Drought Index Sensitive to Global Warming: The Standardized Precipitation Evapotranspiration Index | Journal of Climate | [10.1175/2009jcli2909.1](https://doi.org/10.1175/2009jcli2909.1) |
| 2010 | The Soil Moisture Active Passive (SMAP) Mission | Proceedings of the IEEE | [10.1109/jproc.2010.2043918](https://doi.org/10.1109/jproc.2010.2043918) |
| 2014 | Karst water resources in a changing world: Review of hydrological modeling approaches | Reviews of Geophysics | [10.1002/2013rg000443](https://doi.org/10.1002/2013rg000443) |
| 2016 | Scripting MODFLOW Model Development Using Python and FloPy | Ground Water | [10.1111/gwat.12413](https://doi.org/10.1111/gwat.12413) |
| 2017 | The CAMELS data set: catchment attributes and meteorology for large-sample studies | Hydrology and earth system sciences | [10.5194/hess-21-5293-2017](https://doi.org/10.5194/hess-21-5293-2017) |
| 2018 | Rainfall–runoff modelling using Long Short-Term Memory (LSTM) networks | Hydrology and earth system sciences | [10.5194/hess-22-6005-2018](https://doi.org/10.5194/hess-22-6005-2018) |
| 2019 | Twenty-three unsolved problems in hydrology (UPH) – a community perspective | Hydrological Sciences Journal | [10.1080/02626667.2019.1620507](https://doi.org/10.1080/02626667.2019.1620507) |
| 2019 | Towards learning universal, regional, and local hydrological behaviors via machine learning applied to large-sample datasets | Hydrology and earth system sciences | [10.5194/hess-23-5089-2019](https://doi.org/10.5194/hess-23-5089-2019) |
| 2019 | Deep learning and process understanding for data-driven Earth system science | Nature | [10.1038/s41586-019-0912-1](https://doi.org/10.1038/s41586-019-0912-1) |

## Seismohydrology (50)

### Ambient-noise velocity change and water

| Year | Title | Venue | DOI |
|---|---|---|---|
| 2006 | Passive image interferometry and seasonal variations of seismic velocities at Merapi Volcano, Indonesia | Geophysical Research Letters | [10.1029/2006gl027797](https://doi.org/10.1029/2006gl027797) |
| 2017 | Monitoring ground water storage at mesoscale using seismic noise: 30 years of continuous observation and thermo-elastic and hydrological modeling | Scientific Reports | [10.1038/s41598-017-14468-9](https://doi.org/10.1038/s41598-017-14468-9) |
| 2017 | Groundwater Monitoring with Passive Seismic Interferometry | Journal of Water Resource and Protection | [10.4236/jwarp.2017.912091](https://doi.org/10.4236/jwarp.2017.912091) |
| 2017 | Seasonal Crustal Seismic Velocity Changes Throughout Japan | Journal of Geophysical Research Solid Earth | [10.1002/2017jb014307](https://doi.org/10.1002/2017jb014307) |
| 2018 | Tracking Groundwater Levels Using the Ambient Seismic Field | Geophysical Research Letters | [10.1029/2018gl077706](https://doi.org/10.1029/2018gl077706) |
| 2022 | Space-time monitoring of groundwater fluctuations with passive seismic interferometry | Nature Communications | [10.1038/s41467-022-32194-3](https://doi.org/10.1038/s41467-022-32194-3) |

### Distributed acoustic sensing of water systems

| Year | Title | Venue | DOI |
|---|---|---|---|
| 2017 | Distributed Acoustic Sensing for Seismic Monitoring of The Near Surface: A Traffic-Noise Interferometry Case Study | Scientific Reports | [10.1038/s41598-017-11986-4](https://doi.org/10.1038/s41598-017-11986-4) |
| 2020 | Distributed Acoustic Sensing as a Distributed Hydraulic Sensor in Fractured Bedrock | Water Resources Research | [10.1029/2020wr028140](https://doi.org/10.1029/2020wr028140) |
| 2021 | Aquifer Monitoring Using Ambient Seismic Noise Recorded With Distributed Acoustic Sensing (DAS) Deployed on Dark Fiber | Journal of Geophysical Research Solid Earth | [10.1029/2020jb021004](https://doi.org/10.1029/2020jb021004) |

### Data assimilation (hydrology side)

| Year | Title | Venue | DOI |
|---|---|---|---|
| 2009 | Ensemble Kalman filter data assimilation for a process‐based catchment scale model of surface and subsurface flow | Water Resources Research | [10.1029/2008wr007031](https://doi.org/10.1029/2008wr007031) |
| 2015 | Data Assimilation of Satellite Soil Moisture into Rainfall-Runoff Modelling: A Complex Recipe? | Remote Sensing | [10.3390/rs70911403](https://doi.org/10.3390/rs70911403) |

### Hydrological loading

| Year | Title | Venue | DOI |
|---|---|---|---|
| 1972 | Deformation of the Earth by surface loads | Reviews of Geophysics | [10.1029/rg010i003p00761](https://doi.org/10.1029/rg010i003p00761) |
| 2011 | A model for seasonal changes in GPS positions and seismic wave speeds due to thermoelastic and hydrologic variations | Journal of Geophysical Research Atmospheres | [10.1029/2010jb008156](https://doi.org/10.1029/2010jb008156) |
| 2013 | Numerical simulations of global‐scale high‐resolution hydrological crustal deformations | Journal of Geophysical Research Solid Earth | [10.1002/jgrb.50353](https://doi.org/10.1002/jgrb.50353) |
| 2017 | Seasonal water storage, stress modulation, and California seismicity | Science | [10.1126/science.aak9547](https://doi.org/10.1126/science.aak9547) |
| 2022 | A Review of GNSS/GPS in Hydrogeodesy: Hydrologic Loading Applications and Their Implications for Water Resource Research | Water Resources Research | [10.1029/2022wr032078](https://doi.org/10.1029/2022wr032078) |

### Earthquake hydrologic response

| Year | Title | Venue | DOI |
|---|---|---|---|
| 1993 | Hydrological signatures of earthquake strain | Journal of Geophysical Research Atmospheres | [10.1029/93jb02219](https://doi.org/10.1029/93jb02219) |
| 2003 | Streamflow and Water Well Responses to Earthquakes | Science | [10.1126/science.1082980](https://doi.org/10.1126/science.1082980) |
| 2003 | A mechanism for sustained groundwater pressure changes induced by distant earthquakes | Journal of Geophysical Research Atmospheres | [10.1029/2002jb002321](https://doi.org/10.1029/2002jb002321) |
| 2006 | Seismic waves increase permeability | Nature | [10.1038/nature04798](https://doi.org/10.1038/nature04798) |
| 2010 | Hydrologic responses to earthquakes and a general metric | Geofluids | [10.1111/j.1468-8123.2009.00270.x](https://doi.org/10.1111/j.1468-8123.2009.00270.x) |
| 2012 | Changes in permeability caused by transient stresses: Field observations, experiments, and mechanisms | Reviews of Geophysics | [10.1029/2011rg000382](https://doi.org/10.1029/2011rg000382) |
| 2016 | Regional changes in streamflow after a megathrust earthquake | Earth and Planetary Science Letters | [10.1016/j.epsl.2016.11.013](https://doi.org/10.1016/j.epsl.2016.11.013) |

### Soil moisture, freeze-thaw and permafrost

| Year | Title | Venue | DOI |
|---|---|---|---|
| 2019 | Quantitative imaging of water, ice and air in permafrost systems through petrophysical joint inversion of seismic refraction and electrical resistivity data | Geophysical Journal International | [10.1093/gji/ggz402](https://doi.org/10.1093/gji/ggz402) |
| 2020 | Petrophysical Joint Inversion Applied to Alpine Permafrost Field Sites to Image Subsurface Ice, Water, Air, and Rock Contents | Frontiers in Earth Science | [10.3389/feart.2020.00085](https://doi.org/10.3389/feart.2020.00085) |
| 2023 | Long-term ambient seismic interferometry for constraining seasonal subsurface velocity variations in urban settings: a distributed acoustic sensing (DAS) case study | Geophysical Journal International | [10.1093/gji/ggad181](https://doi.org/10.1093/gji/ggad181) |

### Poroelasticity and seismicity

| Year | Title | Venue | DOI |
|---|---|---|---|
| 1956 | Theory of Propagation of Elastic Waves in a Fluid-Saturated Porous Solid. I. Low-Frequency Range | The Journal of the Acoustical Society of America | [10.1121/1.1908239](https://doi.org/10.1121/1.1908239) |
| 1976 | Some basic stress diffusion solutions for fluid‐saturated elastic porous media with compressible constituents | Reviews of Geophysics | [10.1029/rg014i002p00227](https://doi.org/10.1029/rg014i002p00227) |
| 1989 | Earthquakes triggered by fluid extraction | Geology | [10.1130/0091-7613(1989)017<0942:etbfe>2.3.co;2](https://doi.org/10.1130/0091-7613(1989)017<0942:etbfe>2.3.co;2) |
| 1998 | Poroelastic rebound along the Landers 1992 earthquake surface rupture | Journal of Geophysical Research Atmospheres | [10.1029/98jb02302](https://doi.org/10.1029/98jb02302) |
| 2002 | Pore pressure and poroelasticity effects in Coulomb stress analysis of earthquake interactions | Journal of Geophysical Research Atmospheres | [10.1029/2000jb000138](https://doi.org/10.1029/2000jb000138) |
| 2010 | Seismic wave attenuation and dispersion resulting from wave-induced flow in porous rocks — A review | Geophysics | [10.1190/1.3463417](https://doi.org/10.1190/1.3463417) |
| 2015 | Injection‐induced seismicity: Poroelastic and earthquake nucleation effects | Journal of Geophysical Research Solid Earth | [10.1002/2015jb012060](https://doi.org/10.1002/2015jb012060) |

### Hydrogeophysics and the critical zone

| Year | Title | Venue | DOI |
|---|---|---|---|
| 2010 | Improved extraction of hydrologic information from geophysical data through coupled hydrogeophysical inversion | Water Resources Research | [10.1029/2008wr007060](https://doi.org/10.1029/2008wr007060) |
| 2013 | Geophysical constraints on deep weathering and water storage potential in the Southern Sierra Critical Zone Observatory | Earth Surface Processes and Landforms | [10.1002/esp.3502](https://doi.org/10.1002/esp.3502) |
| 2015 | The emergence of hydrogeophysics for improved understanding of subsurface processes over multiple scales | Water Resources Research | [10.1002/2015wr017016](https://doi.org/10.1002/2015wr017016) |
| 2018 | Critical Zone Structure Under a Granite Ridge Inferred From Drilling and Three‐Dimensional Seismic Refraction Data | Journal of Geophysical Research Earth Surface | [10.1029/2017jf004280](https://doi.org/10.1029/2017jf004280) |

### Induced seismicity

| Year | Title | Venue | DOI |
|---|---|---|---|
| 1997 | Estimating the crust permeability from fluid-injection-induced seismic emission at the KTB site | Geophysical Journal International | [10.1111/j.1365-246x.1997.tb01215.x](https://doi.org/10.1111/j.1365-246x.1997.tb01215.x) |
| 2013 | Injection-Induced Earthquakes | Science | [10.1126/science.1225942](https://doi.org/10.1126/science.1225942) |
| 2014 | Sharp increase in central Oklahoma seismicity since 2008 induced by massive wastewater injection | Science | [10.1126/science.1255802](https://doi.org/10.1126/science.1255802) |
| 2016 | How will induced seismicity in Oklahoma respond to decreased saltwater injection rates? | Science Advances | [10.1126/sciadv.1601542](https://doi.org/10.1126/sciadv.1601542) |
| 2016 | Fault activation by hydraulic fracturing in western Canada | Science | [10.1126/science.aag2583](https://doi.org/10.1126/science.aag2583) |

### Water and natural seismicity

| Year | Title | Venue | DOI |
|---|---|---|---|
| 2017 | Hydrologically-driven crustal stresses and seismicity in the New Madrid Seismic Zone | Nature Communications | [10.1038/s41467-017-01696-w](https://doi.org/10.1038/s41467-017-01696-w) |
| 2018 | Seasonal modulation of deep slow-slip and earthquakes on the Main Himalayan Thrust | Nature Communications | [10.1038/s41467-018-06371-2](https://doi.org/10.1038/s41467-018-06371-2) |
| 2020 | Rain and small earthquakes maintain a slow-moving landslide in a persistent critical state | Nature Communications | [10.1038/s41467-020-14445-3](https://doi.org/10.1038/s41467-020-14445-3) |

### River seismics

| Year | Title | Venue | DOI |
|---|---|---|---|
| 2008 | Spectral analysis of seismic noise induced by rivers: A new tool to monitor spatiotemporal changes in stream hydrodynamics | Journal of Geophysical Research Atmospheres | [10.1029/2007jb005034](https://doi.org/10.1029/2007jb005034) |
| 2011 | A physical model for seismic noise generation from sediment transport in rivers | Geophysical Research Letters | [10.1029/2011gl050255](https://doi.org/10.1029/2011gl050255) |
| 2014 | A physical model for seismic noise generation by turbulent flow in rivers | Journal of Geophysical Research Earth Surface | [10.1002/2014jf003201](https://doi.org/10.1002/2014jf003201) |
| 2016 | Bed load sediment transport inferred from seismic signals near a river | Journal of Geophysical Research Earth Surface | [10.1002/2015jf003782](https://doi.org/10.1002/2015jf003782) |
| 2018 | Glacial lake outburst floods as drivers of fluvial erosion in the Himalaya | Science | [10.1126/science.aat4981](https://doi.org/10.1126/science.aat4981) |

## Decisions and hazards (10)

| Year | Title | Venue | DOI |
|---|---|---|---|
| 1984 | Landslides caused by earthquakes | Geological Society of America Bulletin | [10.1130/0016-7606(1984)95<406:lcbe>2.0.co;2](https://doi.org/10.1130/0016-7606(1984)95<406:lcbe>2.0.co;2) |
| 2000 | Landslide triggering by rain infiltration | Water Resources Research | [10.1029/2000wr900090](https://doi.org/10.1029/2000wr900090) |
| 2007 | CO2 storage in geological media: Role, means, status and barriers to deployment | Progress in Energy and Combustion Science | [10.1016/j.pecs.2007.10.001](https://doi.org/10.1016/j.pecs.2007.10.001) |
| 2012 | Groundwater depletion and sustainability of irrigation in the US High Plains and Central Valley | Proceedings of the National Academy of Sciences | [10.1073/pnas.1200311109](https://doi.org/10.1073/pnas.1200311109) |
| 2013 | Global flood risk under climate change | Nature Climate Change | [10.1038/nclimate1911](https://doi.org/10.1038/nclimate1911) |
| 2014 | The global groundwater crisis | Nature Climate Change | [10.1038/nclimate2425](https://doi.org/10.1038/nclimate2425) |
| 2014 | Reviewing and visualizing the interactions of natural hazards | Reviews of Geophysics | [10.1002/2013rg000445](https://doi.org/10.1002/2013rg000445) |
| 2019 | Earthquake Early Warning: Advances, Scientific Challenges, and Societal Needs | Annual Review of Earth and Planetary Sciences | [10.1146/annurev-earth-053018-060457](https://doi.org/10.1146/annurev-earth-053018-060457) |
| 2019 | Earthquake‐Induced Chains of Geologic Hazards: Patterns, Mechanisms, and Impacts | Reviews of Geophysics | [10.1029/2018rg000626](https://doi.org/10.1029/2018rg000626) |
| 2024 | Rapid groundwater decline and some cases of recovery in aquifers globally | Nature | [10.1038/s41586-023-06879-8](https://doi.org/10.1038/s41586-023-06879-8) |
