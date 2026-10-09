"""Batch folder processing — find supported files under a directory,
anonymize each, write the masked version to an output folder.

Each input file gets its own MappingStore so aliases are scoped per file.
Word documents are written back as .docx with their formatting preserved
and are verified for leftovers; other formats are written as text.
"""
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from anonymizer.core.mapping import MappingStore
from anonymizer.core.pipeline import Pipeline
from anonymizer.io import anonymize_docx, read_text, write_text
from anonymizer.io.readers import SUPPORTED_READ_SUFFIXES


@dataclass
class BatchResult:
    source: Path
    destination: Path | None
    error: str | None
    entity_count: int
    warnings: list[str] | None = None


def collect_files(folder: Path, *, recursive: bool = True) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    files: list[Path] = []
    for p in folder.glob(pattern):
        if p.is_file() and p.suffix.lower() in SUPPORTED_READ_SUFFIXES:
            files.append(p)
    return sorted(files)


def run_batch(
    pipeline: Pipeline,
    files: list[Path],
    output_dir: Path,
    *,
    output_suffix: str = ".txt",
    progress_cb: Callable[[int, int, Path], None] | None = None,
) -> list[BatchResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[BatchResult] = []
    for i, src in enumerate(files, start=1):
        if progress_cb is not None:
            progress_cb(i, len(files), src)
        try:
            store = MappingStore()
            if src.suffix.lower() == ".docx":
                dst = output_dir / (src.stem + "_anon.docx")
                result, report = anonymize_docx(src, dst, pipeline, store)
                if report.leaks:
                    dst.unlink(missing_ok=True)
                    leaked = ", ".join(sorted({part for part, _ in report.leaks}))
                    raise RuntimeError(f"контроль утечек не пройден ({leaked}), файл не сохранён")
                warnings = list(report.warnings)
            else:
                text = read_text(src)
                result = pipeline.run(text, store)
                dst = output_dir / (src.stem + "_anon" + output_suffix)
                write_text(dst, result.masked_text)
                warnings = []
            results.append(
                BatchResult(
                    source=src,
                    destination=dst,
                    error=None,
                    entity_count=sum(result.counts.values()),
                    warnings=warnings,
                )
            )
        except Exception as exc:
            results.append(
                BatchResult(source=src, destination=None, error=str(exc), entity_count=0)
            )
    return results
