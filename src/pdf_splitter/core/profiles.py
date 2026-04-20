"""Load YAML profile files, searching local → XDG → package builtins."""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

import yaml

from pdf_splitter.core.models import ProfileConfig


class ProfileNotFoundError(Exception):
    """Raised when a named profile cannot be found in any search location."""


def _local_dir() -> Path:
    return Path.cwd() / "pdf_splitter.profiles"


def _xdg_dir() -> Path:
    root = os.environ.get("XDG_CONFIG_HOME")
    base = Path(root) if root else Path.home() / ".config"
    return base / "pdf_splitter" / "profiles"


def _builtin_dir() -> Path:
    return Path(str(resources.files("pdf_splitter.profiles")))


def _candidates(name: str) -> list[Path]:
    return [
        _local_dir() / f"{name}.yaml",
        _xdg_dir() / f"{name}.yaml",
        _builtin_dir() / f"{name}.yaml",
    ]


def find_profile(name: str) -> Path | None:
    for p in _candidates(name):
        if p.exists():
            return p
    return None


def load_profile(name: str) -> ProfileConfig:
    path = find_profile(name)
    if path is None:
        raise ProfileNotFoundError(f"Profile not found: {name}")
    raw: dict[str, object] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ProfileConfig.model_validate(raw)
