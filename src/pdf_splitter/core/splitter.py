"""Apply a Manifest to a source PDF and write one file per segment."""

from __future__ import annotations

from pathlib import Path

import pypdf

from pdf_splitter.core.models import Manifest


def _unique_path(out_dir: Path, name: str) -> Path:
    candidate = out_dir / name
    if not candidate.exists():
        return candidate
    stem, suffix = Path(name).stem, Path(name).suffix
    i = 2
    while True:
        candidate = out_dir / f"{stem}_v{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def apply_split(
    *,
    source_pdf: Path,
    manifest: Manifest,
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reader = pypdf.PdfReader(str(source_pdf))
    written: list[Path] = []
    for segment in manifest.segments:
        writer = pypdf.PdfWriter()
        for p in range(segment.start, segment.end + 1):
            writer.add_page(reader.pages[p])
        out_path = _unique_path(output_dir, segment.suggested_filename)
        with out_path.open("wb") as f:
            writer.write(f)  # type: ignore[arg-type]
        written.append(out_path)
    return written
