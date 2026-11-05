# Download runbook: OpenAlex on a shared machine

For whoever runs the download with their own OpenAlex key and credit. Commands run from the repository root. The metered commands have not yet run with a real key, so watch the first run and compare its spend with the OpenAlex dashboard.

## What it costs

| Step | Command | Cost | Notes |
|---|---|---|---|
| Check the key | `shkg scope-report` | About $0.01 | |
| Metadata and abstracts, about 1M works | `shkg ingest` | Up to $1.86 | Two days on the free budget |
| Full-text pilot, 500 works in TEI XML | `shkg fulltext ... --limit 500` | About $5 | Five days on the free budget |
| Full text, 10,000 works in TEI XML | `shkg fulltext ... --limit 10000` | About $100 | Only after the pilot shows a gain |

Rates are from the [OpenAlex price list](https://help.openalex.org/access/example-costs/). The free budget is $1 per day and resets at midnight UTC. [Prepaid credit](https://help.openalex.org/access/pricing/) is bought by card in $1 increments, is used only after the free budget runs out, and expires 3 months after your most recent purchase, so buy what the next step needs.

## Set up the machine

```bash
umask 077                       # Files you create are private to you
git clone https://github.com/Denolle-Lab/seismohydro-knowledge-graph.git
cd seismohydro-knowledge-graph
uv sync

touch .env && chmod 600 .env    # Then add OPENALEX_API_KEY=... with an editor
export SHKG_DATA_DIR=/path/with/space/you/alone/can/read
mkdir -p "$SHKG_DATA_DIR" && chmod 700 "$SHKG_DATA_DIR"
ls -ld .env "$SHKG_DATA_DIR"    # Check that the group and others have no access
```

On a shared machine:

- **Your key spends your money.** Keep it out of commands, shell history and shared files. Use `.env`, which `shkg` warns about if others can read it. An administrator can still read your files, so use a machine and administrators you trust.
- **Avoid passing the key on a command line.** This includes OpenAlex's own `openalex download --api-key`, since other users can see running commands. That tool also has no spending cap, which is why `shkg fulltext` exists.
- **Raw data stays private.** Raw records hold abstract indexes, and full text is under copyright. `shkg` creates its files readable only by you. Don't change this for `raw/` or `fulltext/` to share them with the group; share derived tables instead.
- **Survive logouts.** Long runs should go in `tmux` or `screen`.

If the key may have been exposed, rotate it at [Settings → API](https://openalex.org/settings/api).

## Run it

```bash
uv run shkg scope-report        # Confirms the key works
uv run shkg ingest              # Up to $1.86. Rerun the next day to resume
uv run shkg graph build
uv run shkg graph validate

# Pilot. The 0.10 covers listing the works to fetch.
uv run shkg fulltext --set bridge_keyword_and --limit 500 --format xml --max-usd 5.10
```

The free budget caps each UTC day at $1. To spend prepaid credit within one day, raise that guard for the run. Only do this if you have the credit:

```bash
SHKG_OPENALEX_DAILY_USD=5.20 uv run shkg fulltext --set bridge_keyword_and --limit 500 --format xml --max-usd 5.10
```

`shkg fulltext` takes the most-cited works in the set that OpenAlex holds in that format, so it favors older and review papers. TEI XML is the better format for extraction. PDFs average about 5 MB each per the OpenAlex docs, so 10,000 of them need about 50 GB.

Commands can be rerun safely: `ingest` resumes from its checkpoint, and `fulltext` skips files already on disk.

| Exit code | Meaning | What to do |
|---|---|---|
| 0 | Finished | Next step |
| 1 | Graph validation failed | Don't publish. Read the listed violations |
| 2 | Stopped at a spending cap | Rerun after midnight UTC, or add credit and raise the cap |
| 3 | API error, including rate limits | Wait a few minutes and rerun. New accounts are paced at $0.10 per 5 minutes for the first $1 |

## Afterward

- **Spend.** Each run writes a manifest to `$SHKG_DATA_DIR/manifests/` with its dollars spent. The ledger `openalex_ledger.json` only knows about spend made through `shkg`, so compare it with your OpenAlex dashboard.
- **What can leave the machine.** `graph/*.parquet` tables and manifests, once `shkg graph validate` has passed. Never `raw/` or `fulltext/`.
- **What OpenAlex holds.** Its full-text copies cover open-access works, but licenses vary by work. Check licenses before any reuse beyond local text mining.
