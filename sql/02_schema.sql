-- Run this against ai_engineer_embeddings (after 01_create_database.sql),
-- either manually via psql or automatically via scripts/init_db.py.
--
-- psql -U postgres -h 127.0.0.1 -p 5432 -d ai_engineer_embeddings -f sql/02_schema.sql

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
