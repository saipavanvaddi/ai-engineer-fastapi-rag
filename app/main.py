import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from app.schemas.embedding import (
    ChunkRequest,
    EmbeddingRequest,
    SearchRequest,
    SimilarityRequest,
    StoreChunksRequest,
)
from app.services.chunking_service import chunk_text
from app.services.embedding_service import create_embedding
from app.services.search_service import search_similar_chunks
from app.services.similarity_service import create_embeddings, find_similar_sentences
from app.services.vector_store_service import store_chunks


load_dotenv()

app = FastAPI()


@app.post("/api/embeddings")
def create_text_embedding(
    request: EmbeddingRequest,
):

    embedding = create_embedding(request.text)

    return {
        "text": request.text,
        "dimensions": len(embedding),
        "embedding": embedding,
    }


@app.post("/api/embeddings/similarity")
def embedding_similarity(
    request: SimilarityRequest,
):

    results = find_similar_sentences(
        request.query,
        request.sentences,
    )

    return {
        "query": request.query,
        "results": results,
    }


@app.post("/api/embeddings/chunk")
def chunk_and_embed(request: ChunkRequest):

    if request.overlap >= request.chunk_size:
        raise HTTPException(
            status_code=400,
            detail="overlap must be smaller than chunk_size",
        )

    chunks = chunk_text(
        text=request.text,
        chunk_size=request.chunk_size,
        overlap=request.overlap,
    )

    embeddings = create_embeddings(chunks)

    results = []

    for index, (chunk, embedding) in enumerate(
        zip(chunks, embeddings)
    ):

        results.append({
            "chunk_id": index,
            "text": chunk,
            "dimensions": len(embedding),
            "embedding": embedding,
        })

    return {
        "total_chunks": len(results),
        "chunks": results,
    }


@app.post("/api/embeddings/store")
def store_chunks_endpoint(request: StoreChunksRequest):

    if request.overlap >= request.chunk_size:
        raise HTTPException(
            status_code=400,
            detail="overlap must be smaller than chunk_size",
        )

    chunks = chunk_text(
        text=request.text,
        chunk_size=request.chunk_size,
        overlap=request.overlap,
    )

    embeddings = create_embeddings(chunks)

    stored_ids = store_chunks(
        chunks,
        embeddings,
        document_id=request.document_id,
        source=request.source,
    )

    return {
        "total_stored": len(stored_ids),
        "chunk_ids": stored_ids,
    }


@app.post("/api/embeddings/upload")
async def upload_and_store(
    file: UploadFile = File(...),
    chunk_size: int = Form(500),
    overlap: int = Form(50),
    document_id: int | None = Form(None),
):

    if overlap >= chunk_size:
        raise HTTPException(
            status_code=400,
            detail="overlap must be smaller than chunk_size",
        )

    raw = await file.read()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="file must be plain text (utf-8) — PDFs/images aren't supported yet",
        )

    if not text.strip():
        raise HTTPException(status_code=400, detail="file is empty")

    chunks = chunk_text(
        text=text,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    embeddings = create_embeddings(chunks)

    stored_ids = store_chunks(
        chunks,
        embeddings,
        document_id=document_id,
        source=file.filename,
    )

    return {
        "source": file.filename,
        "total_stored": len(stored_ids),
        "chunk_ids": stored_ids,
    }


@app.post("/api/embeddings/search")
def search_chunks_endpoint(request: SearchRequest):

    results = search_similar_chunks(
        request.query,
        top_k=request.top_k,
    )

    return {
        "query": request.query,
        "results": results,
    }


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", 5000)),
        reload=True,
    )
