// GraphRAG backend schema for the ground-truthing knowledge graph.
// Ingested into Neo4j Aura by Qoder document-intelligence (GraphRAG).
//
// Node labels
//   (:Document {__id__, filename})                         -- a cited source
//   (:Claim {__id__, text, semantic_type,                  -- an extracted claim
//            ratio_value, ratio_min, ratio_max, ratio_unit})
//   (:__Chunk__ {__id__, index, text, prev_chunk_uid,      -- chunked source text
//                embedding})                                --   (embedding excluded from snapshot)
//   (:__Document__ {__id__, path, document_type,           -- the ingested source PDF
//                   file_identifier, file_size, createdAt})
//   (Document and Claim also carry the internal :__Entity__ label)
//   (:CaseStudy {case_id, title, icon, popular_claim, verdict,
//                summary, accent, order})                   -- curated mutation
//                                                             story (import_cases.py)
//
// Relationships
//   (:Document)-[:CONTAINS_CLAIM]->(:Claim)
//   (:__Chunk__)-[:__CHUNK_TO_DOCUMENT__]->(:__Document__)
//   (:__Chunk__)-[:__NEXT_CHUNK__]->(:__Chunk__)
//   (:Document|:Claim)-[:__NODE_TO_CHUNK__]->(:__Chunk__)
//   (:CaseStudy)-[:HAS_DOCUMENT]->(:Document)               -- curated corpus
//   (:Document)-[:CITES {strength, confidence, kind,
//                        label}]->(:Document)                 -- curated citation with
//                                                             faithfulness score

CREATE CONSTRAINT document_id IF NOT EXISTS
  FOR (d:Document) REQUIRE d.__id__ IS UNIQUE;

CREATE CONSTRAINT claim_id IF NOT EXISTS
  FOR (c:Claim) REQUIRE c.__id__ IS UNIQUE;

CREATE CONSTRAINT chunk_id IF NOT EXISTS
  FOR (ch:__Chunk__) REQUIRE ch.__id__ IS UNIQUE;

CREATE CONSTRAINT source_document_id IF NOT EXISTS
  FOR (sd:__Document__) REQUIRE sd.__id__ IS UNIQUE;
