"""Load YAML profile files, searching local → XDG → package builtins."""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

import platformdirs
import yaml

from pdf_splitter.core.models import ProfileConfig


class ProfileNotFoundError(Exception):
    """Raised when a named profile cannot be found in any search location."""


def _local_dir() -> Path:
    return Path.cwd() / "pdf_splitter.profiles"


def _xdg_dir() -> Path:
    # Honor XDG_CONFIG_HOME if set (enables hermetic test isolation and
    # lets power users override). Otherwise fall back to the
    # platform-native user config dir: ~/.config on Linux, ~/Library/Application
    # Support on macOS, %APPDATA% on Windows.
    root = os.environ.get("XDG_CONFIG_HOME")
    base = Path(root) if root else Path(platformdirs.user_config_dir("pdf_splitter"))
    return (base / "pdf_splitter" if root else base) / "profiles"


def _builtin_dir() -> Path:
    return Path(str(resources.files("pdf_splitter.profiles")))


def search_dirs() -> list[Path]:
    """Return the three profile-directory tiers in precedence order.

    Public so the CLI's `profiles list` can enumerate from the same set the
    library's `load_profile` searches — keeps listing and loading consistent.
    """
    return [_local_dir(), _xdg_dir(), _builtin_dir()]


def _candidates(name: str) -> list[Path]:
    return [d / f"{name}.yaml" for d in search_dirs()]


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
