import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.schemas.embedding import EmbeddingRequest
from app.services.embedding_service import create_embedding


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


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", 5000)),
        reload=True,
    )
