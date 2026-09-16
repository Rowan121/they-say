#!/usr/bin/env python3
"""Export graph.json from Neo4j Aura — makes the database the source of truth.

Queries CaseStudy + Document + CITES data from Neo4j and writes
frontend/graph.json in the format the D3 frontend expects.

Usage:
    /usr/bin/python3 backend/export_from_neo4j.py

Requires: pip install neo4j
Credentials: .env (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
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
OUT = ROOT / "frontend" / "graph.json"
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
    uri = normalize_uri(os.environ.get("NEO4J_URI", ""))
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    if not uri or not password:
        sys.exit("Set NEO4J_URI and NEO4J_PASSWORD in .env")

    local_meta = json.loads(META_FILE.read_text(encoding="utf-8"))

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=database) as s:
            cases_raw = s.run(
                "MATCH (c:CaseStudy) RETURN c ORDER BY c.order"
            ).data()

            docs_raw = s.run(
                "MATCH (c:CaseStudy)-[:HAS_DOCUMENT]->(d:Document) "
                "RETURN d, c.case_id AS case_id ORDER BY c.order, d.year"
            ).data()

            edges_raw = s.run(
                "MATCH (a:Document)-[r:CITES]->(b:Document) "
                "RETURN a.__id__ AS source, b.__id__ AS target, "
                "r.strength AS strength, r.confidence AS confidence, "
                "r.kind AS kind, r.label AS label"
            ).data()
    finally:
        driver.close()

    nodes_by_case = {}
    for row in docs_raw:
        d = dict(row["d"])
        cid = row["case_id"]
        node = {
            "id": d.get("__id__", ""),
            "title": d.get("title", ""),
            "authors": d.get("authors", ""),
            "year": d.get("year", 0),
            "type": d.get("type", ""),
            "layer": d.get("layer", 0),
            "url": d.get("url", ""),
            "stance": d.get("stance", ""),
            "claim": d.get("claim", ""),
            "ratio": d.get("ratio", ""),
            "verified": d.get("verified", False),
            "note": d.get("note", ""),
            "case_id": cid,
        }
        nodes_by_case.setdefault(cid, []).append(node)

    edges_by_case = {}
    for e in edges_raw:
        cid = None
        for node_list in nodes_by_case.values():
            if any(n["id"] == e["source"] for n in node_list):
                cid = node_list[0]["case_id"]
                break
        if cid:
            edges_by_case.setdefault(cid, []).append({
                "source": e["source"],
                "target": e["target"],
                "strength": e.get("strength", 0.5),
                "confidence": e.get("confidence", 0.5),
                "kind": e.get("kind", ""),
                "label": e.get("label", ""),
            })

    cases = []
    all_nodes, all_edges = [], []
    for c in cases_raw:
        props = dict(c["c"])
        cid = props["case_id"]
        meta = local_meta.get(cid, {})
        case_entry = {
            "id": cid,
            "icon": props.get("icon", meta.get("icon", "")),
            "title": props.get("title", meta.get("title", "")),
            "popular_claim": props.get("popular_claim", meta.get("popular_claim", "")),
            "verdict": props.get("verdict", meta.get("verdict", "")),
            "summary": props.get("summary", meta.get("summary", "")),
            "accent": props.get("accent", meta.get("accent", "#888")),
            "doc_count": len(nodes_by_case.get(cid, [])),
            "edge_count": len(edges_by_case.get(cid, [])),
        }
        cases.append(case_entry)
        all_nodes += nodes_by_case.get(cid, [])
        all_edges += edges_by_case.get(cid, [])

    out = {
        "meta": {
            "project": "They Say — Ground Truthing",
            "generated_by": "backend/export_from_neo4j.py",
            "note": "Exported from Neo4j Aura. The database is the source of truth.",
        },
        "cases": cases,
        "nodes": all_nodes,
        "edges": all_edges,
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(f"Exported {len(cases)} cases, {len(all_nodes)} nodes, "
          f"{len(all_edges)} edges → {OUT}")


if __name__ == "__main__":
    main()
