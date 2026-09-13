#!/usr/bin/env python3
"""Dump the ground-truthing GraphRAG backend from Neo4j into backend/data/*.json.

Credentials come from the environment - nothing is hardcoded:
    export NEO4J_URI="neo4j+s://<instance>.databases.neo4j.io"
    export NEO4J_USER="neo4j"
    export NEO4J_PASSWORD="<your-password>"
    python3 backend/export_backend.py

Requires: pip install neo4j
Chunk vector embeddings are intentionally omitted (large, regenerable).
"""
import json
import os
import pathlib
import sys

try:
    from neo4j import GraphDatabase
except ImportError:
    sys.exit("Missing dependency. Run: pip install neo4j")

DATA = pathlib.Path(__file__).resolve().parent / "data"
DATA.mkdir(parents=True, exist_ok=True)

Q_DOCS = """
MATCH (d:Document)
WITH d ORDER BY d.__id__
OPTIONAL MATCH (d)-[:CONTAINS_CLAIM]->(c:Claim)
WITH d, [x IN collect({id:c.__id__, text:c.text, semantic_type:c.semantic_type,
         ratio_value:c.ratio_value, ratio_min:c.ratio_min, ratio_max:c.ratio_max,
         ratio_unit:c.ratio_unit}) WHERE x.id IS NOT NULL] AS claims
RETURN d.__id__ AS id, d.filename AS filename, claims
"""

Q_CHUNKS = """
MATCH (ch:__Chunk__)
OPTIONAL MATCH (ch)-[:__CHUNK_TO_DOCUMENT__]->(sd:__Document__)
OPTIONAL MATCH (ch)-[:__NEXT_CHUNK__]->(nx:__Chunk__)
RETURN ch.__id__ AS id, ch.index AS index, ch.text AS text,
       ch.prev_chunk_uid AS prev_chunk_uid, sd.__id__ AS source_document,
       nx.__id__ AS next_chunk
ORDER BY ch.index
"""

Q_SOURCES = """
MATCH (sd:__Document__)
RETURN sd.__id__ AS id, sd.path AS path, sd.document_type AS document_type,
       sd.file_identifier AS file_identifier, sd.file_size AS file_size,
       sd.createdAt AS createdAt
"""


def write(name, rows):
    json.dump(rows, open(DATA / name, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def main():
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri or not password:
        sys.exit("Set NEO4J_URI and NEO4J_PASSWORD environment variables first.")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as s:
        docs = [r.data() for r in s.run(Q_DOCS)]
        chunks = [r.data() for r in s.run(Q_CHUNKS)]
        sources = [r.data() for r in s.run(Q_SOURCES)]
    driver.close()

    write("documents_claims.json", docs)
    write("chunks.json", chunks)
    write("source_documents.json", sources)
    n_claims = sum(len(d["claims"]) for d in docs)
    write("manifest.json", {
        "generated_from": "Neo4j (GraphRAG document-intelligence ingestion)",
        "counts": {"documents": len(docs), "claims": n_claims,
                   "chunks": len(chunks), "source_pdfs": len(sources)},
        "note": "Vector embeddings on chunks are intentionally excluded (regenerable, large).",
    })
    print(f"Exported {len(docs)} documents, {n_claims} claims, "
          f"{len(chunks)} chunks, {len(sources)} source PDFs.")


if __name__ == "__main__":
    main()
