from __future__ import annotations

from pathlib import Path

import pytest

from pdf_splitter.core.profiles import ProfileNotFoundError, find_profile, load_profile


def _write_profile(path: Path, name: str, prompt: str) -> None:
    path.write_text(f"name: {name}\ndescription: d\nprompt: |\n  {prompt}\n")


def test_load_profile_from_local_dir(tmp_path: Path, monkeypatch):
    local = tmp_path / "pdf_splitter.profiles"
    local.mkdir()
    _write_profile(local / "foo.yaml", "foo", "hello")
    monkeypatch.chdir(tmp_path)
    # Isolate from any real $HOME/.config entries the test developer has.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nope"))
    p = load_profile("foo")
    assert p.name == "foo"
    assert "hello" in p.prompt


def test_load_profile_from_xdg(tmp_path: Path, monkeypatch):
    xdg = tmp_path / "xdg"
    (xdg / "pdf_splitter" / "profiles").mkdir(parents=True)
    _write_profile(xdg / "pdf_splitter" / "profiles" / "bar.yaml", "bar", "xdg")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.chdir(tmp_path)  # no local profile
    p = load_profile("bar")
    assert "xdg" in p.prompt


def test_local_shadows_xdg(tmp_path: Path, monkeypatch):
    local = tmp_path / "pdf_splitter.profiles"
    local.mkdir()
    _write_profile(local / "baz.yaml", "baz", "LOCAL")
    xdg = tmp_path / "xdg"
    (xdg / "pdf_splitter" / "profiles").mkdir(parents=True)
    _write_profile(xdg / "pdf_splitter" / "profiles" / "baz.yaml", "baz", "XDG")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.chdir(tmp_path)
    p = load_profile("baz")
    assert "LOCAL" in p.prompt


def test_missing_profile_raises(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nope"))
    with pytest.raises(ProfileNotFoundError):
        load_profile("does-not-exist")


def test_find_profile_returns_none_for_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nope"))
    assert find_profile("does-not-exist") is None
