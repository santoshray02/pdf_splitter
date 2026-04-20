"""Simple content-addressed disk cache for BoundaryDecision records."""

from __future__ import annotations

import hashlib
from pathlib import Path

from platformdirs import user_cache_dir

from pdf_splitter.core.models import BoundaryDecision


def make_cache_key(*, prompt: str, payload: bytes) -> str:
    h = hashlib.sha256()
    h.update(prompt.encode("utf-8"))
    h.update(b"\x00")
    h.update(payload)
    return h.hexdigest()


def default_cache_dir() -> Path:
    return Path(user_cache_dir("pdf_splitter")) / "classify"


class DiskCache:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def _file(self, key: str) -> Path:
        return self.path / f"{key}.json"

    def get(self, key: str) -> BoundaryDecision | None:
        f = self._file(key)
        if not f.exists():
            return None
        return BoundaryDecision.model_validate_json(f.read_text(encoding="utf-8"))

    def set(self, key: str, decision: BoundaryDecision) -> None:
        self._file(key).write_text(decision.model_dump_json(), encoding="utf-8")
