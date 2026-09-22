# AI_Engineer

FastAPI backend for the Embeddings → Vector DB → RAG learning roadmap
(Manakarto-style examples used for learning).

## Tech stack

- **[FastAPI](https://fastapi.tiangolo.com/)** 0.141 — API framework
- **[OpenAI API](https://platform.openai.com/)** (`openai` 3.17) — `text-embedding-3-small` for embeddings, `gpt-5-mini` for the RAG answer
- **[PostgreSQL](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector)** (via Docker, `pgvector/pgvector:pg16`) — vector storage and `<=>` cosine-distance search
- **[psycopg](https://www.psycopg.org/psycopg3/)** 3.3 (`psycopg[binary]`) — Postgres driver
- **[Docker Compose](https://docs.docker.com/compose/)** — runs the pgvector Postgres container
- **[NumPy](https://numpy.org/)** — cosine similarity for the in-memory ranking endpoint
- **[Uvicorn](https://www.uvicorn.org/)** — ASGI server
- **python-multipart** — file upload support (`UploadFile`)
- **python-dotenv** — loads `.env`
- Plain HTML/CSS/JS (no framework) for the browser test UI at `/`

## API endpoints

| Endpoint                      | What it does                                              |
|--------------------------------|-------------------------------------------------------------|
| `POST /api/embeddings`         | Text → embedding vector                                    |
| `POST /api/embeddings/similarity` | Rank sentences by cosine similarity to a query (in-memory) |
| `POST /api/embeddings/chunk`   | Split text into overlapping chunks + embed (preview only)  |
| `POST /api/embeddings/store`   | Chunk + embed + persist to Postgres (`document_chunks`)    |
| `POST /api/embeddings/upload`  | Upload a `.txt` file → chunk, embed, persist                |
| `POST /api/embeddings/search`  | pgvector `<=>` similarity search over stored chunks         |
| `POST /api/rag/ask`            | Full RAG: retrieve chunks, then answer via LLM using only that context |

Full request/response details, payloads, and verified examples for each: see
[docs/embeddings-flow.md](docs/embeddings-flow.md).

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
├── schemas/              # Pydantic request/response models (embedding.py, rag.py)
├── services/              # Business logic — OpenAI calls, chunking, pgvector storage/search, RAG
├── db/                    # Postgres connection (psycopg)
└── static/                # Browser test UI (one page, one section per endpoint)

documents/                 # Sample .txt files for seeding/uploading
sql/                       # Schema SQL
scripts/                   # One-off setup scripts (init_db.py, seed_documents.py)
docker-compose.yml         # pgvector Postgres container
```

## Docs

- [docs/architecture.md](docs/architecture.md) — layered structure, the two RAG paths, and a full request trace for `/api/rag/ask`
- [docs/embeddings-flow.md](docs/embeddings-flow.md) — step-by-step flow, run commands, and progress
- [docs/vector-storage.md](docs/vector-storage.md) — Postgres + pgvector setup (database, schema, script)
