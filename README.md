# They Say · Ground Truthing

**Live demo:** <https://rowan121.github.io/they-say/>

## The proposed system — "GroundTruth" claim tracker

The five cases below are curated by hand. The plan is to automate this: an
open-source pipeline that ingests documents, extracts verifiable claims, and
tracks how each claim mutates or gets refuted **over time**. Full proposal:
[Proposed System Architecture for "GroundTruth" Claim Tracker](docs/Proposed%20System%20Architecture%20for%20“GroundTruth”%20Claim%20Tracker.pdf)
· worked example on the hummingbird rule:
[Tracing the Hummingbird "One-to-Four" Rule Back to the Science](docs/Tracing%20the%20Hummingbird%20“One-to-Four”%20Rule%20Back%20to%20the%20Science.pdf)

How it works, in four stages:

1. **Ingest & extract claims** — chunk the corpus (papers, blog posts, gov
   pages), then an LLM (GPT-4o class, or an open model) splits each chunk into
   verifiable claim triples (subject–predicate–object), each tagged with its
   source document and publication date.
2. **Store as a time-aware knowledge graph** — claims, authors, and
   publications are nodes; `cites` / `supports` / `refutes` are edges. A graph
   DB (Neo4j or ArangoDB) holds the graph; a vector store (Weaviate/Milvus)
   indexes claim embeddings for semantic lookup. Hybrid search = vector
   similarity to find candidate claims + graph traversal to walk the evidence
   chain.
3. **Track claims through time** — every claim carries `valid_from` (and
   `valid_until` once superseded). An invalidation pass flags earlier claims
   that newer evidence contradicts, so the system can answer questions like
   *"which widely-cited claim was later refuted?"* and *"what was the
   consensus in 2010 vs today?"* — the temporal question the current
   prototype can't answer.
4. **Update continuously** — new documents flow through the same pipeline
   (chunk → extract → embed → index), so the graph stays current without
   manual curation.

Why build it: the current Neo4j GraphRAG prototype proved the concept, but the
free tier caps document intelligence at 25 chunks per source — fine for a demo,
not for a real corpus. This design is the reproducible, open-source path (the
proposal also covers deployment: Python services, Airflow/Kafka orchestration,
Docker).

---

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
docs/               Design PDFs (proposed system, hummingbird trace) + screenshot
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
