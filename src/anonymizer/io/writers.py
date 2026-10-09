"""Write masked text to .txt or .docx.

There are two modes for .docx:
  * `write_text(path, text)` — create a new plain document (loses styles).
  * `anonymize_docx(source, path, pipeline, store)` — detect and mask every
    part of the original document (see :mod:`anonymizer.io.ooxml`), keeping
    run-level formatting, and verify the result for leftovers.
"""
from pathlib import Path

SUPPORTED_WRITE_SUFFIXES = (".txt", ".docx")


class UnsupportedFormatError(ValueError):
    pass


def write_text(path: Path, text: str) -> None:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        path.write_text(text, encoding="utf-8")
        return
    if suffix == ".docx":
        _write_docx(path, text)
        return
    raise UnsupportedFormatError(f"Формат не поддерживается: {suffix or '(без расширения)'}")


def _write_docx(path: Path, text: str) -> None:
    from docx import Document

    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(str(path))


def rewrite_docx(
    source: Path, destination: Path, replacements: list[tuple[str, str]]
) -> None:
    """Re-save `source` as `destination` with literal string replacements.

    All parts of the document are processed (body, tables, headers, footers,
    comments, metadata) and run formatting is preserved. Replacement happens
    in a single pass, so an inserted alias is never re-replaced.
    """
    import re

    from anonymizer.io.ooxml import DocxDocument

    doc = DocxDocument.open(source)
    mapping = {o: r for o, r in replacements if o}
    if not mapping:
        Path(destination).write_bytes(Path(source).read_bytes())
        return
    alt = "|".join(re.escape(o) for o in sorted(mapping, key=len, reverse=True))
    pattern = re.compile(alt)
    edits = [(m.start(), m.end(), mapping[m.group()]) for m in pattern.finditer(doc.text)]
    data = doc.apply_edits(edits)
    Path(destination).write_bytes(data)


def anonymize_docx(source: Path, destination: Path, pipeline, store):
    """Detect and mask personal data in a DOCX file, keeping its layout.

    Returns an :class:`~anonymizer.io.ooxml.ExportReport` with the leak
    verification results.
    """
    from anonymizer.io.ooxml import DocxDocument

    doc = DocxDocument.open(source)
    result = pipeline.run(doc.text, store)
    report = doc.save_anonymized(destination, result.spans, store)
    return result, report
