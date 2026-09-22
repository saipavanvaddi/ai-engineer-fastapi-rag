# Architecture

How the pieces fit together, and exactly what happens on a single RAG request.

## Layered structure

```
┌─────────────────────────────────────────────────────────────┐
│  Browser UI (app/static/index.html)                          │
│  7 sections, one per endpoint — fetch() calls, no framework  │
└───────────────────────────┬───────────────────────────────────┘
                             │ HTTP (JSON / multipart)
┌───────────────────────────▼───────────────────────────────────┐
│  FastAPI app (app/main.py)                                    │
│  Route registration only — each endpoint validates via a      │
│  Pydantic schema, then delegates to a service function         │
└──────┬──────────────┬──────────────┬──────────────┬────────────┘
       │              │              │              │
┌──────▼─────┐ ┌──────▼──────┐ ┌─────▼──────┐ ┌──────▼──────┐
│ schemas/    │ │ services/   │ │ db/         │ │ static/      │
│ embedding.py│ │ *.py        │ │ database.py │ │ index.html   │
│ rag.py      │ │ (business   │ │ (psycopg    │ │ (test UI)    │
│ (Pydantic   │ │  logic)     │ │  connection)│ │              │
│  models)    │ │             │ │             │ │              │
└─────────────┘ └──────┬──────┘ └──────┬──────┘ └─────────────┘
                        │               │
              ┌─────────▼───────┐  ┌────▼─────────────────┐
              │  OpenAI API      │  │  Postgres + pgvector  │
              │  text-embedding- │  │  (Docker container,   │
              │  3-small,        │  │  port 5433)            │
              │  gpt-5-mini      │  │  document_chunks table│
              └──────────────────┘  └────────────────────────┘
```

## Layers in detail

Six layers, top to bottom. Each one only talks to the layer directly below it —
`main.py` never touches the database directly, services never touch HTTP, etc.

| # | Layer | Responsibility | Files |
|---|---|---|---|
| 1 | **Presentation** | Renders forms, calls `fetch()`, displays results | `app/static/index.html` |
| 2 | **Routing** | Declares routes, wires request → schema → service → response | `app/main.py` |
| 3 | **Validation** | Defines request shapes, rejects bad input before any logic runs | `app/schemas/embedding.py`, `app/schemas/rag.py` |
| 4 | **Business logic** | Chunking, embedding calls, similarity scoring, RAG orchestration | `app/services/chunking_service.py`, `embedding_service.py`, `similarity_service.py`, `vector_store_service.py`, `search_service.py`, `rag_service.py` |
| 5 | **Data access** | Owns the one place a Postgres connection is opened | `app/db/database.py` |
| 6 | **External services** | Things outside this codebase that layer 4 calls out to | OpenAI API (embeddings + chat), Postgres + pgvector (Docker) |

**Why it's split this way:** `main.py` stays thin (route + wiring only, no business logic
inline) so every endpoint's actual behavior lives in one testable function in `services/`.
`db/database.py` is the only file that imports `psycopg` — if the driver or connection
string handling ever changes, it changes in one place. Schemas are separate from services
so FastAPI can validate and reject bad requests (`422`) before any OpenAI or Postgres call
is made — no wasted API calls on malformed input.

## The two paths (the core RAG shape)

Documents get embedded once at ingestion time, questions get embedded at query time,
and both paths meet at the vector comparison:

```
                    DOCUMENT INGESTION (write path)
documents/*.txt  or  uploaded .txt file
        │
        ▼
chunk_text()                         [chunking_service.py]
        │
        ▼
create_embeddings()  ── OpenAI ──▶   1536-dim vector per chunk
        │
        ▼
store_chunks()                       [vector_store_service.py]
        │
        ▼
document_chunks table (Postgres)     content, embedding, metadata

═══════════════════════════════════════════════════════════════

                    QUERY (read path)
question
        │
        ▼
create_embedding()   ── OpenAI ──▶   1536-dim vector for the question
        │
        ▼
search_similar_chunks()              [search_service.py]
   SELECT ... ORDER BY embedding <=> %s::vector LIMIT %s
        │
        ▼
ranked chunks (pgvector does the nearest-neighbor search)
        │
        ▼
generate_answer()                    [rag_service.py]
   builds "[source] content" context, sends to gpt-5-mini
   with instructions: "answer only from context"
        │
        ▼
{ answer, sources }
```

## Endpoint map (which service each one calls)

