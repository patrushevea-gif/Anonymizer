"""Format-preserving, complete DOCX anonymisation.

A ``.docx`` file is a ZIP package of XML parts. Personal data lives in many
of them, not only in the main body:

* ``word/document.xml``       — body text, tables, text boxes, field codes,
                                tracked deletions, image alt-text
* ``word/header*.xml`` / ``footer*.xml``
* ``word/comments.xml``, ``footnotes.xml``, ``endnotes.xml``
* ``word/charts/*``, ``word/diagrams/*``, ``word/glossary/*``
* ``word/_rels/*.rels``       — external hyperlink targets (``mailto:``…)
* ``docProps/core.xml`` / ``app.xml`` / ``custom.xml`` — metadata
* author attributes of comments and tracked changes, ``people.xml``
* ``docProps/thumbnail.*``    — a rendered picture of the first page

``DocxDocument`` collects every piece of text from every part into *streams*
(one per paragraph or attribute). Each stream remembers which XML text node
holds each character. The concatenation of all streams is the document text
the detectors see, so a detected span maps back to exact characters inside
exact ``<w:t>`` nodes. Replacements are written in place:

* run formatting (bold, colour, italics, underline) is untouched — the alias
  takes the formatting of the run where the original value started;
* hidden text (``<w:vanish/>``) stays hidden;
* a name split across several runs is replaced as a whole.

Personal metadata that has no business being in an anonymised file (author,
last editor, company, manager, custom properties, thumbnail, template path,
document variables) is removed. Finally every output is re-read and checked
for leftovers of every masked value; anything found outside the modelled
places is scrubbed and reported.
"""
from __future__ import annotations

import bisect
import io
import posixpath
import re
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

from anonymizer.core.entities import EntitySpan
from anonymizer.core.mapping import MappingStore
from anonymizer.core.masking import assign_aliases
from anonymizer.core.reverse import restore_replacements

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC = "http://purl.org/dc/elements/1.1/"
DCTERMS = "http://purl.org/dc/terms/"
EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

_PARSER = etree.XMLParser(
    resolve_entities=False, no_network=True, huge_tree=True, remove_blank_text=False
)

ANON_AUTHOR = "Автор"

# Parts with formatting definitions only — never personal text.
_SKIP_PARTS = re.compile(
    r"^word/(?:styles|stylesWithEffects|fontTable|numbering|webSettings|settings"
    r"|theme/.*|commentsExtended|commentsIds|commentsExtensible|people)\.xml$"
)

_CORE_TEXT_FIELDS = (
    (DC, "title"), (DC, "subject"), (CP, "keywords"), (DC, "description"),
    (CP, "category"), (CP, "contentStatus"), (DC, "identifier"), (CP, "version"),
)
_CORE_SCRUB_FIELDS = ((DC, "creator"), (CP, "lastModifiedBy"))
_APP_SCRUB_FIELDS = ("Company", "Manager", "HyperlinkBase")

# Attributes that carry user-visible free text.
_TEXT_ATTRS = (
    (f"{{{WP}}}docPr", ("descr", "title")),
    (f"{{{PIC}}}cNvPr", ("descr", "title")),
    (f"{{{W}}}fldSimple", (f"{{{W}}}instr",)),
    (f"{{{W}}}hyperlink", (f"{{{W}}}tooltip",)),
    (f"{{{W}}}helpText", (f"{{{W}}}val",)),
    (f"{{{W}}}statusText", (f"{{{W}}}val",)),
    (f"{{{W}}}listEntry", (f"{{{W}}}val",)),
    (f"{{{W}}}alias", (f"{{{W}}}val",)),
)
_TEXT_ATTR_MAP = {tag: attrs for tag, attrs in _TEXT_ATTRS}
_AUTHOR_ATTRS = (f"{{{W}}}author", f"{{{W}}}initials")

