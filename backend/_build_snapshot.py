import json, pathlib

TMP = "/Users/rowancooper/.qoder/tmp/-Users-rowancooper-Documents-Qoder-2026-09-12-38818de0/c58754ad-e17e-4ee4-b1c8-6698d15b2594/tool-results"
OUT = pathlib.Path(__file__).resolve().parent / "data"
OUT.mkdir(parents=True, exist_ok=True)

docs = json.load(open(f"{TMP}/neo4j_read-cypher_ead01aee7e5c.txt"))
chunks = json.load(open(f"{TMP}/neo4j_read-cypher_f3c09a17aa3e.txt"))

source_documents = [
  {"id":"18766d73-2345-4319-b1dd-edf97e7efaad","document_type":"pdf","file_size":"2325650","createdAt":"2026-09-12T23:56:40.436222+00:00","path":"Johanna-Juntunen_Food-Preference-by-Hummingbirds-Visiting-Feeders_2023.pdf"},
  {"id":"23694c3d-9c29-4cc8-97dd-ab3a30b4a637","document_type":"pdf","file_size":"812418","createdAt":"2026-09-12T23:56:40.438796+00:00","path":"Rufous_Hummingbird_Sucrose_Preference__Precision_of_Selection_Var.pdf"},
  {"id":"8e9627b1-df4d-482c-8f66-5e9ccbe7468a","document_type":"pdf","file_size":"162375","createdAt":"2026-09-12T23:56:40.439401+00:00","path":"condor0054.pdf"},
]

json.dump(docs, open(OUT/"documents_claims.json","w"), indent=2, ensure_ascii=False)
json.dump(chunks, open(OUT/"chunks.json","w"), indent=2, ensure_ascii=False)
json.dump(source_documents, open(OUT/"source_documents.json","w"), indent=2, ensure_ascii=False)

n_docs = len(docs)
n_claims = sum(len(d["claims"]) for d in docs)
n_chunks = len(chunks)
manifest = {
  "generated_from": "Neo4j Aura instance 04bf4cb1 (GraphRAG document-intelligence ingestion)",
  "counts": {"documents": n_docs, "claims": n_claims, "chunks": n_chunks, "source_pdfs": len(source_documents)},
  "note": "Vector embeddings on chunks are intentionally excluded (regenerable, large). Rebuild with import_backend.py."
}
json.dump(manifest, open(OUT/"manifest.json","w"), indent=2, ensure_ascii=False)
print("wrote:", n_docs, "documents,", n_claims, "claims,", n_chunks, "chunks")
