"""Span post-processing shared by the pipeline and the GUI.

The steps turn raw detector output into the final, consistent set of
entities:

1. ``clean_spans``      — drop known false positives (file formats, software
                          vendors, CAPS headings), honour the user allowlist,
                          repair organisation names cut before the closing
                          quote.
2. ``resolve_overlaps`` — one entity per character range.
3. ``merge_adjacent_persons`` — «Никитина» + «Алина Валерьевна» → one ФИО.
4. ``link_persons``     — one canonical key per real person.
5. ``propagate``        — every surface form that was recognised once is
                          masked everywhere in the document (header, footer,
                          comment, table…), including inflected surnames.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import replace

from anonymizer.core import morph
from anonymizer.core.entities import EntityKind, EntitySpan
from anonymizer.core.persons import link_persons, surname_lemma_of_key
from anonymizer.core.resolve import IntervalSet, resolve_overlaps

# Public products, vendors, file formats and acronyms that NER models like
# to tag as organisations. None of them is confidential.
BUILTIN_STOPLIST: frozenset[str] = frozenset(
    s.casefold()
    for s in (
        "DOCX", "DOC", "DOCM", "DOTX", "XLSX", "XLS", "XLSM", "CSV", "PDF", "TXT", "RTF", "ODT",
        "XML", "JSON", "HTML", "ZIP", "RAR", "PNG", "JPG", "JPEG",
        "IP", "API", "URL", "URI", "HTTP", "HTTPS", "SQL", "VPN", "SSL", "TLS", "DNS", "QA",
        "ИИ", "ИТ", "IT", "AI", "ПО", "ОС", "ЭЦП", "PDF/A",
        "Word", "Excel", "PowerPoint", "Outlook", "Teams", "SharePoint", "OneDrive",
        "Microsoft", "Microsoft Word", "Microsoft Excel", "Microsoft Office", "Office",
        "Microsoft Teams", "Windows", "Linux", "macOS", "Android", "iOS",
        "Google", "Google Docs", "Apple", "Adobe", "Adobe Acrobat", "Acrobat",
        "OpenAI", "ChatGPT", "GPT", "Claude", "Anthropic", "GigaChat", "ГигаЧат",
        "YandexGPT", "DeepSeek", "Gemini", "Copilot",
        "GitHub", "Telegram", "WhatsApp", "Viber", "Skype", "Zoom",
        "1С", "1C", "SAP", "Oracle", "IBM", "Intel", "AMD", "Nvidia",
        "Россия", "РФ", "Российская Федерация",
        "ANONYMIZER", "ANONYMIZER ROSSILBER",
    )
)

_NER_KINDS = {EntityKind.ORG, EntityKind.LOCATION, EntityKind.PERSON}
_QUOTES = {"«": "»", "„": "“", "“": "”", '"': '"'}


def _norm_term(s: str) -> str:
    s = s.strip(" \t.,;:«»\"'()“”„")
    return " ".join(s.casefold().replace("ё", "е").split())


def _allowed(term: str, kind: EntityKind, allowed: set[str]) -> bool:
    if term in allowed:
        return True
    # «Россильбер» in the allowlist also keeps «ООО «Россильбер»».
    if kind in (EntityKind.ORG, EntityKind.LOCATION, EntityKind.URL, EntityKind.EMAIL):
        return any(
            re.search(rf"(?<!\w){re.escape(a)}(?!\w)", term) for a in allowed
        )
    return False


def clean_spans(
    spans: list[EntitySpan], text: str, allowlist: Iterable[str] = ()
) -> list[EntitySpan]:
    allowed = {_norm_term(a) for a in allowlist if a and a.strip()}
    stop = {_norm_term(s) for s in BUILTIN_STOPLIST}
    out: list[EntitySpan] = []
    for span in spans:
        term = _norm_term(span.text)
        if allowed and _allowed(term, span.kind, allowed):
            continue
        if span.kind in _NER_KINDS and span.priority < 1000:
            if term in stop:
                continue
            if span.kind is EntityKind.ORG and _is_junk_org(span.text):
                continue
            if span.kind is EntityKind.ORG:
                span = _balance_quotes(span, text)
        out.append(span)
    return out


def _is_junk_org(surface: str) -> bool:
    words = surface.split()
    if len(words) != 1:
        return False
    word = words[0].strip("«»\"'.,")
    if len(word) <= 2:
        return True  # «NO», «ИП», «ЦБ» alone are never a confidential company name
    letters = [c for c in word if c.isalpha()]
    if not letters or not all(c.isupper() for c in letters):
        return False
    if all("a" <= c.lower() <= "z" for c in letters):
        return False  # Latin acronyms are handled by the stoplist only.
    # A CAPS common Russian word («КОММЕНТАРИЯ», «ВАЖНО») is a heading, not a company.
    if morph.get_analyzer() is None:
        return False
    tags = morph.parses(word)
    if not tags or not morph.is_known(word):
        return False
    return not any({"Orgn", "Abbr", "Geox", "Surn", "Name"} & t for t, _, _ in tags)


def _balance_quotes(span: EntitySpan, text: str) -> EntitySpan:
    start, end = span.start, span.end
    for opening, closing in _QUOTES.items():
        inner = text[start:end]
        if opening == closing:
            unbalanced = inner.count(opening) % 2 == 1
        else:
            unbalanced = inner.count(opening) > inner.count(closing)
        if not unbalanced:
            continue
        tail = text[end:end + 120].split("\n", 1)[0]
        pos = tail.find(closing)
        if pos != -1:
            end = end + pos + 1
    if end == span.end:
        return span
    surface = text[start:end]
    return replace(span, end=end, text=surface, normalized_key=" ".join(surface.lower().split()))


def merge_adjacent_persons(spans: list[EntitySpan], text: str) -> list[EntitySpan]:
    """Glue PERSON spans separated only by spaces into one span."""
    out: list[EntitySpan] = []
    for span in sorted(spans, key=lambda s: s.start):
        if (
            out
            and span.kind is EntityKind.PERSON
            and out[-1].kind is EntityKind.PERSON
            and re.fullmatch(r"[  ]{1,2}", text[out[-1].end:span.start] or "x")
        ):
            prev = out[-1]
            surface = text[prev.start:span.end]
            out[-1] = replace(
                prev, end=span.end, text=surface,
                normalized_key=" ".join(surface.lower().split()),
                priority=max(prev.priority, span.priority),
            )
            continue
        out.append(span)
    return out


_MIN_PROPAGATE = 3


def _ws(s: str) -> str:
    return " ".join(s.split())


def surfaces_regex(surfaces: Iterable[str]) -> re.Pattern[str] | None:
    """One regex matching any of *surfaces* as a whole word, longest first.

    Whitespace inside a value matches any run of spaces / NBSP / line breaks
    so a name wrapped onto the next line is still found.
    """
    alts = []
    for surface in sorted({_ws(s) for s in surfaces if s.strip()}, key=len, reverse=True):
        alts.append(r"\s+".join(re.escape(p) for p in surface.split()))
    if not alts:
        return None
    return re.compile(r"(?<![\w])(?:" + "|".join(alts) + r")(?![\w])")


def propagate(spans: list[EntitySpan], text: str) -> list[EntitySpan]:
    """Mask every other occurrence of each recognised value.

    A value found once (in a table, by a validator, by NER, by a manual
    marking) is a confirmed secret: leaving its other occurrences in the
    header, a comment or another paragraph would be a leak.
    """
    if not spans:
        return spans
    intervals = IntervalSet()
    for s in spans:
        intervals.add(s.start, s.end)
    added: list[EntitySpan] = []

    seen: dict[str, EntitySpan] = {}
    for span in sorted(spans, key=lambda s: -s.priority):
        surface = _ws(span.text.strip())
        if sum(ch.isalnum() for ch in surface) < _MIN_PROPAGATE:
            continue
        seen.setdefault(surface, span)

    pattern = surfaces_regex(seen)
    if pattern is not None:
        for m in pattern.finditer(text):
            if intervals.overlaps(m.start(), m.end()):
                continue
            model = seen.get(_ws(m.group()))
            if model is None:
                continue
            intervals.add(m.start(), m.end())
            added.append(
                replace(model, start=m.start(), end=m.end(), text=m.group(),
                        priority=max(model.priority - 1, 0))
            )

    added.extend(_propagate_surnames(spans, text, intervals))
    return sorted(list(spans) + added, key=lambda s: s.start)


_CAP_WORD = re.compile(r"(?<![\w])[А-ЯЁ][а-яё]{2,}(?:-[А-ЯЁ][а-яё]+)?(?![\w])")


def _propagate_surnames(
    spans: list[EntitySpan], text: str, intervals: IntervalSet
) -> list[EntitySpan]:
    """Catch stand-alone inflected surnames of people already found.

    «Иванов Иван Иванович» found in the body → «Иванову» in a comment is
    masked as well and linked to the same person.
    """
    if morph.get_analyzer() is None:
        return []
    lemmas: dict[str, EntitySpan] = {}
    for s in spans:
        if s.kind is EntityKind.PERSON and s.key.startswith("person:"):
            lemma = surname_lemma_of_key(s.key)
            if len(lemma) >= 4:
                lemmas.setdefault(lemma, s)
    if not lemmas:
        return []
    out: list[EntitySpan] = []
    for m in _CAP_WORD.finditer(text):
        if intervals.overlaps(m.start(), m.end()):
            continue
        lemma = morph.lemma_for(m.group(), "Surn")
        if not lemma:
            continue
        lemma = lemma.lower().replace("ё", "е")
        model = lemmas.get(lemma)
        if model is None:
            continue
        intervals.add(m.start(), m.end())
        out.append(
            replace(model, start=m.start(), end=m.end(), text=m.group(),
                    normalized_key=m.group().lower(), priority=max(model.priority - 1, 0))
        )
    return out


def finalize_spans(
    spans: list[EntitySpan], text: str, allowlist: Iterable[str] = ()
) -> list[EntitySpan]:
    """Full post-processing chain: clean → resolve → merge → link → propagate."""
    cleaned = clean_spans(spans, text, allowlist)
    resolved = resolve_overlaps(cleaned)
    merged = merge_adjacent_persons(resolved, text)
    linked = link_persons(merged)
    propagated = propagate(linked, text)
    return link_persons(propagated)
