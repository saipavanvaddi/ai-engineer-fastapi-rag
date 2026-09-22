from psycopg.types.json import Jsonb

from app.db.database import get_connection


def store_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    document_id: int | None = None,
    source: str | None = None,
):

    metadata = Jsonb({"source": source} if source else {})

    stored_ids = []

    with get_connection() as conn:
        with conn.cursor() as cur:

            for chunk, embedding in zip(chunks, embeddings):

                embedding_literal = "[" + ",".join(str(v) for v in embedding) + "]"

                cur.execute(
                    """
                    INSERT INTO document_chunks (document_id, content, embedding, metadata)
                    VALUES (%s, %s, %s::vector, %s)
                    RETURNING id
                    """,
                    (document_id, chunk, embedding_literal, metadata),
                )

                stored_ids.append(cur.fetchone()[0])

        conn.commit()

    return stored_ids
