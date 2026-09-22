import os

from dotenv import load_dotenv
from openai import OpenAI

from app.services.search_service import search_similar_chunks
from app.services.session_service import append_turn, create_session, get_history


load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

RAG_INSTRUCTIONS = (
    "You are a support assistant for Manakarto, a food delivery app. "
    "Answer using only the context provided below. "
    "If the context doesn't contain the answer, say you don't have that information — "
    "do not make anything up. "
    "You may also use earlier turns in this conversation to resolve references "
    "like \"it\" or \"that\", but never invent facts not present in the context."
)


def _sources(chunks):
    return [
        {
            "source": chunk["metadata"].get("source"),
            "similarity": chunk["similarity"],
        }
        for chunk in chunks
    ]


def generate_answer(question: str, top_k: int = 5):

    chunks = search_similar_chunks(question, top_k=top_k)

    context = "\n\n".join(
        f"[{chunk['metadata'].get('source', 'unknown')}] {chunk['content']}"
        for chunk in chunks
    )

    response = client.responses.create(
        model="gpt-5-mini",
        instructions=RAG_INSTRUCTIONS,
        input=f"Context:\n{context}\n\nQuestion: {question}",
    )

    return {
        "answer": response.output_text,
        "sources": _sources(chunks),
    }


def chat_with_session(message: str, session_id: str | None = None, top_k: int = 5):

    if session_id is None:
        session_id = create_session()

    history = get_history(session_id)

    chunks = search_similar_chunks(message, top_k=top_k)

    context = "\n\n".join(
        f"[{chunk['metadata'].get('source', 'unknown')}] {chunk['content']}"
        for chunk in chunks
    )

    messages = history + [{
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {message}",
    }]

    response = client.responses.create(
        model="gpt-5-mini",
        instructions=RAG_INSTRUCTIONS,
        input=messages,
    )

    # Store the plain message (not the context-stuffed version) so history
    # doesn't balloon with repeated context blocks on every turn.
    append_turn(session_id, "user", message)
    append_turn(session_id, "assistant", response.output_text)

    return {
        "session_id": session_id,
        "answer": response.output_text,
        "sources": _sources(chunks),
    }
