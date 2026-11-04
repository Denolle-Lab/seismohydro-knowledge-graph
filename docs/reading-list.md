# Reading list: knowledge graphs

A short path for students joining the project, from undergraduate to graduate level. No background in knowledge graphs is assumed. Read in this order, and stop when you have what you need.

Each paper's title, year, venue and DOI were checked against OpenAlex on 2026-11-03. Levels and reading advice are our judgment, so please say if one misleads you. Papers marked "library" may need institutional access.

## Start here

| # | Paper | Level | Why read it | Access |
|---|---|---|---|---|
| 1 | Noy et al. (2019), [Industry-scale knowledge graphs: lessons and challenges](https://doi.org/10.1145/3331166), *Communications of the ACM* | Undergraduate | Short and practical, with no math. Five companies describe what building a real graph involves | [Free](https://doi.org/10.1145/3331166) |
| 2 | Swanson (1986), [Fish oil, Raynaud's syndrome, and undiscovered public knowledge](https://doi.org/10.1353/pbm.1986.0087), *Perspectives in Biology and Medicine* | Undergraduate | The founding idea of this project: two literatures that never cite each other can together imply something neither states | Library |
| 3 | Hogan et al. (2021), [Knowledge graphs](https://doi.org/10.1145/3447772), *ACM Computing Surveys* | Upper undergraduate | The standard introduction. It is long, so read the opening sections and return to the rest as a reference | [Free PDF](https://dl.acm.org/doi/pdf/10.1145/3447772) |

## How this applies to science

| # | Paper | Level | Why read it | Access |
|---|---|---|---|---|
| 4 | Krenn & Zeilinger (2020), [Predicting research trends with semantic and neural networks with an application in quantum physics](https://doi.org/10.1073/pnas.1914370116), *PNAS* | Graduate | The closest model for our approach: a concept network built from papers, used to predict what gets studied next | [Free](https://www.ncbi.nlm.nih.gov/pmc/articles/6994972) |
| 5 | Krenn et al. (2023), [Forecasting the future of artificial intelligence with machine learning-based link prediction in an exponentially growing knowledge network](https://doi.org/10.1038/s42256-023-00735-0), *Nature Machine Intelligence* | Graduate | Link prediction tested on literature that appeared later, as our holdout in M6 will do | [Free PDF](https://www.nature.com/articles/s42256-023-00735-0.pdf) |
| 6 | Nickel et al. (2015), [A review of relational machine learning for knowledge graphs](https://doi.org/10.1109/JPROC.2015.2483592), *Proceedings of the IEEE* | Graduate | The statistical models behind predicting missing links. Expect linear algebra and probability | [Free PDF](https://arxiv.org/pdf/1503.00759) |

## Optional, for specific parts of the project

| Paper | Read it if you work on | Access |
|---|---|---|
| Pan et al. (2024), [Unifying large language models and knowledge graphs: a roadmap](https://doi.org/10.1109/TKDE.2024.3352100), *IEEE Transactions on Knowledge and Data Engineering* | LLM extraction (M3, M4) | [Free PDF](https://arxiv.org/pdf/2306.08302) |
| Priem et al. (2022), [OpenAlex: a fully-open index of scholarly works, authors, venues, institutions, and concepts](https://doi.org/10.48550/arXiv.2205.01833), arXiv | Our data source (M1). OpenAlex has changed since 2022, so check [its documentation](https://help.openalex.org/) for current details | [Free PDF](https://arxiv.org/pdf/2205.01833) |
| Raskin & Pan (2005), [Knowledge representation in the semantic web for Earth and environmental terminology (SWEET)](https://doi.org/10.1016/j.cageo.2004.12.004), *Computers & Geosciences* | Earth science ontologies (M3) | Library |

## After reading

Move on to [design.md](design.md) and [node-types.md](node-types.md), which apply these ideas to seismology and hydrology.
