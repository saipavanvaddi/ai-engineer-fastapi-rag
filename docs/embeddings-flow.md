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

## Step 3 — Chunking ⬜

Split a long document into overlapping chunks, embed each one.

**Plan**

- `app/schemas/embedding.py` → add `ChunkRequest` (`text`, `chunk_size`, `overlap`)
- `app/services/chunking_service.py` → `chunk_text(text, chunk_size, overlap)`
- `app/main.py` → `POST /api/embeddings/chunk` (reuses batch embedding from Step 2)

---

## Progress

- [x] Step 1 — text → embedding endpoint
- [x] Step 2 — cosine similarity ranking
- [ ] Step 3 — document chunking
- [ ] Step 4 — store vectors (pgvector)
- [ ] Step 5 — vector similarity search in Postgres
- [ ] Step 6 — full RAG (retrieval + LLM answer)
