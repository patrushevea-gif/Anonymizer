import re

from anonymizer.core.mapping import MappingStore


def alias_pattern(store: MappingStore) -> re.Pattern[str] | None:
    """One regex matching every alias of *store* as a whole token.

    Longest aliases come first and a trailing digit is forbidden, so «ФИО1»
    never matches inside «ФИО12».
    """
    aliases = sorted(store.aliases(), key=len, reverse=True)
    if not aliases:
        return None
    alt = "|".join(re.escape(a) for a in aliases)
    return re.compile(rf"(?<![\w])(?:{alt})(?!\d)")


def restore_replacements(text: str, store: MappingStore) -> list[tuple[int, int, str]]:
    """``(start, end, original)`` for every alias occurrence in *text*.

    When an alias occurs exactly as many times as it was produced, each
    occurrence gets back its own original form — an unchanged document is
    restored character-for-character («Иванов И.И.» stays «Иванов И.И.»).
    Otherwise (an AI answer that rephrased the text) every occurrence gets
    the canonical, most complete form of the value.
    """
    pattern = alias_pattern(store)
    if pattern is None:
        return []
    matches = list(pattern.finditer(text))
    counts: dict[str, int] = {}
    for m in matches:
        counts[m.group()] = counts.get(m.group(), 0) + 1
    seen: dict[str, int] = {}
    out: list[tuple[int, int, str]] = []
    for m in matches:
        alias = m.group()
        original = store.original_for(alias)
        if original is None:
            continue
        occ = store.occurrences(alias)
        if occ and len(occ) == counts[alias]:
            i = seen.get(alias, 0)
            seen[alias] = i + 1
            original = occ[i]
        out.append((m.start(), m.end(), original))
    return out


def restore(text: str, store: MappingStore) -> str:
    # Single pass: a restored value is never re-scanned, so an original that
    # itself looks like an alias cannot be corrupted.
    parts: list[str] = []
    pos = 0
    for start, end, original in restore_replacements(text, store):
        parts.append(text[pos:start])
        parts.append(original)
        pos = end
    parts.append(text[pos:])
    return "".join(parts)
