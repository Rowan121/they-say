#!/usr/bin/env python3
"""Sync curated case studies (backend/data/cases/*.json) into Neo4j Aura.

Additive on top of the GraphRAG backend - creates:
    (:CaseStudy {case_id, title, icon, popular_claim, verdict, summary, accent, order})
    (:Document {__id__, title, authors, year, type, layer, url, stance, claim,
                ratio, verified, note, case_id})
    (CaseStudy)-[:HAS_DOCUMENT]->(Document)
    (Document)-[:CITES {strength, confidence, kind, label}]->(Document)

Credentials come from the environment, with a fallback to a .env file in the
project root:
    export NEO4J_URI="neo4j+s://<instance>.databases.neo4j.io"
    export NEO4J_USER="neo4j"
    export NEO4J_PASSWORD="<your-password>"
    python3 backend/import_cases.py            # merge/update
    python3 backend/import_cases.py --clear    # drop case data first, then import

Requires: pip install neo4j
"""
import json
import os
import pathlib
import sys

try:
    from neo4j import GraphDatabase
except ImportError:
    sys.exit("Missing dependency. Run: pip install neo4j")

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "backend" / "data" / "cases"
META_FILE = ROOT / "backend" / "data" / "cases_meta.json"


def load_env():
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def normalize_uri(uri):
    if uri.startswith("http://") or uri.startswith("https://"):
        return "neo4j+s://" + uri.split("://", 1)[1]
    return uri


def main():
    load_env()
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri or not password:
        sys.exit("Set NEO4J_URI and NEO4J_PASSWORD environment variables first.")
    uri = normalize_uri(uri)

    meta = json.loads(META_FILE.read_text(encoding="utf-8"))
    cases, all_nodes, all_edges, case_ids = [], [], [], []
    for f in sorted(CASES_DIR.glob("*.json")):
        case = json.loads(f.read_text(encoding="utf-8"))
        cid = case["case_id"]
        if cid not in meta:
            sys.exit(f"{f.name}: case_id '{cid}' missing from {META_FILE.name}")
        case_ids.append(cid)
        m = dict(meta[cid])
        order = m.pop("order")
        cases.append({"case_id": cid, "order": order, **m})
        for n in case["nodes"]:
            n.setdefault("case_id", cid)
        all_nodes += case["nodes"]
        all_edges += case["edges"]

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as s:
            s.run(
                "CREATE CONSTRAINT case_study_id IF NOT EXISTS "
                "FOR (c:CaseStudy) REQUIRE c.case_id IS UNIQUE"
            )

            if "--clear" in sys.argv:
                s.run("MATCH (c:CaseStudy) DETACH DELETE c")
                s.run(
                    "MATCH (d:Document) WHERE d.case_id IN $ids "
                    "OR any(cid IN $ids WHERE d.__id__ STARTS WITH cid + '_') "
                    "DETACH DELETE d",
                    ids=case_ids,
                )
                print("Cleared existing case data.")

            s.run(
                """
                UNWIND $cases AS cs
                MERGE (c:CaseStudy {case_id: cs.case_id})
                SET c.title = cs.title, c.icon = cs.icon,
                    c.popular_claim = cs.popular_claim, c.verdict = cs.verdict,
                    c.summary = cs.summary, c.accent = cs.accent, c.order = cs.order
                """,
                cases=cases,
            )
            s.run(
                """
                UNWIND $nodes AS n
                MERGE (d:Document {__id__: n.id})
                SET d.title = n.title, d.authors = n.authors, d.year = n.year,
                    d.type = n.type, d.layer = n.layer, d.url = n.url,
                    d.stance = n.stance, d.claim = n.claim, d.ratio = n.ratio,
                    d.verified = n.verified, d.note = n.note, d.case_id = n.case_id
                WITH d, n
                MATCH (c:CaseStudy {case_id: n.case_id})
                MERGE (c)-[:HAS_DOCUMENT]->(d)
                """,
                nodes=all_nodes,
            )
            s.run(
                """
                UNWIND $edges AS e
                MATCH (a:Document {__id__: e.source})
                MATCH (b:Document {__id__: e.target})
                MERGE (a)-[r:CITES]->(b)
                SET r.strength = e.strength, r.confidence = e.confidence,
                    r.kind = e.kind, r.label = e.label
                """,
                edges=all_edges,
            )
    finally:
        driver.close()

    print(f"Imported {len(cases)} cases, {len(all_nodes)} documents, "
          f"{len(all_edges)} citations.")


if __name__ == "__main__":
    main()
