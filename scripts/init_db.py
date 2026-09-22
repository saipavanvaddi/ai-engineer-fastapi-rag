"""
Applies sql/02_schema.sql (pgvector extension + document_chunks table)
against DATABASE_URL from .env.

Run after creating the database manually (see sql/01_create_database.sql):

    python scripts/init_db.py
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


load_dotenv()

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "sql" / "02_schema.sql"


def main():

    schema_sql = SCHEMA_FILE.read_text()

    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()

    print(f"Applied {SCHEMA_FILE.name} — pgvector extension + document_chunks table ready.")


if __name__ == "__main__":
    main()
