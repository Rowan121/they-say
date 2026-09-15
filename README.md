# They Say · Ground Truthing

**Live demo:** <https://rowan121.github.io/they-say/>

Common knowledge has a citation trail — and sometimes it leads nowhere the
source ever went. Each case here is a "fact" everyone repeats, traced back to
what the original study actually found. Watch a real result mutate as it
spreads, while the counter-evidence sits ignored off to the side.

Current cases:

| # | Claim | What the source actually said |
|---|-------|-------------------------------|
| 🐦 | Hummingbird sugar water must be **1:4** (~20%) | The cited papers never prescribed it; Blem et al. 2000 found birds prefer ~50% sucrose — and sits uncited |
| 🥩 | You can only absorb **~40g protein per meal** | A 20g MPS plateau in six young men; later work found no upper limit |
| 🧠 | The **Dunning-Kruger effect** — the least skilled are most overconfident | Four small studies plus an internet-fabricated curve; random numbers reproduce it |
| 🏠 | The most expensive house in the world is **$4 billion** | A compounded projection about Antilia; no $4B transaction has ever existed |
| 👟 | You need **10,000 steps** a day | A 1965 pedometer brand's product name; benefits plateau thousands of steps lower |

![Ground Truthing visualization](docs/screenshot.png)

In each graph: edge **thickness** = citation strength, edge **color** =
confidence the citation is faithful (red = mutated claim, green = faithful).
The mis-read anchor sits in the middle, popularized claims fan out on the
left, overlooked correct evidence clusters on the right, and the isolated
counter-truth stands alone at the far right.

## Repository layout

```
frontend/           D3 force-graph visualization (index.html) + graph.json data
backend/            Neo4j GraphRAG snapshot + case data + build/import scripts
backend/data/cases/ One JSON file per curated case study (the source of truth)
docs/               Screenshot
```

`frontend/graph.json` is a **build artifact**. It is merged from
`backend/data/cases/*.json` plus shared metadata in
`backend/data/cases_meta.json`:

```
python3 backend/build_cases.py
```

To add a new case, drop `<case_id>.json` into `backend/data/cases/` (same
schema as the existing files), add its metadata to `cases_meta.json`, and
rebuild. Node `stance` values: `mutated_claim` (layers 1–3, most viral on the
left), `pivotal` (layer 4, the misread anchor), `evidence` (layer 5),
`isolated_truth` (layer 6, pinned at the far right). Edge `kind` values:
`faithful`, `overstated`, `mutated`.

## View the visualization locally

The page fetches `graph.json`, so it needs a local web server — opening the
file directly (`file://`) will not work.

```
cd frontend
python3 -m http.server 8777
```

Then open <http://127.0.0.1:8777> in your browser. Anyone who clones this repo
can do the same; no deployment required. The landing page lists every case;
click one to walk its mutation graph, or jump straight to a case with
`#<case_id>` in the URL.

## Backend (Neo4j)

Two graphs live in the same Neo4j Aura instance:

1. **GraphRAG ingestion** — `backend/data/` is a snapshot of the knowledge
   graph that document-intelligence ingestion built from the source PDFs:
   **80 documents**, **840 extracted claims** (with numeric `ratio_value` /
   `ratio_min` / `ratio_max` fields), **25 text chunks**, and **3 source PDFs**.
   Chunk vector embeddings are excluded (large and regenerable).

   ```
   pip install -r backend/requirements.txt
   export NEO4J_URI="neo4j+s://<instance>.databases.neo4j.io"
   export NEO4J_USER="neo4j"
   export NEO4J_PASSWORD="<your-password>"
   python3 backend/import_backend.py
   ```

   Re-dump a live instance back to `backend/data/` with
   `python3 backend/export_backend.py` (same environment variables).

2. **Curated case studies** — the same corpus visualized by the frontend,
   synced from `backend/data/cases/*.json`:

   ```
   python3 backend/import_cases.py            # merge/update cases
   python3 backend/import_cases.py --clear    # drop case data first, then import
   ```

   This creates `(:CaseStudy)` nodes linked via `[:HAS_DOCUMENT]` to
   `(:Document)` nodes carrying `case_id` and `stance`, plus scored
   `[:CITES]` edges (`strength`, `confidence`, `kind`, `label`) — see
   `backend/schema.cypher`.

No credentials are stored in this repo; the scripts read them from the
environment.
