"""Write masked text to .txt or .docx.

There are two modes for .docx:
  * `write_text(path, text)` — create a new plain document (loses styles).
  * `rewrite_docx(source, path, replacements)` — open the original document
    and perform in-place string substitution on each run's text, preserving
    paragraph styles, fonts, and layout wherever possible.
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
    """Re-save `source` as `destination` with the given string replacements
    applied to every paragraph and table cell. Replacements are applied in
    order, longest original first, to avoid substring clobbering.
    """
    from docx import Document

    ordered = sorted(replacements, key=lambda r: len(r[0]), reverse=True)
    doc = Document(str(source))

    def _apply_to_paragraph(paragraph) -> None:
        # We join all runs, do replacements on the joined text, then rewrite
        # the first run's text and clear the rest. Styles on the first run
        # are preserved for the whole paragraph; run-level styles within the
        # paragraph are lost, which is an acceptable trade-off.
        full = "".join(run.text for run in paragraph.runs)
        if not full:
            return
        new = full
        for original, replacement in ordered:
            if original and original in new:
                new = new.replace(original, replacement)
        if new == full:
            return
        if paragraph.runs:
            paragraph.runs[0].text = new
            for run in paragraph.runs[1:]:
                run.text = ""
        else:
            paragraph.add_run(new)

    for paragraph in doc.paragraphs:
        _apply_to_paragraph(paragraph)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _apply_to_paragraph(paragraph)

    doc.save(str(destination))
