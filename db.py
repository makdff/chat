import sqlite3
import os
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chats.db")

def get_database_url() -> Optional[str]:
    """Return a Postgres connection URL from env vars or Streamlit secrets."""
    database_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    try:
        import streamlit as st
    except ImportError:
        return None

    try:
        return st.secrets.get("SUPABASE_DB_URL") or st.secrets.get("DATABASE_URL")
    except Exception:
        return None

def using_postgres() -> bool:
    return bool(get_database_url())

def get_sqlite_connection():
    conn = sqlite3.connect(DB_PATH)
    # Enable foreign keys support in SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def get_postgres_connection():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        raise ImportError("Please install psycopg to use Supabase/Postgres: `pip install psycopg[binary]`")

    return psycopg.connect(get_database_url(), row_factory=dict_row)

@contextmanager
def get_connection():
    conn = get_postgres_connection() if using_postgres() else get_sqlite_connection()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database and create tables if they do not exist."""
    with get_connection() as conn:
        if using_postgres():
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model_name TEXT,
                    provider TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()
            return

        # Create chats table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create messages table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model_name TEXT,
                provider TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
        """)
        
        # Create settings table (for storing API keys, selected model, etc.)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()

# --- Chat CRUD Operations ---

def create_chat(title: str = "New Chat") -> int:
    """Create a new chat session and return its ID."""
    with get_connection() as conn:
        placeholder = "%s" if using_postgres() else "?"
        cursor = conn.cursor()
        if using_postgres():
            cursor.execute(f"INSERT INTO chats (title) VALUES ({placeholder}) RETURNING id", (title,))
            chat_id = cursor.fetchone()["id"]
        else:
            cursor.execute(f"INSERT INTO chats (title) VALUES ({placeholder})", (title,))
            chat_id = cursor.lastrowid
        conn.commit()
        return chat_id

def get_chats() -> List[Dict[str, Any]]:
    """Retrieve all chats sorted by creation time (newest first)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, created_at FROM chats ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]

def rename_chat(chat_id: int, new_title: str) -> None:
    """Rename an existing chat session."""
    with get_connection() as conn:
        placeholder = "%s" if using_postgres() else "?"
        conn.execute(f"UPDATE chats SET title = {placeholder} WHERE id = {placeholder}", (new_title, chat_id))
        conn.commit()

def delete_chat(chat_id: int) -> None:
    """Delete a chat session (messages will be deleted cascadingly)."""
    with get_connection() as conn:
        placeholder = "%s" if using_postgres() else "?"
        conn.execute(f"DELETE FROM chats WHERE id = {placeholder}", (chat_id,))
        conn.commit()

# --- Message CRUD Operations ---

def get_chat_messages(chat_id: int) -> List[Dict[str, Any]]:
    """Retrieve all messages for a given chat ID."""
    with get_connection() as conn:
        placeholder = "%s" if using_postgres() else "?"
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT role, content, model_name, provider, created_at FROM messages WHERE chat_id = {placeholder} ORDER BY id ASC",
            (chat_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def add_message(chat_id: int, role: str, content: str, model_name: Optional[str] = None, provider: Optional[str] = None) -> None:
    """Add a message to the specified chat session."""
    with get_connection() as conn:
        placeholder = "%s" if using_postgres() else "?"
        conn.execute(
            f"INSERT INTO messages (chat_id, role, content, model_name, provider) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})",
            (chat_id, role, content, model_name, provider)
        )
        conn.commit()

# --- Settings Operations ---

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve a setting value by key."""
    with get_connection() as conn:
        placeholder = "%s" if using_postgres() else "?"
        cursor = conn.cursor()
        cursor.execute(f"SELECT value FROM settings WHERE key = {placeholder}", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

def set_setting(key: str, value: str) -> None:
    """Save or update a setting value."""
    with get_connection() as conn:
        placeholder = "%s" if using_postgres() else "?"
        conn.execute(
            f"INSERT INTO settings (key, value) VALUES ({placeholder}, {placeholder}) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value)
        )
        conn.commit()
