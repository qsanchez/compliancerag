# Folder Dependency Diagram

Code-level relationships between the main folders of the ComplianceRAG repo.

```mermaid
flowchart TD
    api["**api/**\nFastAPI · Lambda handler\nrouters · middleware"]
    agent["**agent/**\nLangGraph graph\nrouter · tools"]
    rag["**rag/**\npipeline · retriever\nreranker · context_builder"]
    ingestion["**ingestion/**\nloaders · chunker · indexer"]
    vectorstore["**vectorstore/**\nembedder · client\n(Chroma / pgvector)"]
    audit["**audit/**\nAuditLogger"]
    observability["**observability/**\nLangSmith setup"]
    evaluation["**evaluation/**\nRAGAS evaluator"]
    analytics_etl["**analytics_etl/**\nCSV → Parquet → S3"]
    analytics_query["**analytics_query/**\nquery_metrics · generate_chart"]
    infra["**infra/**\nTerraform IaC"]
    tests["**tests/**\nunit · integration\nregression"]

    api -->|"invoke graph()"| agent
    api -->|"log_query()"| audit
    api -->|"setup()"| observability

    agent -->|"pipeline.run()"| rag
    agent -->|"query_metrics · generate_chart"| analytics_query

    rag -->|"embed() · get_collection()"| vectorstore
    ingestion -->|"embed() · get_collection()"| vectorstore

    evaluation -->|"pipeline.run()"| rag
    evaluation -->|"embed()"| vectorstore

    infra -.->|"Lambda · API Gateway"| api
    infra -.->|"RDS · Chroma"| vectorstore
    infra -.->|"S3 · Athena"| analytics_etl
    infra -.->|"Athena"| analytics_query

    tests -->|"covers"| agent
    tests -->|"covers"| rag
    tests -->|"covers"| ingestion
    tests -->|"covers"| vectorstore
    tests -->|"covers"| analytics_query
```

## Notes

- Solid arrows = Python import dependencies
- Dashed arrows = runtime infrastructure provisioned by Terraform (no Python imports)
- `vectorstore/` is the shared DB access layer — both `ingestion/` and `rag/` depend on it
- `analytics_etl/` has no cross-folder Python imports (standalone ETL scripts)
- `analytics_query/` is called by `agent/` and reads from Athena at runtime
- `audit/` and `observability/` are leaf modules — nothing imports from them except `api/`
