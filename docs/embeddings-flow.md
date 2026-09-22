# Embeddings — Step-by-Step Flow

## Setup (run once)

```
cd D:\Projects\AI_Engineer
venv\Scripts\activate
pip install -r requirements.txt
```

`.env` must contain:

```
OPENAI_API_KEY=...
HOST=127.0.0.1
PORT=8000
```

## Run the server

Host/port are read from `.env` (`app/main.py` has a `if __name__ == "__main__"` block using `uvicorn.run(...)`), so run it as a module:

```
cd D:\Projects\AI_Engineer
venv\Scripts\activate
python -m app.main
```

(`uvicorn app.main:app --reload` still works too, but then it uses uvicorn's own default host/port — `PORT` in `.env` only takes effect when run via `python -m app.main`.)

Server runs at `http://<HOST>:<PORT>` from `.env` (default `http://127.0.0.1:8000`).

---

## Step 1 — Basic embedding endpoint ✅

Convert one piece of text into a vector.

**Files**

- `app/schemas/embedding.py` → `EmbeddingRequest`
- `app/services/embedding_service.py` → `create_embedding(text)`
- `app/main.py` → `POST /api/embeddings`

**Flow**

```
text
  |
  v
client.embeddings.create(model="text-embedding-3-small", input=text)
  |
  v
1536-dim vector (list[float])
```

**Test**

Payload (paste directly into the web UI textarea, or into `/docs` → `Try it out` → Request body):

```json
{
  "text": "Chicken biryani costs 250 rupees"
}
```

curl equivalent:

```
curl -X POST http://127.0.0.1:8000/api/embeddings ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"Chicken biryani costs 250 rupees\"}"
```

Response:

```json
{
  "text": "Chicken biryani costs 250 rupees",
  "dimensions": 1536,
  "embedding": [-0.0108, -0.0235, 0.0742, "..."]
}
```

Verified live — real call to OpenAI, real 1536-dim vector back.

**Web UI**

A simple test page is served at `http://127.0.0.1:8000/` (no Postman/curl needed):

- `app/static/index.html` — textarea + button, calls `POST /api/embeddings` via `fetch`, shows dimensions + a preview of the vector
- `app/main.py` → `app.mount("/", StaticFiles(directory="app/static", html=True))`, mounted **after** the API routes so `/api/embeddings` still matches first

---

## Step 2 — Similarity search ✅

Compare a query against several candidate sentences, rank by cosine similarity.

**Files**

- `app/schemas/embedding.py` → `SimilarityRequest` (`query`, `sentences`)
- `app/services/similarity_service.py` → `create_embeddings(texts)` (batched, one API call for query + all sentences), `cosine_similarity(a, b)` (numpy dot / norms), `find_similar_sentences(query, sentences)` (embeds all, scores each sentence against the query, sorts descending)
- `app/main.py` → `POST /api/embeddings/similarity`

**Flow**

```
[query] + sentences
        |
        v
create_embeddings(...)   (1 batched OpenAI call)
        |
        v
query_embedding, [sentence_embeddings]
        |
        v
cosine_similarity(query_embedding, each sentence_embedding)
        |
        v
sorted results, highest similarity first
```

**Test**

Payload for `/docs` → `Try it out`:

```json
{
  "query": "How much does chicken biryani cost?",
  "sentences": [
    "Chicken biryani costs 250 rupees.",
    "The delivery partner is 10 minutes away.",
    "Veg meals are available for 180 rupees."
  ]
}
```

For the web UI form (separate fields, not raw JSON) — paste this into the **query** box:

```
How much does chicken biryani cost?
```

...and this into the **sentences** textarea (one sentence per line):

```
Chicken biryani costs 250 rupees.
The delivery partner is 10 minutes away.
Veg meals are available for 180 rupees.
```

curl equivalent:

```
curl -X POST http://127.0.0.1:8000/api/embeddings/similarity ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"How much does chicken biryani cost?\", \"sentences\": [\"Chicken biryani costs 250 rupees.\", \"The delivery partner is 10 minutes away.\", \"Veg meals are available for 180 rupees.\"]}"
```

Verified live:

```json
{
  "query": "How much does chicken biryani cost?",
  "results": [
    {"sentence": "Chicken biryani costs 250 rupees.", "similarity": 0.7856},
    {"sentence": "Veg meals are available for 180 rupees.", "similarity": 0.4388},
    {"sentence": "The delivery partner is 10 minutes away.", "similarity": 0.1088}
  ]
}
```

Ranking matches expectations — the biryani-price sentence wins, the unrelated delivery sentence loses.

**Web UI**

`app/static/index.html` now has a second section: a query field + a "one sentence per line" textarea, calling `POST /api/embeddings/similarity` and rendering results as ranked bars (similarity score as bar width). Same page as Step 1's form, both sections live at `http://127.0.0.1:8000/`.

Note: this and the `/api/embeddings` endpoint are `POST`-only — pasting the URL into the browser address bar sends a `GET` and returns `404`/`405`. Use the web UI, `curl`, Postman, or the auto-generated Swagger docs at `http://127.0.0.1:8000/docs` to actually call them.

---

## Step 3 — Chunking ✅

Split a long document into overlapping word-based chunks, embed each one.

**Files**

- `app/schemas/embedding.py` → `ChunkRequest` (`text`, `chunk_size=500`, `overlap=50`)
- `app/services/chunking_service.py` → `chunk_text(text, chunk_size, overlap)` — pure word-splitting, no OpenAI call
- `app/main.py` → `POST /api/embeddings/chunk` (reuses `create_embeddings` from `similarity_service.py` — one batched OpenAI call for all chunks)

**Flow**

```
text
  |
  v
chunk_text(...)              (word-based split, overlap between consecutive chunks)
  |
  v
[chunk_1, chunk_2, ...]
  |
  v
create_embeddings(chunks)    (1 batched OpenAI call)
  |
  v
[{chunk_id, text, dimensions, embedding}, ...]
```

**Guard added:** if `overlap >= chunk_size`, the loop's `start = end - overlap` never advances and the request would hang forever. The endpoint now returns `400 overlap must be smaller than chunk_size` instead of hanging — verified this returns immediately rather than blocking.

**Test**

Payload for `/docs` → `Try it out`:

```json
{
  "text": "Customers can cancel an order before the restaurant accepts it. Once the restaurant accepts the order, cancellation may not be possible. If the restaurant has started preparing the food, cancellation is normally not allowed. Refund eligibility depends on the cancellation stage and payment method.",
  "chunk_size": 20,
  "overlap": 5
}
```

For the web UI form — paste this into the **document** textarea:

```
Customers can cancel an order before the restaurant accepts it. Once the restaurant accepts the order, cancellation may not be possible. If the restaurant has started preparing the food, cancellation is normally not allowed. Refund eligibility depends on the cancellation stage and payment method.
```

...and set **Chunk size** = `20`, **Overlap** = `5`.

curl equivalent:

```
curl -X POST http://127.0.0.1:8000/api/embeddings/chunk ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"Customers can cancel an order before the restaurant accepts it. Once the restaurant accepts the order, cancellation may not be possible. If the restaurant has started preparing the food, cancellation is normally not allowed. Refund eligibility depends on the cancellation stage and payment method.\", \"chunk_size\": 20, \"overlap\": 5}"
```

Verified live — 3 chunks, each one overlapping the last by 5 words (e.g. "order, cancellation may not be" appears at the end of chunk 0 and the start of chunk 1).

**Web UI**

`app/static/index.html` has a third section: a textarea for the document + number inputs for chunk size / overlap, calling `POST /api/embeddings/chunk` and listing each chunk with its dimension count. All three tools (embed, similarity, chunk) now live on one page at `http://127.0.0.1:8000/`.

---

## Step 4 — Store vectors (pgvector) ✅

Persist chunk embeddings in Postgres instead of only returning them in the response.

Full infra details: [docs/vector-storage.md](vector-storage.md).

**Infra**

- Native local Postgres 18 has no `pgvector` (would need MSVC build tools to compile) — switched to the official `pgvector/pgvector` Docker image instead (`docker compose up -d`)
- `docker-compose.yml` — pgvector Postgres container on port `5433` (not 5432, avoids clashing with native Postgres), database `ai_engineer_embeddings`, data in named volume `ai_engineer_pgvector_data`
- `app/db/database.py` → `get_connection()` (psycopg, reads `DATABASE_URL`)
- `sql/02_schema.sql` + `scripts/init_db.py` — applies `CREATE EXTENSION vector` + `document_chunks` table automatically

**Endpoint**

- `app/schemas/embedding.py` → `StoreChunksRequest` (`text`, `chunk_size`, `overlap`, `document_id`, `source`)
- `app/services/vector_store_service.py` → `store_chunks(chunks, embeddings, document_id, source)` — inserts each chunk as a row, embedding passed as a `[v1,v2,...]` string cast to `::vector`, metadata via psycopg's `Jsonb`
- `app/main.py` → `POST /api/embeddings/store` — chunks text, embeds (batched), stores in `document_chunks`, returns the inserted row IDs
- Kept separate from `POST /api/embeddings/chunk` (which stays a pure preview with no side effects) — same overlap guard applied

**Flow**

```
text
  |
  v
chunk_text(...)
  |
  v
create_embeddings(chunks)     (1 batched OpenAI call)
  |
  v
store_chunks(...)             (INSERT ... VALUES (%s, %s, %s::vector, %s) per chunk)
  |
  v
document_chunks table (Postgres + pgvector)
```

**Test**

Payload for `/docs` → `Try it out`:

```json
{
  "text": "Customers can cancel an order before the restaurant accepts it. Once the restaurant accepts the order, cancellation may not be possible.",
  "chunk_size": 15,
  "overlap": 3,
  "document_id": 1,
  "source": "cancellation_policy.txt"
}
```

For the web UI form — paste this into the **document** textarea:

```
Customers can cancel an order before the restaurant accepts it. Once the restaurant accepts the order, cancellation may not be possible.
```

...set **Chunk size** = `15`, **Overlap** = `3`, and paste this into the **source label** field:

```
cancellation_policy.txt
```

Verified live — stored 3 rows, confirmed via `docker exec ai_engineer_pgvector psql ... SELECT id, document_id, vector_dims(embedding), metadata FROM document_chunks`: correct `document_id`, `1536`-dim vectors, `{"source": "cancellation_policy.txt"}` metadata.

**Web UI**

`app/static/index.html` has a fourth section — "Store in Postgres" — same chunk-size/overlap controls as the chunk preview, plus an optional source label, calling `POST /api/embeddings/store` and showing the stored row count + IDs.

---

## Sample data — 5 seeded documents

Real files, not inline strings — visible in the project at [`documents/`](../documents):

| file                                                 | document_id | covers                                                                 |
|-------------------------------------------------------|-------------|-------------------------------------------------------------------------|
| [`documents/menu.txt`](../documents/menu.txt)                             | 1–5 (alphabetical — see below) | Prices (biryani, mutton, naan, drinks), combos, spice levels, vegan options |
| [`documents/delivery_policy.txt`](../documents/delivery_policy.txt)       | ″ | Delivery time, charges, range limit, rain delays, delivery instructions, contactless |
| [`documents/cancellation_policy.txt`](../documents/cancellation_policy.txt) | ″ | Cancel-before-acceptance rule, auto-cancel + refund if restaurant can't fulfil, repeated-cancellation restriction, post-acceptance support escalation |
| [`documents/refund_policy.txt`](../documents/refund_policy.txt)           | ″ | Refund timing by payment method, wallet vs. bank refund, damaged/missing/incorrect order refunds, refund status tracking |
| [`documents/support_hours.txt`](../documents/support_hours.txt)           | ″ | Restaurant hours, chat/phone/email support hours, holiday hours, supervisor escalation |

[`scripts/seed_documents.py`](../scripts/seed_documents.py) globs `documents/*.txt`,
assigns `document_id` in alphabetical filename order (so `cancellation_policy.txt` is
`1`, not `menu.txt`), and stores each file as one row (no chunking) with
`source = filename`.

Run:

```
cd D:\Projects\AI_Engineer
venv\Scripts\activate
python scripts/seed_documents.py
```

Re-running it inserts new rows each time (it doesn't delete old ones first) — clear the
table first if you want a fresh set: `docker exec ai_engineer_pgvector psql -U postgres -d ai_engineer_embeddings -c "DELETE FROM document_chunks;"`

---

## Uploading your own files ✅

`POST /api/embeddings/upload` — a real ingestion endpoint: upload a `.txt` file, it gets
chunked, embedded, and stored, with `source` set to the uploaded filename.

**Files**

- `app/main.py` → `POST /api/embeddings/upload` (multipart form: `file`, `chunk_size`, `overlap`, `document_id`) — needs `python-multipart` (added to `requirements.txt`)
- Reuses `chunk_text`, `create_embeddings`, `store_chunks` — no new service needed
- Rejects non-UTF-8 files (`400`, e.g. PDFs/images) and empty files, same `overlap >= chunk_size` guard as the other endpoints

**Test**

```
curl -X POST http://127.0.0.1:8000/api/embeddings/upload ^
  -F "file=@documents/menu.txt" ^
  -F "chunk_size=30" ^
  -F "overlap=5"
```

Verified live — uploading `documents/menu.txt` produced 4 chunks (ids 27–30), each with
`metadata: {"source": "menu.txt"}` confirmed via `psql`. The `overlap >= chunk_size` guard
also verified on this endpoint (`400`, no hang).

**Web UI**

`app/static/index.html` has a section between "Store in Postgres" and "Search Postgres" —
a native file picker (`.txt` only) + chunk-size/overlap fields, posting as `FormData`
(not JSON, since it's a file upload) to `/api/embeddings/upload`.

---

## Step 5 — Vector similarity search in Postgres ✅

Search stored chunks directly in Postgres using pgvector's `<=>` cosine-distance operator,
instead of the in-memory numpy approach from Step 2. This is what real retrieval looks
like at scale — Postgres does the nearest-neighbor search, not Python.

**Files**

- `app/schemas/embedding.py` → `SearchRequest` (`query`, `top_k=5`)
- `app/services/search_service.py` → `search_similar_chunks(query, top_k)` — embeds the query, runs `SELECT ... ORDER BY embedding <=> %s::vector LIMIT %s`, returns `distance` and `similarity = 1 - distance`
- `app/main.py` → `POST /api/embeddings/search`

**Flow**

```
query
  |
  v
create_embedding(query)        (1 OpenAI call)
  |
  v
SELECT id, document_id, content, metadata, embedding <=> %s::vector AS distance
FROM document_chunks
ORDER BY embedding <=> %s::vector
LIMIT %s
  |
  v
ranked results (Postgres does the nearest-neighbor search, not Python)
```

No index (ivfflat/hnsw) yet — with only 5 rows this is an exact sequential scan, which is
fine. An index becomes worth adding once the table has thousands+ of rows.

**Test**

Payload for `/docs` → `Try it out`:

```json
{
  "query": "Can I get a refund if I cancel my order after the restaurant accepts it?",
  "top_k": 5
}
```

For the web UI form — paste this into the **query** box and set **Top K** = `5`:

```
Can I get a refund if I cancel my order after the restaurant accepts it?
```

Verified live against the 5 seeded documents:

```json
{
  "query": "Can I get a refund if I cancel my order after the restaurant accepts it?",
  "results": [
    {"document_id": 3, "metadata": {"source": "cancellation_policy.txt"}, "similarity": 0.7290},
    {"document_id": 4, "metadata": {"source": "refund_policy.txt"},       "similarity": 0.5654},
    {"document_id": 5, "metadata": {"source": "support_hours.txt"},       "similarity": 0.3465},
    {"document_id": 2, "metadata": {"source": "delivery_policy.txt"},     "similarity": 0.3436},
    {"document_id": 1, "metadata": {"source": "menu.txt"},                "similarity": 0.1486}
  ]
}
```

Cancellation + refund policies correctly rank #1/#2; unrelated docs trail well behind.
Cross-checked with a second query, `"Is delivery free and how far do you deliver?"` →
`delivery_policy.txt` scored 0.5280, next closest (`refund_policy.txt`) only 0.2697.

**Web UI**

`app/static/index.html` has a fifth section — "Search Postgres" — query box + top-K,
calling `POST /api/embeddings/search` and rendering results as ranked bars with the
matched chunk's source label and content.

---

## Step 6 — Full RAG (retrieval + LLM answer) ✅

Ties everything together: retrieve relevant chunks (Step 5), then hand them to an LLM as
context so it answers using only that context — the actual point of the whole pipeline.

**Files**

- `app/schemas/rag.py` → `AskRequest` (`question`, `top_k=5`)
- `app/services/rag_service.py` → `generate_answer(question, top_k)` — calls `search_similar_chunks` (Step 5), builds a `[source] content` context block from the results, calls `client.responses.create(model="gpt-5-mini", instructions=..., input=...)` with instructions to answer only from context and say so if it can't, returns `{answer, sources}`
- `app/main.py` → `POST /api/rag/ask`

**Flow**

```
question
  |
  v
search_similar_chunks(question, top_k)     (Step 5 — pgvector <=> search)
  |
  v
context = "[source] content" for each retrieved chunk
  |
  v
client.responses.create(instructions="answer only from context", input=context + question)
  |
  v
{ answer, sources: [{source, similarity}, ...] }
```

This is the same two-embedding-paths diagram from the very start of the roadmap —
documents embedded once at ingestion time (Steps 3/4), the question embedded at query
time (Step 5) — now closed by handing the retrieved text to an LLM instead of returning
raw chunks.

**Test**

Payload for `/docs` → `Try it out`:

```json
{
  "question": "Can I cancel my order after the restaurant accepts it, and will I get a refund?",
  "top_k": 3
}
```

For the web UI form — paste this into the **question** box:

```
Can I cancel my order after the restaurant accepts it, and will I get a refund?
```

Verified live against the 5 seeded documents:

```
ANSWER:
Yes. If you cancel after the restaurant accepts and no payment was collected in advance,
you can get a refund as wallet credit, processed within 5-7 business days. Cash-on-delivery
orders cancelled after acceptance are not eligible for refunds. You can check progress in
the Orders tab under Refund Status.

SOURCES: refund_policy.txt (sim 0.53, 0.48, 0.48)
```

Also verified the "don't make it up" instruction holds for an out-of-scope question —
`"Who is the CEO of Manakarto?"` → *"I don't have that information in the provided
context..."* instead of a hallucinated answer.

**Web UI**

`app/static/index.html` has a sixth section — "Ask (RAG)" — a question box + top-K,
calling `POST /api/rag/ask` and showing the generated answer plus a sources card listing
each retrieved chunk's source file and similarity score.

---

## Progress

- [x] Step 1 — text → embedding endpoint
- [x] Step 2 — cosine similarity ranking
- [x] Step 3 — document chunking
- [x] Step 4 — store vectors (pgvector)
- [x] Step 5 — vector similarity search in Postgres
- [x] Step 6 — full RAG (retrieval + LLM answer)
