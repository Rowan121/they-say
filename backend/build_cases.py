#!/usr/bin/env python3
"""Merge per-case graph files in data/cases/ into frontend/graph.json.

frontend/graph.json is a BUILD ARTIFACT — do not hand-edit it.
Add or edit a case by dropping <case_id>.json into data/cases/ and
updating CASE_META below, then run:  python3 backend/build_cases.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "backend" / "data" / "cases"
META_FILE = ROOT / "backend" / "data" / "cases_meta.json"
OUT = ROOT / "frontend" / "graph.json"

CASE_META = json.loads(META_FILE.read_text())


def main():
    case_files = sorted(CASES_DIR.glob("*.json"))
    if not case_files:
        raise SystemExit(f"no case files in {CASES_DIR}")

    all_nodes, all_edges, cases = [], [], []
    for f in case_files:
        case = json.loads(f.read_text())
        cid = case["case_id"]
        if cid not in CASE_META:
            raise SystemExit(f"{f.name}: case_id '{cid}' missing from {META_FILE.name}")
        nodes = case["nodes"]
        edges = case["edges"]
        for n in nodes:
            n.setdefault("case_id", cid)
        all_nodes += nodes
        all_edges += edges
        meta = dict(CASE_META[cid])
        meta["id"] = cid
        meta["doc_count"] = len(nodes)
        meta["edge_count"] = len(edges)
        cases.append(meta)

    cases.sort(key=lambda c: c["order"])
    for c in cases:
        c.pop("order", None)

    ids = [n["id"] for n in all_nodes]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise SystemExit(f"duplicate node ids across cases: {dupes}")
    node_ids = set(ids)
    for e in all_edges:
        for k in ("source", "target"):
            if e[k] not in node_ids:
                raise SystemExit(f"edge references unknown node '{e[k]}'")

    out = {
        "meta": {
            "project": "They Say — Ground Truthing",
            "generated_by": "backend/build_cases.py",
            "note": "Build artifact: merged from backend/data/cases/*.json. "
                    "Edit the case files, then rebuild. The Neo4j Aura instance "
                    "holds the GraphRAG ingestion; this file drives the frontend.",
        },
        "cases": cases,
        "nodes": all_nodes,
        "edges": all_edges,
    }
    OUT.write_text(json.dumps(out, indent=1))
    total_e = len(all_edges)
    print(f"wrote {OUT} — {len(cases)} cases, {len(all_nodes)} nodes, {total_e} edges")


if __name__ == "__main__":
    main()