| Endpoint | Service function(s) | Touches DB? | Touches OpenAI? |
|---|---|---|---|
| `POST /api/embeddings` | `create_embedding` | no | embed |
| `POST /api/embeddings/similarity` | `create_embeddings`, `cosine_similarity` (numpy) | no | embed |
| `POST /api/embeddings/chunk` | `chunk_text`, `create_embeddings` | no | embed |
| `POST /api/embeddings/store` | `chunk_text`, `create_embeddings`, `store_chunks` | write | embed |
| `POST /api/embeddings/upload` | same as `/store`, source = filename | write | embed |
| `POST /api/embeddings/search` | `search_similar_chunks` | read | embed |
| `POST /api/rag/ask` | `search_similar_chunks` → `generate_answer` | read | embed + chat |
| `POST /api/rag/chat` | `search_similar_chunks` → `chat_with_session` (reads/writes `session_service`'s in-memory store) | read | embed + chat |

Steps 1–2 (`/similarity`) do cosine similarity **in Python** with numpy — fine for a
handful of sentences held in memory, the "teach the concept" version. Step 5 (`/search`)
does it **in Postgres** with pgvector's `<=>` operator — what actually scales, since the
database indexes and searches the vectors directly instead of pulling everything into
Python first.

`/api/rag/ask` is stateless (one question, one answer, no memory). `/api/rag/chat` adds a
`session_id`-keyed conversation history (in-memory, not Postgres — resets on restart) so
follow-up questions can use pronouns like "it" or "the veg one" and still resolve
correctly against the prior turn.

---

## RAG request trace — from user input to rendered response

Every hop for `POST /api/rag/ask`, in order:

```
┌──────────────────────────────────────────────────────────────────────┐
│ 1. BROWSER — app/static/index.html                                    │
│    User types into #ask-question, sets #ask-top-k, clicks "Ask"       │
│    askForm submit handler:                                            │
│      fetch("/api/rag/ask", { method: "POST",                          │
│             body: JSON.stringify({ question, top_k }) })              │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │ HTTP POST, JSON body
┌───────────────────────────────▼─────────────────────────────────────┐
│ 2. FASTAPI ROUTING — app/main.py                                     │
│    @app.post("/api/rag/ask")                                         │
│    def ask_endpoint(request: AskRequest):                            │
│    Body is parsed + validated against AskRequest                      │
│    (app/schemas/rag.py — question: str, top_k: int = 5).              │
│    Bad/missing fields → FastAPI auto-returns 422, never reaches here. │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │ request.question, request.top_k
┌───────────────────────────────▼─────────────────────────────────────┐
│ 3. RAG SERVICE — app/services/rag_service.py                         │
│    generate_answer(question, top_k) — orchestrates steps 4–7         │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │
┌───────────────────────────────▼─────────────────────────────────────┐
│ 4. RETRIEVAL — app/services/search_service.py                        │
│    search_similar_chunks(question, top_k)                            │
│      a) create_embedding(question)  →  OpenAI API call #1            │
│         (embedding_service.py, model=text-embedding-3-small)         │
│         returns a 1536-float vector for the question                 │
│      b) formats it as a pgvector literal: "[0.012,-0.03,...]"        │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │ query_literal
┌───────────────────────────────▼─────────────────────────────────────┐
│ 5. DATABASE — app/db/database.py → Docker Postgres (port 5433)       │
│    get_connection() opens a psycopg connection to the                │
│    ai_engineer_pgvector container                                    │
│                                                                        │
│    SELECT id, document_id, content, metadata,                        │
│           embedding <=> %s::vector AS distance                       │
│    FROM document_chunks                                              │
│    ORDER BY embedding <=> %s::vector                                 │
│    LIMIT %s                                                          │
│                                                                        │
│    pgvector computes cosine distance between the question's vector   │
│    and every stored chunk's embedding column, sorts, returns top_k.  │
│    Rows come back as (chunk_id, document_id, content, metadata,      │
│    distance) — converted to similarity = 1 - distance.               │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │ ranked list of chunk dicts
┌───────────────────────────────▼─────────────────────────────────────┐
│ 6. CONTEXT BUILDING — back in rag_service.py                         │
│    context = "\n\n".join(f"[{source}] {content}" for each chunk)     │
│    e.g. "[refund_policy.txt] Refunds for prepaid orders are..."      │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │ context string + original question
┌───────────────────────────────▼─────────────────────────────────────┐
│ 7. GENERATION — OpenAI API call #2                                   │
│    client.responses.create(                                          │
│        model="gpt-5-mini",                                           │
│        instructions="answer using only the context... if it's       │
│                       not there, say you don't have that info",      │
│        input=f"Context:\n{context}\n\nQuestion: {question}",         │
│    )                                                                  │
│    LLM reads the retrieved chunks (not the whole document_chunks     │
│    table — only the top_k rows from step 5) and writes an answer.    │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │ response.output_text
┌───────────────────────────────▼─────────────────────────────────────┐
│ 8. RESPONSE ASSEMBLY                                                  │
│    rag_service.py returns { answer, sources: [{source, similarity}] }│
│    main.py wraps it: { question, answer, sources } → FastAPI         │
│    serializes to JSON, sends 200 OK back to the browser.             │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │ JSON response
┌───────────────────────────────▼─────────────────────────────────────┐
│ 9. BROWSER RENDERS — index.html                                      │
│    askForm handler's .then/await: builds the answer card + a         │
│    sources card (file name + similarity score per source), injects   │
│    into #ask-result. Button re-enabled.                              │
└────────────────────────────────────────────────────────────────────┘
```

**Key things worth noticing:**

- **Two separate OpenAI calls** happen per request — one to embed the question (step 4a),
  one to generate the answer (step 7). Different models (`text-embedding-3-small` vs
  `gpt-5-mini`) doing different jobs.
- **The LLM never sees the whole database** — only the `top_k` chunks pgvector already
  ranked as most relevant. This is what keeps RAG cheap and accurate instead of stuffing
  every document into every prompt.
- **The `<=>` search happens inside Postgres**, not in Python — the vector comparison is
  a single SQL query, not a loop over rows in `rag_service.py`.
