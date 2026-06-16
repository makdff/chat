import sqlite3
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chats.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    # Enable foreign keys support in SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database and create tables if they do not exist."""
    with get_connection() as conn:
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
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chats (title) VALUES (?)", (title,))
        conn.commit()
        return cursor.lastrowid

def get_chats() -> List[Dict[str, Any]]:
    """Retrieve all chats sorted by creation time (newest first)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, created_at FROM chats ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]

def rename_chat(chat_id: int, new_title: str) -> None:
    """Rename an existing chat session."""
    with get_connection() as conn:
        conn.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))
        conn.commit()

def delete_chat(chat_id: int) -> None:
    """Delete a chat session (messages will be deleted cascadingly)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        conn.commit()

# --- Message CRUD Operations ---

def get_chat_messages(chat_id: int) -> List[Dict[str, Any]]:
    """Retrieve all messages for a given chat ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, model_name, provider, created_at FROM messages WHERE chat_id = ? ORDER BY id ASC",
            (chat_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def add_message(chat_id: int, role: str, content: str, model_name: Optional[str] = None, provider: Optional[str] = None) -> None:
    """Add a message to the specified chat session."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, role, content, model_name, provider) VALUES (?, ?, ?, ?, ?)",
            (chat_id, role, content, model_name, provider)
        )
        conn.commit()

# --- Settings Operations ---

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve a setting value by key."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

def set_setting(key: str, value: str) -> None:
    """Save or update a setting value."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value)
        )
        conn.commit()
