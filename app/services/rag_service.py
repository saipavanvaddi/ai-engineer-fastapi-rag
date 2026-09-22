import os

from dotenv import load_dotenv
from openai import OpenAI

from app.services.search_service import search_similar_chunks


load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def generate_answer(question: str, top_k: int = 5):

    chunks = search_similar_chunks(question, top_k=top_k)

    context = "\n\n".join(
        f"[{chunk['metadata'].get('source', 'unknown')}] {chunk['content']}"
        for chunk in chunks
    )

    response = client.responses.create(
        model="gpt-5-mini",
        instructions=(
            "You are a support assistant for Manakarto, a food delivery app. "
            "Answer the question using only the context provided below. "
            "If the context doesn't contain the answer, say you don't have that information — "
            "do not make anything up."
        ),
        input=f"Context:\n{context}\n\nQuestion: {question}",
    )

    return {
        "answer": response.output_text,
        "sources": [
            {
                "source": chunk["metadata"].get("source"),
                "similarity": chunk["similarity"],
            }
            for chunk in chunks
        ],
    }
