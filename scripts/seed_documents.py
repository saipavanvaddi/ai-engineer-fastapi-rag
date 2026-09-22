"""
Seeds the 5 sample Manakarto documents from documents/*.txt into document_chunks,
for testing Step 5 (vector similarity search). Each file is stored as one row
(no chunking), with document_id assigned by filename order and source = filename.

    python scripts/seed_documents.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.similarity_service import create_embeddings
from app.services.vector_store_service import store_chunks


DOCUMENTS_DIR = Path(__file__).resolve().parent.parent / "documents"


def main():

    files = sorted(DOCUMENTS_DIR.glob("*.txt"))

    if not files:
        print(f"No .txt files found in {DOCUMENTS_DIR}")
        return

    texts = [f.read_text().strip() for f in files]
    embeddings = create_embeddings(texts)

    for document_id, (file, content, embedding) in enumerate(
        zip(files, texts, embeddings), start=1
    ):
        stored_ids = store_chunks(
            [content],
            [embedding],
            document_id=document_id,
            source=file.name,
        )
        print(f"document_id={document_id} source={file.name} -> chunk id {stored_ids[0]}")


if __name__ == "__main__":
    main()
