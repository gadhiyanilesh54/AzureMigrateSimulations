"""Durable SQLite conversation store for Migration Copilot."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class ChatConversationStore:
    """Persist chat conversations and messages in a small local SQLite database."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_updated
                    ON conversations(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages(conversation_id, created_at ASC);
                """
            )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _title_from_message(message: str) -> str:
        title = " ".join(message.strip().split())
        if len(title) > 72:
            title = title[:69].rstrip() + "…"
        return title or "New migration conversation"

    def create_conversation(self, title: str = "New migration conversation") -> dict[str, Any]:
        conversation_id = f"conv-{uuid4().hex}"
        now = self._timestamp()
        normalized_title = self._title_from_message(title)
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conversation_id, normalized_title, now, now),
            )
        return {
            "id": conversation_id,
            "title": normalized_title,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
        }

    def list_conversations(self, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.title, c.created_at, c.updated_at,
                       COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_conversation(
        self,
        conversation_id: str,
        message_limit: int = 200,
    ) -> dict[str, Any] | None:
        safe_limit = max(1, min(int(message_limit), 500))
        with self._lock, self._connect() as connection:
            conversation = connection.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if conversation is None:
                return None
            rows = connection.execute(
                """
                SELECT id, role, content, metadata_json, created_at
                FROM (
                    SELECT id, role, content, metadata_json, created_at
                    FROM messages
                    WHERE conversation_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                )
                ORDER BY created_at ASC
                """,
                (conversation_id, safe_limit),
            ).fetchall()
        messages = []
        for row in rows:
            message = dict(row)
            try:
                message["metadata"] = json.loads(message.pop("metadata_json") or "{}")
            except json.JSONDecodeError:
                message["metadata"] = {}
                message.pop("metadata_json", None)
            messages.append(message)
        result = dict(conversation)
        result["message_count"] = len(messages)
        result["messages"] = messages
        return result

    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if role not in ("user", "assistant"):
            raise ValueError("Chat role must be 'user' or 'assistant'.")
        if not content.strip():
            raise ValueError("Chat message content cannot be empty.")
        message_id = f"msg-{uuid4().hex}"
        now = self._timestamp()
        with self._lock, self._connect() as connection:
            conversation = connection.execute(
                "SELECT title FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if conversation is None:
                raise KeyError(f"Conversation '{conversation_id}' was not found.")
            connection.execute(
                """
                INSERT INTO messages
                    (id, conversation_id, role, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    conversation_id,
                    role,
                    content.strip(),
                    json.dumps(metadata or {}, separators=(",", ":"), default=str),
                    now,
                ),
            )
            title = conversation["title"]
            if role == "user":
                message_count = connection.execute(
                    "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
                    (conversation_id,),
                ).fetchone()[0]
                if message_count == 1 or title == "New migration conversation":
                    title = self._title_from_message(content)
            connection.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, conversation_id),
            )
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content.strip(),
            "metadata": metadata or {},
            "created_at": now,
        }

    def get_recent_history(
        self,
        conversation_id: str,
        limit: int = 12,
    ) -> list[dict[str, str]]:
        conversation = self.get_conversation(conversation_id, message_limit=limit)
        if conversation is None:
            return []
        return [
            {"role": message["role"], "content": message["content"]}
            for message in conversation["messages"]
        ]

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
        return cursor.rowcount > 0
