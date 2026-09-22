from app.db.database import get_connection
from app.services.embedding_service import create_embedding


def search_similar_chunks(query: str, top_k: int = 5):

    query_embedding = create_embedding(query)
    query_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, document_id, content, metadata,
                       embedding <=> %s::vector AS distance
                FROM document_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_literal, query_literal, top_k),
            )
            rows = cur.fetchall()

    return [
        {
            "chunk_id": row[0],
            "document_id": row[1],
            "content": row[2],
            "metadata": row[3],
            "distance": row[4],
            "similarity": 1 - row[4],
        }
        for row in rows
    ]
