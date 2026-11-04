"""Column layout of the node and edge tables, the only tables a release publishes."""

from __future__ import annotations

import pyarrow as pa

NODE_SCHEMA = pa.schema(
    [
        ("node_id", pa.string()),
        ("node_type", pa.string()),
        ("layer", pa.string()),
        ("label", pa.string()),
        ("domain", pa.string()),
        ("attrs", pa.string()),
    ]
)

EDGE_SCHEMA = pa.schema(
    [
        ("source", pa.string()),
        ("target", pa.string()),
        ("edge_type", pa.string()),
        ("layer", pa.string()),
        ("work_id", pa.string()),
        ("char_start", pa.int64()),
        ("char_end", pa.int64()),
        ("extractor_version", pa.string()),
        ("confidence", pa.float64()),
        ("tier", pa.string()),
    ]
)

MEMBERSHIP_SCHEMA = pa.schema([("work_id", pa.string()), ("set_name", pa.string())])

LAYERS = ("L0", "L1", "L2", "L3")
TIERS = ("openalex", "gazetteer", "llm", "human")
