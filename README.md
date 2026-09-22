# AI_Engineer

FastAPI backend for the Embeddings → Vector DB → RAG learning roadmap
(Day 144 onward — Manakarto-style examples used for learning).

## Setup

```
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Requires `OPENAI_API_KEY` in `.env`.

## Structure

```
app/
├── main.py              # FastAPI app + route registration
├── schemas/              # Pydantic request/response models
└── services/              # Business logic (OpenAI calls, etc.)
```

## Docs

- [docs/embeddings-flow.md](docs/embeddings-flow.md) — step-by-step flow, run commands, and progress
