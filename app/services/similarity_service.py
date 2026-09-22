import os

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def create_embeddings(texts: list[str]):

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )

    return [item.embedding for item in response.data]


def cosine_similarity(
    vector_a: list[float],
    vector_b: list[float],
):

    a = np.array(vector_a)
    b = np.array(vector_b)

    return float(
        np.dot(a, b)
        / (np.linalg.norm(a) * np.linalg.norm(b))
    )


def find_similar_sentences(
    query: str,
    sentences: list[str],
):

    texts = [query] + sentences

    embeddings = create_embeddings(texts)

    query_embedding = embeddings[0]

    results = []

    for sentence, embedding in zip(
        sentences,
        embeddings[1:],
    ):

        similarity = cosine_similarity(
            query_embedding,
            embedding,
        )

        results.append({
            "sentence": sentence,
            "similarity": similarity,
        })

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True,
    )

    return results
