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

## Progress

- [x] Step 1 — text → embedding endpoint
- [x] Step 2 — cosine similarity ranking
- [x] Step 3 — document chunking
- [ ] Step 4 — store vectors (pgvector)
- [ ] Step 5 — vector similarity search in Postgres
- [ ] Step 6 — full RAG (retrieval + LLM answer)
