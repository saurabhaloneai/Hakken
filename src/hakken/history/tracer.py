from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4


@dataclass(frozen=True)
class TraceSession:
    id: str
    path: Path


class TraceLogger:
    def __init__(
        self,
        base_dir: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        self._enabled = self._resolve_enabled(enabled)
        self._base_dir = Path(base_dir or os.getenv("TRACE_DIR", "logs/traces")).expanduser()
        if self._enabled:
            self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def start_session(self, metadata: Optional[Dict[str, Any]] = None) -> Optional[TraceSession]:
        if not self._enabled:
            return None

        session_id = self._build_session_id(metadata)
        file_path = self._base_dir / f"{session_id}.jsonl"
        self._write(
            file_path,
            {
                "event": "session_start",
                "session_id": session_id,
                "ts": self._timestamp(),
                "metadata": self._make_json_safe(metadata or {}),
            },
        )
        return TraceSession(session_id, file_path)

    def log_message(
        self,
        session: Optional[TraceSession],
        message: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self._enabled or session is None:
            return

        payload = {
            "event": "message",
            "session_id": session.id,
            "ts": self._timestamp(),
            "metadata": self._make_json_safe(metadata or {}),
            "message": self._make_json_safe(message),
        }
        self._write(session.path, payload)

    def log_event(
        self,
        session: Optional[TraceSession],
        event_name: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self._enabled or session is None:
            return

        payload = {
            "event": event_name,
            "session_id": session.id,
            "ts": self._timestamp(),
            "details": self._make_json_safe(details or {}),
        }
        self._write(session.path, payload)

    def _write(self, file_path: Path, payload: Dict[str, Any]) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("a", encoding="utf-8") as trace_file:
            trace_file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _build_session_id(self, metadata: Optional[Dict[str, Any]]) -> str:
        if metadata and metadata.get("session_id"):
            return str(metadata["session_id"])
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        return f"trace-{timestamp}-{uuid4().hex[:6]}"

    def _make_json_safe(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, dict):
            return {str(k): self._make_json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._make_json_safe(v) for v in value]
        if hasattr(value, "model_dump"):
            return self._make_json_safe(value.model_dump())
        if hasattr(value, "dict"):
            return self._make_json_safe(value.dict())
        if hasattr(value, "__dict__"):
            return self._make_json_safe(vars(value))
        return str(value)

    def _resolve_enabled(self, explicit: Optional[bool]) -> bool:
        if explicit is not None:
            return explicit
        env_value = os.getenv("TRACE_ENABLED")
        if env_value is None:
            return True
        return env_value.strip().lower() in {"1", "true", "yes", "on"}