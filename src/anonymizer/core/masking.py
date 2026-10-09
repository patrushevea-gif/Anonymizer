from collections import defaultdict

from anonymizer.core.entities import EntityKind, EntitySpan
from anonymizer.core.mapping import MappingStore
from anonymizer.core.persons import preferred_display


def assign_aliases(spans: list[EntitySpan], store: MappingStore) -> dict[tuple, str]:
    """Create aliases in reading order and return ``(kind, key) -> alias``.

    Numbering follows the document: the first person mentioned is ФИО1.
    For people the restore form is the most complete nominative variant,
    so «ФИО2» is restored as «Иванова Марина Петровна» rather than the
    dative «Ивановой Марине Петровне» that happened to come first.
    """
    ordered = sorted(spans, key=lambda s: s.start)
    texts: dict[tuple, list[str]] = defaultdict(list)
    for span in ordered:
        bucket = texts[(span.kind, span.key)]
        if span.text not in bucket:
            bucket.append(span.text)

    aliases: dict[tuple, str] = {}
    for span in ordered:
        sig = (span.kind, span.key)
        if sig in aliases:
            continue
        variants = texts[sig]
        display = (
            preferred_display(variants) if span.kind is EntityKind.PERSON else variants[0]
        )
        alias = store.alias_for(span.kind, span.key, display_original=display)
        for v in variants:
            store.add_variant(alias, v)
        aliases[sig] = alias
    occurrences: dict[str, list[str]] = defaultdict(list)
    for span in ordered:
        occurrences[aliases[(span.kind, span.key)]].append(span.text)
    store.set_occurrences(occurrences)
    return aliases


def apply_mask(text: str, spans: list[EntitySpan], store: MappingStore) -> str:
    aliases = assign_aliases(spans, store)
    out: list[str] = []
    pos = 0
    for span in sorted(spans, key=lambda s: s.start):
        if span.start < pos:
            continue
        out.append(text[pos:span.start])
        out.append(aliases[(span.kind, span.key)])
        pos = span.end
    out.append(text[pos:])
    return "".join(out)
