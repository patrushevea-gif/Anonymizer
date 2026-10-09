"""Person linking: one canonical key per real person, whatever the form.

Every PERSON span, whichever detector produced it, is decomposed into
surname / first name / patronymic (or initials) and lemmatised, so that
«Иванов Иван Иванович», «Иванову Ивану Ивановичу» and «Иванов И.И.» share a
key — and therefore a single alias — while «Ивановой Марине Петровне» and
«Ивановой Марии Петровне» stay two different people.

Partial mentions (initials, surname only, «Имя Отчество») are attached to a
full name only when exactly one compatible full name exists in the text.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, replace

from anonymizer.core import morph
from anonymizer.core.entities import EntityKind, EntitySpan

_WORD_RE = re.compile(r"[А-ЯЁа-яё]+(?:-[А-ЯЁа-яё]+)*")
_INITIAL_RE = re.compile(r"(?<![А-ЯЁа-яё])([А-ЯЁ])\.")
_SURNAME_ENDINGS = re.compile(
    r"(?:ов|ев|ёв|ин|ын)(?:а|у|ым|е|ой|у|ою|ых|ы)?$|(?:ск|цк)(?:ий|ая|ого|ому|им|ом|ой|ую)$"
)


@dataclass(frozen=True)
class PersonParts:
    last: str = ""
    first: str = ""
    middle: str = ""
    gender: str = ""  # "masc" / "femn" / ""
    surname_genders: frozenset[str] = frozenset()

    def key(self) -> str:
        return " ".join(p for p in (self.last, self.first, self.middle) if p)

    @property
    def has_initials(self) -> bool:
        return len(self.first) == 1 or len(self.middle) == 1

    @property
    def is_full(self) -> bool:
        return bool(self.last and self.first and len(self.first) > 1)


def _norm(s: str) -> str:
    return s.lower().replace("ё", "е")


def _gender_of(word: str, grammeme: str) -> str:
    best = None
    for tags, _, score in morph.parses(word):
        if grammeme in tags and (best is None or score > best[0]):
            g = "femn" if "femn" in tags else "masc" if "masc" in tags else ""
            best = (score, g)
    return best[1] if best else ""


def _surname_genders(word: str) -> frozenset[str]:
    out = set()
    for tags, _, _ in morph.parses(word):
        if "Surn" in tags:
            if "femn" in tags:
                out.add("femn")
            if "masc" in tags:
                out.add("masc")
    return frozenset(out)


def _surname_lemma(word: str) -> str:
    lemma = morph.lemma_for(word, "Surn")
    if lemma:
        return _norm(lemma)
    p = morph.parses(word)
    if p:
        return _norm(p[0][1])
    # No dictionary: strip common case endings so «Иванову»/«Иванов» match.
    w = _norm(word)
    m = re.match(r"^(.+?(?:ов|ев|ин|ын))(?:а|у|ым|е|ой|ою|ых|ы)?$", w)
    return m.group(1) if m else w


def parse_person(text: str) -> PersonParts:
    initials = _INITIAL_RE.findall(text)
    # Remove initials so they aren't mistaken for one-letter words.
    rest = _INITIAL_RE.sub(" ", text)
    words = _WORD_RE.findall(rest)
    has_dict = morph.get_analyzer() is not None

    first = middle = last = ""
    gender = ""
    remaining = list(words)

    if has_dict and remaining:
        scored = [
            (w, morph.role_score(w, "Name"), morph.role_score(w, "Patr"), morph.role_score(w, "Surn"))
            for w in remaining
        ]
        patr = max(scored, key=lambda t: t[2])
        if patr[2] > 0.3 and len(remaining) > 1:
            middle = _norm(morph.lemma_for(patr[0], "Patr") or patr[0])
            gender = _gender_of(patr[0], "Patr")
            remaining.remove(patr[0])
            scored = [t for t in scored if t[0] is not patr[0]]
        if remaining and not initials:
            name_cands = [t for t in scored if t[1] > 0]
            if name_cands and (len(remaining) > 1 or middle or name_cands[0][1] > name_cands[0][3]):
                # Prefer the word that is most "name-like" relative to surname-likeness.
                best = max(name_cands, key=lambda t: t[1] - t[3])
                first = _norm(morph.lemma_for(best[0], "Name") or best[0])
                gender = gender or _gender_of(best[0], "Name")
                remaining.remove(best[0])
    elif not has_dict and remaining:
        # Heuristic order: Фамилия Имя Отчество.
        if len(remaining) == 3:
            last_w, first_w, middle_w = remaining
            remaining = [last_w]
            first, middle = _norm(first_w), _norm(middle_w)

    surname_genders: frozenset[str] = frozenset()
    if remaining:
        last_word = remaining[0]
        last = _surname_lemma(last_word) if not (len(remaining) > 1) else " ".join(
            _surname_lemma(w) for w in remaining
        )
        surname_genders = _surname_genders(last_word) if has_dict else frozenset()

    if initials:
        if not first:
            first = _norm(initials[0])
        if len(initials) > 1 and not middle:
            middle = _norm(initials[1])

    return PersonParts(
        last=last, first=first, middle=middle, gender=gender, surname_genders=surname_genders
    )


def _initials_match(part: PersonParts, full: PersonParts) -> bool:
    if part.last and part.last != full.last:
        return False
    if part.first and not full.first.startswith(part.first):
        return False
    return not (part.middle and not full.middle.startswith(part.middle))


def link_persons(spans: list[EntitySpan]) -> list[EntitySpan]:
    """Return *spans* with PERSON ``normalized_key`` values canonicalised."""
    idx = [i for i, s in enumerate(spans) if s.kind is EntityKind.PERSON]
    if not idx:
        return spans
    parts = {i: parse_person(spans[i].text) for i in idx}

    fulls: dict[str, PersonParts] = {}
    for i in idx:
        p = parts[i]
        if p.is_full and not p.has_initials:
            fulls.setdefault(p.key(), p)
    by_last: dict[str, list[PersonParts]] = defaultdict(list)
    for p in fulls.values():
        by_last[p.last].append(p)

    def resolve(p: PersonParts) -> str:
        if p.is_full and not p.has_initials:
            return p.key()
        candidates: list[PersonParts]
        if p.last and p.has_initials:
            candidates = [f for f in by_last.get(p.last, []) if _initials_match(p, f)]
        elif p.last and not p.first and not p.middle:
            candidates = list(by_last.get(p.last, []))
            if p.surname_genders and len(candidates) > 1:
                narrowed = [f for f in candidates if not f.gender or f.gender in p.surname_genders]
                candidates = narrowed or candidates
        elif not p.last and p.first:
            # «Имя Отчество» links to a unique full name; a lone first name
            # is too weak a signal and keeps its own alias.
            candidates = [
                f for f in fulls.values()
                if p.middle and f.first == p.first and f.middle == p.middle
            ]
        else:
            candidates = []
        unique = {c.key() for c in candidates}
        if len(unique) == 1:
            return next(iter(unique))
        return p.key() or " ".join(_norm(w) for w in _WORD_RE.findall(p.key()))

    out = list(spans)
    for i in idx:
        key = resolve(parts[i]) or _norm(" ".join(spans[i].text.split()))
        out[i] = replace(spans[i], normalized_key="person:" + key)
    return out


def surname_lemma_of_key(key: str) -> str:
    """Surname component of a canonical key produced by :func:`link_persons`."""
    body = key.removeprefix("person:")
    return body.split(" ")[0] if body else ""


def preferred_display(texts: list[str]) -> str:
    """Pick the most informative surface form for restoring a person alias.

    Prefers a complete name without initials in the nominative case, so the
    restored text reads «Иванова Марина Петровна» rather than the dative form
    that happened to appear first in the document.
    """
    def score(t: str) -> tuple[int, int, int, int]:
        words = _WORD_RE.findall(_INITIAL_RE.sub(" ", t))
        has_init = bool(_INITIAL_RE.search(t))
        nominative = all(morph.is_nominative(w) for w in words) if words else False
        return (int(not has_init), len(words), int(nominative), -texts.index(t))

    return max(texts, key=score)


def looks_like_surname(word: str) -> bool:
    if morph.get_analyzer() is not None:
        return morph.role_score(word, "Surn") > 0
    return bool(_SURNAME_ENDINGS.search(_norm(word)))
