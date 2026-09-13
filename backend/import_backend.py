#!/usr/bin/env python3
"""Rebuild the ground-truthing GraphRAG backend into Neo4j from the JSON snapshot.

Credentials come from the environment - nothing is hardcoded:
    export NEO4J_URI="neo4j+s://<instance>.databases.neo4j.io"
    export NEO4J_USER="neo4j"
    export NEO4J_PASSWORD="<your-password>"
    python3 backend/import_backend.py

Requires: pip install neo4j
Note: chunk vector embeddings are not in the snapshot; regenerate them
with your embedding pipeline after import if you need vector search.
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


def load(name):
    return json.load(open(DATA / name, encoding="utf-8"))


def main():
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri or not password:
        sys.exit("Set NEO4J_URI and NEO4J_PASSWORD environment variables first.")

    docs = load("documents_claims.json")
    chunks = load("chunks.json")
    sources = load("source_documents.json")

    schema_stmts = [
        s.strip() for s in (pathlib.Path(__file__).resolve().parent / "schema.cypher")
        .read_text(encoding="utf-8").split(";")
        if s.strip() and not s.strip().startswith("//")
    ]

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as s:
        for stmt in schema_stmts:
            s.run(stmt)

        s.run(
            """
            UNWIND $sources AS sd
            MERGE (d:__Document__ {__id__: sd.id})
            SET d.path = sd.path, d.document_type = sd.document_type,
                d.file_size = sd.file_size, d.createdAt = sd.createdAt
            """,
            sources=sources,
        )

        s.run(
            """
            UNWIND $docs AS doc
            MERGE (d:Document {__id__: doc.id})
            SET d.filename = doc.filename, d:__Entity__
            WITH d, doc
            UNWIND doc.claims AS cl
            MERGE (c:Claim {__id__: cl.id})
            SET c.text = cl.text, c.semantic_type = cl.semantic_type,
                c.ratio_value = cl.ratio_value, c.ratio_min = cl.ratio_min,
                c.ratio_max = cl.ratio_max, c.ratio_unit = cl.ratio_unit, c:__Entity__
            MERGE (d)-[:CONTAINS_CLAIM]->(c)
            """,
            docs=docs,
        )

        s.run(
            """
            UNWIND $chunks AS ch
            MERGE (c:__Chunk__ {__id__: ch.id})
            SET c.index = ch.index, c.text = ch.text, c.prev_chunk_uid = ch.prev_chunk_uid
            WITH c, ch
            MATCH (sd:__Document__ {__id__: ch.source_document})
            MERGE (c)-[:__CHUNK_TO_DOCUMENT__]->(sd)
            """,
            chunks=chunks,
        )

        s.run(
            """
            UNWIND $chunks AS ch
            WITH ch WHERE ch.next_chunk IS NOT NULL
            MATCH (a:__Chunk__ {__id__: ch.id})
            MATCH (b:__Chunk__ {__id__: ch.next_chunk})
            MERGE (a)-[:__NEXT_CHUNK__]->(b)
            """,
            chunks=chunks,
        )

    driver.close()
    n_claims = sum(len(d["claims"]) for d in docs)
    print(f"Imported {len(docs)} documents, {n_claims} claims, "
          f"{len(chunks)} chunks, {len(sources)} source PDFs.")


if __name__ == "__main__":
    main()
