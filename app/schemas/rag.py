from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    top_k: int = 5
