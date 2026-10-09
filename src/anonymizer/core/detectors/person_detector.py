"""Rule-based detector of Russian full names (ФИО).

Works alongside the neural NER as a deterministic safety net. It relies on
the OpenCorpora dictionary (bundled with Natasha) which tags given names,
patronymics and surnames, so it recognises every grammatical case:

* ``Фамилия Имя Отчество``     — «Ивановой Марине Петровне»
* ``Имя Отчество Фамилия``     — «Полина Викторовна Лабораторная»
* ``Имя Отчество``             — «Марина Петровна»
* ``Фамилия И.О.`` / ``И.О. Фамилия`` / ``И. О. Фамилия``
* ``Фамилия Имя`` / ``Имя Фамилия`` (both words must be unambiguous)

Names typed in CAPITALS (headings, signature blocks) are handled as well.
Without the dictionary the detector degrades to suffix heuristics that
still catch the most common «Фамилия Имя Отчество» pattern.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from anonymizer.core import morph
from anonymizer.core.entities import EntityKind, EntitySpan

PERSON_PRIORITY = 20

_TOKEN_RE = re.compile(
    r"(?P<init>[А-ЯЁ]\.(?:[  ]?[А-ЯЁ]\.)?)(?![А-ЯЁа-яё])"
    r"|(?P<word>[А-ЯЁ](?:[а-яё]+|[А-ЯЁ]+)(?:-[А-ЯЁ](?:[а-яё]+|[А-ЯЁ]+))?)(?![А-ЯЁа-яё])"
)
# Words are adjacent when separated by plain spaces only (no punctuation,
# no line breaks). Initials may be glued to the surname: «И.И.Иванов».
_GAP_RE = re.compile(r"[   ]{1,3}")

_PATR_FALLBACK = re.compile(
    r"(?:ович|евич|ьич|ична|инична|овна|евна)(?:а|у|ем|е|ом|ой|ы|ну|не|ной)?$"
)
_SURN_FALLBACK = re.compile(
    r"(?:ов|ев|ёв|ин|ын|ский|цкий|ова|ева|ёва|ина|ына|ская|цкая)"
    r"(?:а|у|ым|е|ой|ую|ого|ому|им|ом)?$"
)
_ADJ_SURNAME_END = ("ая", "ий", "ой", "ый", "яя", "ей", "ую", "ому", "ого")

# Capitalised words that start sentences or headings and must never be read
# as part of a name even when the dictionary is unsure about them.
_NEVER_NAME = frozenset({
    "уважаемый", "уважаемая", "уважаемые", "господин", "госпожа", "гражданин",
    "гражданка", "товарищ", "директор", "приказ", "договор", "просим", "прошу",
})


@dataclass
class _Tok:
    start: int
    end: int
    text: str
    initials: bool

    @property
    def low(self) -> str:
        return self.text.lower()


def _tokens(text: str) -> list[_Tok]:
    out: list[_Tok] = []
    for m in _TOKEN_RE.finditer(text):
        out.append(_Tok(m.start(), m.end(), m.group(), m.group("init") is not None))
    return out


def _adjacent(text: str, a: _Tok, b: _Tok) -> bool:
    gap = text[a.end:b.start]
    if gap == "":
        return a.initials and not b.initials
    return _GAP_RE.fullmatch(gap) is not None


class _Classifier:
    def __init__(self) -> None:
        self.has_dict = morph.get_analyzer() is not None

    def name(self, t: _Tok) -> float:
        if t.initials or t.low in _NEVER_NAME:
            return 0.0
        return morph.role_score(t.low, "Name") if self.has_dict else 0.0

    def patr(self, t: _Tok) -> float:
        if t.initials:
            return 0.0
        if self.has_dict:
            return morph.role_score(t.low, "Patr")
        return 1.0 if _PATR_FALLBACK.search(t.low) else 0.0

    def surn(self, t: _Tok) -> float:
        if t.initials or t.low in _NEVER_NAME:
            return 0.0
        if self.has_dict:
            return morph.role_score(t.low, "Surn")
        return 1.0 if _SURN_FALLBACK.search(t.low) else 0.0

    def unknown(self, t: _Tok) -> bool:
        return (
            not t.initials
            and self.has_dict
            and t.low not in _NEVER_NAME
            and not morph.is_known(t.low)
        )

    def surname_like(self, t: _Tok) -> bool:
        return self.surn(t) > 0 or self.unknown(t)

    def adjectival_surname(self, t: _Tok) -> bool:
        if t.initials or t.low in _NEVER_NAME:
            return False
        return t.low.endswith(_ADJ_SURNAME_END)

    def strong_name(self, t: _Tok) -> bool:
        return self.name(t) >= 0.5

    def strong_surn(self, t: _Tok) -> bool:
        return self.surn(t) >= 0.5


class PersonRuleDetector:
    def find(self, text: str) -> list[EntitySpan]:
        toks = _tokens(text)
        if len(toks) < 2:
            return []
        c = _Classifier()
        n = len(toks)
        used = [False] * n
        found: list[tuple[int, int]] = []

        def adj(i: int, j: int) -> bool:
            return 0 <= i < n and 0 <= j < n and _adjacent(text, toks[i], toks[j])

        def free(i: int) -> bool:
            return 0 <= i < n and not used[i]

        def take(s: int, e: int) -> None:
            for k in range(s, e + 1):
                used[k] = True
            found.append((s, e))

        # 1. Имя + Отчество core, extended by an adjacent surname.
        for i in range(n - 1):
            if not (free(i) and free(i + 1) and adj(i, i + 1)):
                continue
            a, b = toks[i], toks[i + 1]
            if a.initials or b.initials:
                continue
            if not c.has_dict:
                continue
            if c.name(a) <= 0 or c.patr(b) <= 0:
                continue
            s, e = i, i + 1
            if free(i - 1) and adj(i - 1, i) and not toks[i - 1].initials:
                prev = toks[i - 1]
                if c.surname_like(prev) and c.patr(prev) == 0:
                    s = i - 1
            if s == i and free(i + 2) and adj(i + 1, i + 2):
                nxt = toks[i + 2]
                if not nxt.initials and (
                    c.surname_like(nxt) or c.adjectival_surname(nxt)
                ) and c.patr(nxt) == 0:
                    e = i + 2
            take(s, e)

        # 1b. Without a dictionary: Фамилия Имя Отчество by suffixes only.
        if not c.has_dict:
            for i in range(n - 2):
                if not (free(i) and free(i + 1) and free(i + 2)):
                    continue
                if not (adj(i, i + 1) and adj(i + 1, i + 2)):
                    continue
                if any(toks[k].initials for k in (i, i + 1, i + 2)):
                    continue
                if c.surn(toks[i]) > 0 and c.patr(toks[i + 2]) > 0:
                    take(i, i + 2)

        # 2. Фамилия + инициалы / инициалы + Фамилия.
        for i in range(n - 1):
            a, b = toks[i], toks[i + 1]
            if not (free(i) and free(i + 1) and adj(i, i + 1)):
                continue
            if a.initials == b.initials:
                continue
            surname = b if a.initials else a
            if c.surname_like(surname) or (not c.has_dict and c.surn(surname) > 0):
                take(i, i + 1)

        # 3. Фамилия + Имя / Имя + Фамилия — both words must be unambiguous.
        if c.has_dict:
            for i in range(n - 1):
                a, b = toks[i], toks[i + 1]
                if not (free(i) and free(i + 1) and adj(i, i + 1)):
                    continue
                if a.initials or b.initials:
                    continue
                if (c.strong_surn(a) and c.strong_name(b) and not c.strong_name(a)) or (
                    c.strong_name(a) and c.strong_surn(b) and not c.strong_name(b)
                ):
                    take(i, i + 1)

        spans: list[EntitySpan] = []
        for s, e in sorted(found):
            start, end = toks[s].start, toks[e].end
            surface = text[start:end]
            spans.append(
                EntitySpan(
                    kind=EntityKind.PERSON,
                    start=start,
                    end=end,
                    text=surface,
                    normalized_key=" ".join(surface.lower().split()),
                    priority=PERSON_PRIORITY,
                )
            )
        return spans
