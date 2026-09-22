# Vector Storage — PostgreSQL + pgvector

Stores chunk embeddings in Postgres so they can be searched later instead of
recomputing everything in memory on every request.

## Running via Docker (what we're actually using)

The native local Postgres 18 install has no `pgvector` extension, and building it from
source on Windows needs Visual Studio Build Tools (MSVC) which weren't installed — too
heavy for this. Using the official `pgvector/pgvector` Docker image instead: pgvector is
pre-installed, no compiling needed.

Runs on **port 5433** (not 5432) so it doesn't conflict with the native Postgres install.

**Start it:**

```
cd D:\Projects\AI_Engineer
docker compose up -d
```

(File: [`docker-compose.yml`](../docker-compose.yml) — `pgvector/pgvector:pg16`, database
`ai_engineer_embeddings`, data persisted in the named volume `ai_engineer_pgvector_data`.)

**Stop it** (data persists in the volume): `docker compose down`
**Stop it and wipe all data**: `docker compose down -v`

`DATABASE_URL` in `.env` already points here:

```
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5433/ai_engineer_embeddings
```

## Apply the schema

```
cd D:\Projects\AI_Engineer
venv\Scripts\activate
python scripts/init_db.py
```

Reads `DATABASE_URL` from `.env` and runs [`sql/02_schema.sql`](../sql/02_schema.sql) —
enables the `vector` extension and creates `document_chunks` if it doesn't exist already.
Safe to re-run (`CREATE EXTENSION IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`).

Verified live:

```
$ python scripts/init_db.py
Applied 02_schema.sql — pgvector extension + document_chunks table ready.

$ docker exec ai_engineer_pgvector psql -U postgres -d ai_engineer_embeddings -c "\d document_chunks"
   Column    |           Type           | Nullable |                   Default
-------------+--------------------------+----------+----------------------------------------------
 id          | bigint                   | not null | nextval('document_chunks_id_seq'::regclass)
 document_id | bigint                   |          |
 content     | text                     | not null |
 embedding   | vector(1536)             |          |
 metadata    | jsonb                    |          |
 created_at  | timestamp with time zone | not null | now()
```

pgvector extension version `0.8.6` confirmed installed.

## Table shape

| Column      | Type          | Notes                                    |
|-------------|---------------|-------------------------------------------|
| id          | BIGSERIAL     | primary key                               |
| document_id | BIGINT        | groups chunks from the same source doc    |
| content     | TEXT          | the chunk text itself                     |
| embedding   | VECTOR(1536)  | matches `text-embedding-3-small`'s output |
| metadata    | JSONB         | source filename, page, etc.               |
| created_at  | TIMESTAMPTZ   | defaults to `now()`                       |

## Files

- [`docker-compose.yml`](../docker-compose.yml) — pgvector Postgres container definition
- [`app/db/database.py`](../app/db/database.py) — `get_connection()`, reads `DATABASE_URL` via `psycopg`
- [`sql/02_schema.sql`](../sql/02_schema.sql) — extension + `document_chunks` table
- [`scripts/init_db.py`](../scripts/init_db.py) — applies `sql/02_schema.sql` automatically

`sql/01_create_database.sql` (manual `CREATE DATABASE`) is no longer needed — the Docker
image's `POSTGRES_DB` env var creates `ai_engineer_embeddings` automatically on first boot.

## Storing chunks

`POST /api/embeddings/store` chunks text, embeds each chunk, and inserts into
`document_chunks` — see [docs/embeddings-flow.md](embeddings-flow.md#step-4--store-vectors-pgvector-)
for the request shape and a verified example. `POST /api/embeddings/chunk` remains a
pure preview (chunks + embeddings returned, nothing written to the table).

## Not done yet

- No similarity search against the table yet — that's Step 5, using pgvector's `<=>`
  (cosine distance) operator instead of doing cosine similarity in Python/numpy.
