"""Write a single string of text to .txt or .docx.

No attempt at preserving original document structure — users who need that
should export to .txt and paste back into their source application manually.
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
