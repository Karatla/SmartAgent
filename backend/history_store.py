from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class HistoryStore:
    """Lightweight JSONL-backed chat history store.

    - Appends each message as a single JSON line to a file.
    - Mirrors content in-memory per session for quick reads.
    """

    def __init__(self, file_path: str = "backend/chat_history.jsonl") -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._sessions: Dict[str, List[Dict[str, Any]]] = {}

    def append(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        thinking: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "role": role,
            "content": content,
            "thinking": thinking or [],
            "meta": meta or {},
        }

        with self._lock:
            with self.file_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            self._sessions.setdefault(session_id, []).append(rec)

    def get_session(self, session_id: str) -> List[Dict[str, Any]]:
        # Serve from memory if available; otherwise, read from disk lazily
        with self._lock:
            if session_id in self._sessions:
                return list(self._sessions[session_id])

        # Fallback: scan file (simple but fine for dev)
        items: List[Dict[str, Any]] = []
        if not self.file_path.exists():
            return items
        with self.file_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("session_id") == session_id:
                    items.append(rec)
        return items

