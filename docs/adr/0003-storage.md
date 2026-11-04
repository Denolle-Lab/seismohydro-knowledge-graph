# ADR 0003: Parquet and DuckDB, with no graph database

**Status:** accepted, 2026-11-03.

**Context.** The first corpus is about 1M works, and cites edges could reach tens of millions. The budget is close to zero, the graph is built in batches and read for analysis, and it has to be easy to share. Kuzu, the obvious embedded graph database, was [archived in October 2025](https://www.theregister.com/2025/10/14/kuzudb_abandoned/).

**Decision.** Parquet node and edge tables are the store of record. DuckDB does the querying, and igraph will do graph algorithms from M2. Export to Neo4j CSV and GraphML for anyone who wants those tools, and to Turtle for the ontology layers from M3.

**Consequences.** No server to run or pay for, and a release is a few files. Interactive multi-hop queries are clumsier than in a graph database, and the export path covers people who want one. Revisit if M6 analysis spends its time on traversal that SQL handles badly.
