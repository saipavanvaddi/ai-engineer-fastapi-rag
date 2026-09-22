from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.schemas.embedding import EmbeddingRequest
from app.services.embedding_service import create_embedding


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


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
