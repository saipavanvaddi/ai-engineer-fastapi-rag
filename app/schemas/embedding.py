from pydantic import BaseModel


class EmbeddingRequest(BaseModel):
    text: str


class SimilarityRequest(BaseModel):
    query: str
    sentences: list[str]
