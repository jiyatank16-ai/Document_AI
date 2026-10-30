import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "documind.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)

    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pdf_name TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pdf_name TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)


def save_document(pdf_name):
    if not pdf_name or not pdf_name.strip():
        raise ValueError("PDF name cannot be empty.")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO documents (pdf_name, uploaded_at)
            VALUES (?, ?)
            """,
            (pdf_name.strip(), timestamp),
        )


def save_chat(pdf_name, question, answer):
    pdf_name = pdf_name.strip() if pdf_name and pdf_name.strip() else "Unknown document"

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_history (
                pdf_name,
                question,
                answer,
                timestamp
            )
            VALUES (?, ?, ?, ?)
            """,
            (pdf_name, question.strip(), str(answer or "").strip(), timestamp),
        )


def get_chat_history(limit=100):
    limit = max(1, min(int(limit), 1000))

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, pdf_name, question, answer, timestamp
            FROM chat_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_documents(limit=100):
    limit = max(1, min(int(limit), 1000))

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, pdf_name, uploaded_at
            FROM documents
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def clear_chat_history():
    with get_connection() as conn:
        conn.execute("DELETE FROM chat_history")


def clear_document_history():
    with get_connection() as conn:
        conn.execute("DELETE FROM documents")


if __name__ == "__main__":
    init_db()
    print("DocuMind AI database initialized successfully.")
    print(f"Database location: {DB_PATH}")
