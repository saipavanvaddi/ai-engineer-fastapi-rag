# AI_Engineer

FastAPI backend for the Embeddings → Vector DB → RAG learning roadmap
(Manakarto-style examples used for learning).

## Setup

```
venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

Requires `OPENAI_API_KEY`, `HOST`, `PORT` in `.env`. Past Step 3 (vector storage), also
requires the pgvector Postgres container:

```
docker compose up -d
python scripts/init_db.py
python scripts/seed_documents.py   # optional: loads documents/*.txt as sample data
```

See [docs/vector-storage.md](docs/vector-storage.md) for why this runs in Docker (native
Postgres has no pgvector without compiling it) and full details.

## Structure

```
app/
├── main.py              # FastAPI app + route registration
├── schemas/              # Pydantic request/response models
├── services/              # Business logic (OpenAI calls, chunking, etc.)
├── db/                    # Postgres connection (psycopg)
└── static/                # Browser test UI

documents/                 # Sample .txt files for seeding/uploading
sql/                       # Schema SQL
scripts/                   # One-off setup scripts (init_db.py, seed_documents.py)
docker-compose.yml         # pgvector Postgres container
```

## Docs

- [docs/embeddings-flow.md](docs/embeddings-flow.md) — step-by-step flow, run commands, and progress
- [docs/vector-storage.md](docs/vector-storage.md) — Postgres + pgvector setup (database, schema, script)
