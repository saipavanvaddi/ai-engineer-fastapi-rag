import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.schemas.embedding import ChunkRequest, EmbeddingRequest, SimilarityRequest
from app.services.chunking_service import chunk_text
from app.services.embedding_service import create_embedding
from app.services.similarity_service import create_embeddings, find_similar_sentences


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


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", 5000)),
        reload=True,
    )