_SECTION_LABELS = (
    (re.compile(r"^word/document\.xml$"), ""),
    (re.compile(r"^word/footnotes\.xml$"), "Сноски"),
    (re.compile(r"^word/endnotes\.xml$"), "Концевые сноски"),
    (re.compile(r"^word/comments\.xml$"), "Комментарии"),
    (re.compile(r"^word/header\d*\.xml$"), "Верхний колонтитул"),
    (re.compile(r"^word/footer\d*\.xml$"), "Нижний колонтитул"),
    (re.compile(r"^word/charts/"), "Диаграмма"),
    (re.compile(r"^word/diagrams/"), "Схема SmartArt"),
    (re.compile(r"^word/glossary/"), "Стандартные блоки"),
    (re.compile(r"^word/"), "Прочее содержимое"),
)


def _section_rank(name: str) -> tuple[int, str]:
    for i, (pattern, _) in enumerate(_SECTION_LABELS):
        if pattern.search(name):
            num = re.search(r"(\d+)\.xml$", name)
            return (i, f"{int(num.group(1)):05d}" if num else name)
    return (len(_SECTION_LABELS), name)


def _section_label(name: str) -> str:
    for pattern, label in _SECTION_LABELS:
        if pattern.search(name):
            return label
    return "Прочее содержимое"


# --------------------------------------------------------------------- model
@dataclass
class _Slot:
    element: etree._Element | None  # None → virtual char (tab / break)
    attr: str | None                # None → element.text
    start: int
    end: int
    edits: list[tuple[int, int, str]] = field(default_factory=list)

    @property
    def is_real(self) -> bool:
        return self.element is not None


@dataclass
class _Stream:
    part: str
    slots: list[_Slot]
    text: str
    offset: int = 0


@dataclass
class ExportReport:
    """Outcome of a DOCX export, shown to the user after saving."""

    replaced: int = 0
    parts_changed: list[str] = field(default_factory=list)
    metadata_removed: list[str] = field(default_factory=list)
    leaks_fixed: list[tuple[str, str]] = field(default_factory=list)
    leaks: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.leaks


def _nearest(el: etree._Element, tag: str) -> etree._Element | None:
    p = el.getparent()
    while p is not None:
        if p.tag == tag:
            return p
        p = p.getparent()
    return None


