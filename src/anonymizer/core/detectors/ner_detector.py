import re
from collections import defaultdict
from dataclasses import dataclass

from anonymizer.core.entities import EntityKind, EntitySpan

_NATASHA_TO_KIND = {
    "PER": EntityKind.PERSON,
    "ORG": EntityKind.ORG,
    "LOC": EntityKind.LOCATION,
}

_PRIORITY = {
    EntityKind.PERSON: 20,
    EntityKind.ORG: 15,
    EntityKind.LOCATION: 10,
}

_SURNAME_SUFFIXES = (
    "ов", "ев", "ёв", "ова", "ева", "ёва",
    "ин", "ын", "ина", "ына",
    "ский", "цкий", "ская", "цкая",
    "ой", "ая",
)

_INITIALS_RE = re.compile(r"^\s*([А-ЯЁа-яё])\.\s*([А-ЯЁа-яё])\.?\s*$")
_ADJACENCY_GAP = 3


@dataclass
class _PersonParts:
    first: str = ""
    middle: str = ""
    last: str = ""

    def key(self) -> str:
        return " ".join(p for p in (self.last, self.first, self.middle) if p)

    def has_initials(self) -> bool:
        return len(self.first) == 1 or (0 < len(self.middle) <= 1)


def _looks_like_surname(word: str) -> bool:
    return any(word.endswith(s) for s in _SURNAME_SUFFIXES)


class NatashaDetector:
    def __init__(self) -> None:
        self._segmenter = None
        self._morph_vocab = None
        self._morph_tagger = None
        self._ner_tagger = None
        self._names_extractor = None
        self._doc_cls = None

    def _ensure_loaded(self) -> None:
        if self._segmenter is not None:
            return
        from natasha import (
            Doc,
            MorphVocab,
            NamesExtractor,
            NewsEmbedding,
            NewsMorphTagger,
            NewsNERTagger,
            Segmenter,
        )

        emb = NewsEmbedding()
        self._segmenter = Segmenter()
        self._morph_vocab = MorphVocab()
        self._morph_tagger = NewsMorphTagger(emb)
        self._ner_tagger = NewsNERTagger(emb)
        self._names_extractor = NamesExtractor(self._morph_vocab)
        self._doc_cls = Doc

    def find(self, text: str) -> list[EntitySpan]:
        if not text.strip():
            return []
        self._ensure_loaded()
        doc = self._doc_cls(text)
        doc.segment(self._segmenter)
        doc.tag_morph(self._morph_tagger)
        for token in doc.tokens:
            token.lemmatize(self._morph_vocab)
        doc.tag_ner(self._ner_tagger)

        person_entries: list[list] = []
        other_entries: list[tuple[object, EntityKind]] = []

        for raw in doc.spans:
            kind = _NATASHA_TO_KIND.get(raw.type)
            if kind is None:
                continue
            raw.normalize(self._morph_vocab)
            if kind is EntityKind.PERSON:
                parts = self._fixup_parts(self._person_parts(raw), raw.text)
                person_entries.append([raw, parts])
            else:
                other_entries.append((raw, kind))

        self._apply_adjacency(person_entries)
        person_keys = self._consolidate_persons(person_entries)

        spans: list[EntitySpan] = []
        for (raw, parts), key in zip(person_entries, person_keys, strict=True):
            spans.append(
                EntitySpan(
                    kind=EntityKind.PERSON,
                    start=raw.start,
                    end=raw.stop,
                    text=raw.text,
                    normalized_key=key or parts.key() or raw.normal or raw.text.lower(),
                    priority=_PRIORITY[EntityKind.PERSON],
                )
            )

        for raw, kind in other_entries:
            spans.append(
                EntitySpan(
                    kind=kind,
                    start=raw.start,
                    end=raw.stop,
                    text=raw.text,
                    normalized_key=(raw.normal or raw.text).lower(),
                    priority=_PRIORITY[kind],
                )
            )
        return spans

    def _person_parts(self, raw_span) -> _PersonParts:
        try:
            raw_span.extract_fact(self._names_extractor)
        except Exception:
            return _PersonParts()
        fact = raw_span.fact
        if fact is None:
            return _PersonParts()
        data = fact.as_dict
        return _PersonParts(
            first=(data.get("first") or "").strip().lower(),
            middle=(data.get("middle") or "").strip().lower(),
            last=(data.get("last") or "").strip().lower(),
        )

    @staticmethod
    def _fixup_parts(parts: _PersonParts, surface: str) -> _PersonParts:
        first, middle, last = parts.first, parts.middle, parts.last

        if first and not last and not middle and _looks_like_surname(first):
            last, first = first, ""

        if len(last) == 1 and not first and not middle:
            first, last = last, ""

        match = _INITIALS_RE.match(surface)
        if match and (not first or len(first) <= 1) and (not middle or len(middle) <= 1):
            f, m = match.group(1).lower(), match.group(2).lower()
            if len(first) <= 1:
                first = f
            if len(middle) <= 1:
                middle = m

        return _PersonParts(first=first, middle=middle, last=last)

    @staticmethod
    def _apply_adjacency(entries: list[list]) -> None:
        if len(entries) < 2:
            return
        for i in range(len(entries) - 1):
            raw_a, parts_a = entries[i]
            raw_b, parts_b = entries[i + 1]
            if raw_b.start - raw_a.stop > _ADJACENCY_GAP:
                continue
            merged = _PersonParts(
                first=parts_a.first or parts_b.first,
                middle=parts_a.middle or parts_b.middle,
                last=parts_a.last or parts_b.last,
            )
            entries[i][1] = merged
            entries[i + 1][1] = merged

    def _consolidate_persons(self, entries: list[list]) -> list[str]:
        base_keys = [parts.key() for _, parts in entries]
        resolved = list(base_keys)

        by_last: dict[str, list[int]] = defaultdict(list)
        for idx, (_, parts) in enumerate(entries):
            if parts.last:
                by_last[parts.last].append(idx)

        for indices in by_last.values():
            full_indices = [i for i in indices if not entries[i][1].has_initials()]
            for i in indices:
                parts = entries[i][1]
                if not parts.has_initials():
                    continue
                matched_keys = {
                    base_keys[j]
                    for j in full_indices
                    if self._initial_matches(parts, entries[j][1])
                }
                if len(matched_keys) == 1:
                    resolved[i] = next(iter(matched_keys))

        for i, (_, parts) in enumerate(entries):
            if parts.last and not parts.first and not parts.middle:
                matches = {
                    base_keys[j]
                    for j in by_last[parts.last]
                    if not entries[j][1].has_initials() and entries[j][1].first
                }
                if len(matches) == 1:
                    resolved[i] = next(iter(matches))

        return resolved

    @staticmethod
    def _initial_matches(initial: _PersonParts, full: _PersonParts) -> bool:
        if initial.last and initial.last != full.last:
            return False
        if initial.first and (not full.first or not full.first.startswith(initial.first)):
            return False
        middle_ok = (
            not initial.middle
            or (full.middle is not None and full.middle.startswith(initial.middle))
        )
        return bool(middle_ok)
