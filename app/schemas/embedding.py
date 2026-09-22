from pydantic import BaseModel


class EmbeddingRequest(BaseModel):
    text: str


class SimilarityRequest(BaseModel):
    query: str
    sentences: list[str]


class ChunkRequest(BaseModel):
    text: str
    chunk_size: int = 500
    overlap: int = 50


class StoreChunksRequest(BaseModel):
    text: str
    chunk_size: int = 500
    overlap: int = 50
    document_id: int | None = None
    source: str | None = None