class _Package:
    """Parsed, mutable view of a DOCX package."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            self.infos = zf.infolist()
            self.blobs = {i.filename: zf.read(i.filename) for i in self.infos}
        if "word/document.xml" not in self.blobs:
            raise ValueError("Файл не является документом Word (.docx)")
        self.trees: dict[str, etree._ElementTree] = {}
        self.dirty: set[str] = set()
        self.removed: set[str] = set()
        self.streams: list[_Stream] = []
        self.text = ""
        root = self.tree("word/document.xml")
        if root is None:
            raise ValueError("Документ Word повреждён: не удаётся прочитать основной текст")
        if etree.QName(root.getroot()).namespace != W:
            # Strict Open XML uses different namespaces; processing it
            # silently would find no text at all — refuse loudly instead.
            raise ValueError(
                "Документ сохранён в формате «Strict Open XML» и не поддерживается. "
                "Пересохраните его в Word как обычный «Документ Word (.docx)»."
            )
        self._build()

    # ------------------------------------------------------------ parsing
    def tree(self, name: str) -> etree._ElementTree | None:
        if name in self.trees:
            return self.trees[name]
        blob = self.blobs.get(name)
        if blob is None:
            return None
        try:
            root = etree.fromstring(blob, _PARSER)
        except etree.XMLSyntaxError:
            return None
        tree = root.getroottree()
        self.trees[name] = tree
        return tree

    def content_parts(self) -> list[str]:
        names = [
            n for n in self.blobs
            if n.startswith("word/") and n.endswith(".xml") and not _SKIP_PARTS.match(n)
        ]
        return sorted(names, key=_section_rank)

    def _build(self) -> None:
        pieces: list[str] = []
        pos = 0

        def emit_label(label: str) -> None:
            nonlocal pos
            line = f"[{label}]"
            if pieces:
                pieces.append("\n")
                pos += 1
            pieces.append(line)
            pos += len(line)

        def emit(stream: _Stream, sep: str) -> None:
            nonlocal pos
            if pieces:
                pieces.append(sep)
                pos += len(sep)
            stream.offset = pos
            pieces.append(stream.text)
            pos += len(stream.text)
            self.streams.append(stream)

        for name in self.content_parts():
            tree = self.tree(name)
            if tree is None:
                continue
            label = _section_label(name)
            body = name == "word/document.xml"
            streams = list(self._wordml_streams(name, tree, keep_empty=body))
            streams += list(self._drawing_streams(name, tree))
            streams += list(self._attr_streams(name, tree))
            if not body:
                streams = [s for s in streams if s[0].text.strip()]
            if not streams:
                continue
            if label:
                emit_label(label)
            for stream, sep in streams:
                emit(stream, sep if body else "\n")

        meta = list(self._metadata_streams())
        if meta:
            emit_label("Свойства документа")
            for stream in meta:
                emit(stream, "\n")

        links = list(self._rels_streams())
        if links:
            emit_label("Гиперссылки")
            for stream in links:
                emit(stream, "\n")

        self.text = "".join(pieces)

    def _wordml_streams(self, name, tree, keep_empty: bool):
        root = tree.getroot()
        prev_cell = None
        extra: list[tuple[_Stream, str]] = []
        for p in root.iter(f"{{{W}}}p"):
            main: list[_Slot] = []
            dels: list[_Slot] = []
            instr: list[_Slot] = []
            buf: list[str] = []
            dbuf: list[str] = []
            ibuf: list[str] = []
            for el in p.iter():
                tag = el.tag
                if tag not in (
                    f"{{{W}}}t", f"{{{W}}}delText", f"{{{W}}}instrText",
                    f"{{{W}}}tab", f"{{{W}}}br", f"{{{W}}}cr",
                ):
                    continue
                if _nearest(el, f"{{{W}}}p") is not p:
                    continue
                if tag == f"{{{W}}}t":
                    _add_slot(main, buf, el, None, el.text or "")
                elif tag == f"{{{W}}}delText":
                    _add_slot(dels, dbuf, el, None, el.text or "")
                elif tag == f"{{{W}}}instrText":
                    _add_slot(instr, ibuf, el, None, el.text or "")
                elif el.getparent() is not None and el.getparent().tag == f"{{{W}}}r":
                    _add_virtual(main, buf, "\t" if tag == f"{{{W}}}tab" else "\n")
            cell = _nearest(p, f"{{{W}}}tc")
            sep = "\n"
            if (
                cell is not None and prev_cell is not None and cell is not prev_cell
                and cell.getparent() is prev_cell.getparent()
            ):
                sep = "\t"
            prev_cell = cell
            text = "".join(buf)
            if main and (keep_empty or text.strip()):
                yield _Stream(name, main, text), sep
            elif keep_empty and not main:
                yield _Stream(name, [], ""), sep
            if dels:
                extra.append((_Stream(name, dels, "".join(dbuf)), "\n"))
            if instr:
                extra.append((_Stream(name, instr, "".join(ibuf)), "\n"))
        yield from extra

    def _drawing_streams(self, name, tree):
        root = tree.getroot()
        for p in root.iter(f"{{{A}}}p"):
            slots: list[_Slot] = []
            buf: list[str] = []
            for el in p.iter(f"{{{A}}}t", f"{{{A}}}br"):
                if el.tag == f"{{{A}}}t":
                    _add_slot(slots, buf, el, None, el.text or "")
                else:
                    _add_virtual(slots, buf, "\n")
            if slots:
                yield _Stream(name, slots, "".join(buf)), "\n"
        for v in root.iter(f"{{{C}}}v"):
            parent = v.getparent()
            grand = parent.getparent() if parent is not None else None
            in_str = any(
                anc is not None and anc.tag in (f"{{{C}}}strCache", f"{{{C}}}strLit")
                for anc in (parent, grand)
            )
            if in_str and v.text:
                slots: list[_Slot] = []
                _add_slot(slots, [], v, None, v.text)
                yield _Stream(name, slots, v.text), "\n"

    def _attr_streams(self, name, tree):
        root = tree.getroot()
        for el in root.iter(*_TEXT_ATTR_MAP.keys()):
            for attr in _TEXT_ATTR_MAP[el.tag]:
                value = el.get(attr)
                if value:
                    yield _Stream(name, [_Slot(el, attr, 0, len(value))], value), "\n"

    def _metadata_streams(self):
        core = self.tree("docProps/core.xml")
        if core is not None:
            for ns, local in _CORE_TEXT_FIELDS:
                for el in core.getroot().iter(f"{{{ns}}}{local}"):
                    if el.text and el.text.strip():
                        yield _Stream("docProps/core.xml", [_Slot(el, None, 0, len(el.text))], el.text)
        app = self.tree("docProps/app.xml")
        if app is not None:
            for vec_parent in ("TitlesOfParts", "HLinks"):
                for holder in app.getroot().iter(f"{{{EP}}}{vec_parent}"):
                    for el in holder.iter(f"{{{VT}}}lpstr", f"{{{VT}}}lpwstr"):
                        if el.text and el.text.strip():
                            yield _Stream("docProps/app.xml", [_Slot(el, None, 0, len(el.text))], el.text)

    def _rels_streams(self):
        for name in sorted(self.blobs):
            if not (name.startswith("word/") and name.endswith(".rels")):
                continue
            tree = self.tree(name)
            if tree is None:
                continue
            for rel in tree.getroot().iter(f"{{{REL}}}Relationship"):
                if rel.get("TargetMode") == "External" and rel.get("Type", "").endswith("/hyperlink"):
                    target = rel.get("Target") or ""
                    if target:
                        yield _Stream(name, [_Slot(rel, "Target", 0, len(target))], target)

    # ------------------------------------------------------------ editing
    def apply_edits(self, edits: Iterable[tuple[int, int, str]]) -> int:
        starts = [s.offset for s in self.streams]
        count = 0
        for start, end, replacement in sorted(edits):
            i = max(bisect.bisect_right(starts, start) - 1, 0)
            first = True
            while i < len(self.streams):
                stream = self.streams[i]
                s_start, s_end = stream.offset, stream.offset + len(stream.text)
                if s_start >= end:
                    break
                lo, hi = max(start, s_start), min(end, s_end)
                if lo < hi or (lo == hi and start == end):
                    placed = _edit_stream(stream, lo - s_start, hi - s_start,
                                          replacement if first else "")
                    if placed:
                        self.dirty.add(stream.part)
                        if first:
                            count += 1
                        first = False
                i += 1
        emptied: list[etree._Element] = []
        for stream in self.streams:
            for slot in stream.slots:
                if slot.edits:
                    _commit_slot(slot)
                    if slot.attr is None and slot.element.tag == f"{{{W}}}t" and not slot.element.text:
                        emptied.append(slot.element)
        _drop_empty_runs(emptied)
        return count

    # ------------------------------------------------------------ hygiene
    def scrub_metadata(self, report: ExportReport) -> None:
        core = self.tree("docProps/core.xml")
        if core is not None:
            for ns, local in _CORE_SCRUB_FIELDS:
                for el in core.getroot().iter(f"{{{ns}}}{local}"):
                    if el.text:
                        el.text = ""
                        report.metadata_removed.append(f"core:{local}")
                        self.dirty.add("docProps/core.xml")
        app = self.tree("docProps/app.xml")
        if app is not None:
            for local in _APP_SCRUB_FIELDS:
                for el in app.getroot().iter(f"{{{EP}}}{local}"):
                    if el.text:
                        el.text = ""
                        report.metadata_removed.append(f"app:{local}")
                        self.dirty.add("docProps/app.xml")

        # Authors of comments, tracked changes and the people list.
        for name in list(self.blobs):
            if not (name.startswith("word/") and name.endswith(".xml")):
                continue
            blob = self.blobs[name]
            if b"author" not in blob and b"initials" not in blob and b"userId" not in blob:
                continue
            tree = self.tree(name)
            if tree is None:
                continue
            changed = False
            for el in tree.getroot().iter():
                for attr in _AUTHOR_ATTRS:
                    if el.get(attr):
                        el.set(attr, ANON_AUTHOR if attr.endswith("author") else "А")
                        changed = True
                if el.get(f"{{{W15}}}author"):
                    el.set(f"{{{W15}}}author", ANON_AUTHOR)
                    changed = True
                if el.get(f"{{{W15}}}userId"):
                    el.set(f"{{{W15}}}userId", "")
                    changed = True
            if changed:
                self.dirty.add(name)
                report.metadata_removed.append(f"authors:{name}")

        # Document variables may hold arbitrary hidden text.
        settings = self.tree("word/settings.xml")
        if settings is not None:
            for dv in list(settings.getroot().iter(f"{{{W}}}docVars")):
                dv.getparent().remove(dv)
                self.dirty.add("word/settings.xml")
                report.metadata_removed.append("settings:docVars")

        # Template path reveals the Windows user name (C:\Users\<name>\…).
        rels = self.tree("word/_rels/settings.xml.rels")
        if rels is not None:
            for rel in rels.getroot().iter(f"{{{REL}}}Relationship"):
                if rel.get("Type", "").endswith("/attachedTemplate"):
                    target = rel.get("Target") or ""
                    base = re.split(r"[\\/]", target)[-1] or "Normal.dotm"
                    if target != base:
                        rel.set("Target", base)
                        self.dirty.add("word/_rels/settings.xml.rels")
                        report.metadata_removed.append("template-path")

        # Custom properties and the first-page thumbnail are dropped whole.
        for rel_type, label in (("/custom-properties", "custom-properties"), ("/thumbnail", "thumbnail")):
            self._drop_package_rel(rel_type, label, report)

    def _drop_package_rel(self, type_suffix: str, label: str, report: ExportReport) -> None:
        rels = self.tree("_rels/.rels")
        if rels is None:
            return
        for rel in list(rels.getroot().iter(f"{{{REL}}}Relationship")):
            if not rel.get("Type", "").endswith(type_suffix):
                continue
            target = (rel.get("Target") or "").lstrip("/")
            rel.getparent().remove(rel)
            self.dirty.add("_rels/.rels")
            if target in self.blobs:
                self.removed.add(target)
                ct = self.tree("[Content_Types].xml")
                if ct is not None:
                    for ov in list(ct.getroot().iter(f"{{{CT}}}Override")):
                        if ov.get("PartName", "").lstrip("/") == target:
                            ov.getparent().remove(ov)
                            self.dirty.add("[Content_Types].xml")
            report.metadata_removed.append(label)

    # ------------------------------------------------------------ output
    def serialize(self) -> bytes:
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for info in self.infos:
                name = info.filename
                if name in self.removed:
                    continue
                if name in self.dirty and name in self.trees:
                    tree = self.trees[name]
                    data = etree.tostring(
                        tree, xml_declaration=True, encoding="UTF-8",
                        standalone=tree.docinfo.standalone,
                    )
                else:
                    data = self.blobs[name]
                new_info = zipfile.ZipInfo(name, date_time=info.date_time)
                new_info.compress_type = info.compress_type
                new_info.external_attr = info.external_attr
                zf.writestr(new_info, data)
        return out.getvalue()


def _add_slot(slots: list[_Slot], buf: list[str], el, attr, text: str) -> None:
    start = sum(len(b) for b in buf)
    slots.append(_Slot(el, attr, start, start + len(text)))
    buf.append(text)


def _add_virtual(slots: list[_Slot], buf: list[str], ch: str) -> None:
    start = sum(len(b) for b in buf)
    slots.append(_Slot(None, None, start, start + len(ch)))
    buf.append(ch)


def _edit_stream(stream: _Stream, start: int, end: int, replacement: str) -> bool:
    """Record an edit of ``stream.text[start:end]``. Returns True if placed."""
    real = [s for s in stream.slots if s.is_real]
    hit = [s for s in real if s.start < end and start < s.end]
    if not hit:
        # Insertion point or a range of only virtual characters: attach the
        # replacement to the nearest real slot so nothing is silently lost.
        if not replacement:
            return False
        after = [s for s in real if s.start >= start]
        target = after[0] if after else (real[-1] if real else None)
        if target is None:
            return False
        pos = max(0, min(start, target.end) - target.start)
        target.edits.append((pos, pos, replacement))
        return True
    for i, slot in enumerate(hit):
        lo = max(start, slot.start) - slot.start
        hi = min(end, slot.end) - slot.start
        slot.edits.append((lo, hi, replacement if i == 0 else ""))
    return True


def _commit_slot(slot: _Slot) -> None:
    el = slot.element
    original = el.get(slot.attr) if slot.attr else (el.text or "")
    text = original
    for lo, hi, rep in sorted(slot.edits, key=lambda e: (e[0], e[1]), reverse=True):
        text = text[:lo] + rep + text[hi:]
    slot.edits = []
    if slot.attr:
        el.set(slot.attr, text)
    else:
        el.text = text
        if el.tag in (f"{{{W}}}t", f"{{{W}}}delText", f"{{{W}}}instrText"):
            el.set(XML_SPACE, "preserve")


def _drop_empty_runs(emptied: list[etree._Element]) -> None:
    """Remove runs left with nothing but formatting after a merge."""
    keep = {f"{{{W}}}rPr", f"{{{W}}}t"}
    for t in emptied:
        run = t.getparent()
        if run is None or run.tag != f"{{{W}}}r" or run.getparent() is None:
            continue
        children = list(run)
        if all(c.tag in keep for c in children) and not any(
            c.tag == f"{{{W}}}t" and c.text for c in children
        ):
            run.getparent().remove(run)


# ----------------------------------------------------------------- leak scan
def _raw_strings(tree: etree._ElementTree):
    """Yield ``(element, attr_or_None, value)`` for every text-bearing place."""
    for el in tree.getroot().iter():
        if not isinstance(el.tag, str):
            continue
        if el.text:
            yield el, None, el.text
        for attr, value in el.attrib.items():
            if value and _is_free_text_attr(el, attr):
                yield el, attr, value


def _is_free_text_attr(el, attr: str) -> bool:
    local = etree.QName(attr).localname
    if local in ("descr", "title", "tooltip", "instr", "author", "initials", "userId"):
        return True
    if local == "Target" and el.get("TargetMode") == "External":
        return True
    if local == "val":
        parent_local = etree.QName(el).localname
        return parent_local in ("helpText", "statusText", "listEntry", "alias", "default")
    return False


def _scan_and_fix(pkg: _Package, store: MappingStore, report: ExportReport, *, fix: bool) -> None:
    from anonymizer.core.postprocess import surfaces_regex

    alias_of: dict[str, str] = {}
    for surface, alias in store.all_variants():
        key = " ".join(surface.split())
        if sum(ch.isalnum() for ch in key) >= 3:
            alias_of.setdefault(key, alias)
    rx = surfaces_regex(alias_of)
    if rx is None:
        return

    def _hits(value: str) -> list[str]:
        return [" ".join(m.group().split()) for m in rx.finditer(value)]

    # 1. The modelled text (streams joined) catches values split across runs.
    #    Only meaningful on a freshly parsed package (streams are not updated
    #    by edits), i.e. in verification mode.
    if not fix:
        for stream in pkg.streams:
            for hit in _hits(stream.text):
                report.leaks.append((stream.part, hit))
    # 2. Every text node / free-text attribute in every XML part.
    for name in pkg.blobs:
        if name in pkg.removed or not (name.endswith(".xml") or name.endswith(".rels")):
            continue
        if name == "[Content_Types].xml":
            continue
        tree = pkg.tree(name)
        if tree is None:
            continue
        for el, attr, value in list(_raw_strings(tree)):
            hits = _hits(value)
            if not hits:
                continue
            if not fix:
                report.leaks.extend((name, h) for h in hits)
                continue
            new = rx.sub(lambda m: alias_of.get(" ".join(m.group().split()), m.group()), value)
            report.leaks_fixed.extend((name, h) for h in hits)
            if attr:
                el.set(attr, new)
            else:
                el.text = new
            pkg.dirty.add(name)


def _binary_warnings(pkg: _Package, report: ExportReport) -> None:
    embedded = [n for n in pkg.blobs if n.startswith("word/embeddings/")]
    if embedded:
        report.warnings.append(
            "Встроенные объекты (OLE, вложенные файлы) не анализируются: "
            + ", ".join(posixpath.basename(n) for n in embedded)
            + ". Удалите их из документа или проверьте вручную."
        )
    media = [n for n in pkg.blobs if n.startswith("word/media/")]
    if media:
        report.warnings.append(
            f"Изображения ({len(media)} шт.) не распознаются: текст и подписи на "
            "картинках и сканах не обезличиваются."
        )


# ----------------------------------------------------------------- public API
class DocxDocument:
    """A loaded DOCX file: exposes its full text and exports masked copies."""

    def __init__(self, data: bytes, source: Path | None = None) -> None:
        self._data = data
        self.source = source
        self._pkg = _Package(data)

    @classmethod
    def open(cls, path: Path) -> DocxDocument:
        return cls(Path(path).read_bytes(), Path(path))

    @property
    def text(self) -> str:
        return self._pkg.text

    def _fresh(self) -> _Package:
        pkg = _Package(self._data)
        if pkg.text != self._pkg.text:  # pragma: no cover - determinism guard
            raise RuntimeError("Внутренняя ошибка: нестабильное чтение DOCX")
        return pkg

    def anonymize(self, spans: list[EntitySpan], store: MappingStore) -> tuple[bytes, ExportReport]:
        """Return the anonymised package and a verification report.

        *spans* must refer to :attr:`text` (as produced by the pipeline).
        """
        report = ExportReport()
        pkg = self._fresh()
        aliases = assign_aliases(spans, store)
        edits = [(s.start, s.end, aliases[(s.kind, s.key)]) for s in spans]
        report.replaced = pkg.apply_edits(edits)
        pkg.scrub_metadata(report)
        _scan_and_fix(pkg, store, report, fix=True)
        data = pkg.serialize()
        report.parts_changed = sorted(pkg.dirty)

        # Independent verification on the bytes that will be written.
        check = _Package(data)
        verify = ExportReport()
        _scan_and_fix(check, store, verify, fix=False)
        report.leaks = sorted(set(verify.leaks))
        _binary_warnings(check, report)
        return data, report

    def save_anonymized(self, dest: Path, spans: list[EntitySpan], store: MappingStore) -> ExportReport:
        data, report = self.anonymize(spans, store)
        Path(dest).write_bytes(data)
        return report

    def apply_edits(self, edits: list[tuple[int, int, str]]) -> bytes:
        """Apply raw ``(start, end, replacement)`` edits on :attr:`text`."""
        pkg = self._fresh()
        pkg.apply_edits(edits)
        return pkg.serialize()

    def restore(self, store: MappingStore) -> tuple[bytes, int]:
        """Replace aliases with original values everywhere, keeping formatting."""
        pkg = self._fresh()
        edits = restore_replacements(pkg.text, store)
        if not edits:
            return self._data, 0
        count = pkg.apply_edits(edits)
        return pkg.serialize(), count

    def save_restored(self, dest: Path, store: MappingStore) -> int:
        data, count = self.restore(store)
        Path(dest).write_bytes(data)
        return count
