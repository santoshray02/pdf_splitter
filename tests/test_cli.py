from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from pdf_splitter.cli import app
from pdf_splitter.core.models import BoundaryDecision

runner = CliRunner()


def _async_client(by_page: dict[int, BoundaryDecision]):
    client = AsyncMock()

    async def classify(*, page_index: int, **kwargs):
        return by_page[page_index], 0.0

    client.classify.side_effect = classify
    return client


def test_dry_run_exits_zero(text_pdf_factory):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    result = runner.invoke(app, ["split", str(src), "--dry-run", "--model", "m"])
    assert result.exit_code == 0


def test_profiles_list_runs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nope"))
    (tmp_path / "pdf_splitter.profiles").mkdir()
    (tmp_path / "pdf_splitter.profiles" / "demo.yaml").write_text(
        "name: demo\ndescription: d\nprompt: p\n"
    )
    result = runner.invoke(app, ["profiles", "list"])
    assert result.exit_code == 0
    assert "demo" in result.stdout


def test_manifest_show_pretty_prints(tmp_path):
    from pdf_splitter.core.manifest import build_manifest, write_manifest

    m = build_manifest(
        source="x.pdf",
        mode="text",
        model="m",
        config={},
        cost_usd=0.0,
        page_count=1,
        decisions=[],
    )
    out = tmp_path / "manifest.json"
    write_manifest(out, m)
    result = runner.invoke(app, ["manifest", "show", str(out)])
    assert result.exit_code == 0
    assert "schema_version" in result.stdout


def test_split_invokes_pipeline(text_pdf_factory, tmp_path):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    with patch("pdf_splitter.cli.LLMClient") as mock_client_cls:
        mock_client_cls.return_value = _async_client(
            {
                1: BoundaryDecision(page_index=1, is_boundary=False, confidence=0.1, reason=""),
            }
        )
        result = runner.invoke(
            app, ["split", str(src), "--model", "m", "--output-dir", str(tmp_path / "out")]
        )
    assert result.exit_code == 0
    assert (tmp_path / "out" / "pkt" / "manifest.json").exists()


def test_unknown_profile_returns_exit_2(text_pdf_factory):
    src = text_pdf_factory(["a", "b"], name="pkt.pdf")
    result = runner.invoke(app, ["split", str(src), "--model", "m", "--profile", "nope"])
    assert result.exit_code == 2
