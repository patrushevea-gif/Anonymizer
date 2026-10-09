import re
from collections import defaultdict

from anonymizer.core.entities import EntityKind


class MappingStore:
    def __init__(self) -> None:
        self._counters: dict[EntityKind, int] = defaultdict(int)
        self._key_to_alias: dict[tuple[EntityKind, str], str] = {}
        self._alias_to_original: dict[str, tuple[EntityKind, str]] = {}
        self._reserved_aliases: set[str] = set()
        # Every surface form ever masked with an alias (for leak control).
        self._variants: dict[str, list[str]] = {}
        # Original surface of every masked occurrence, in document order.
        # Lets an unchanged text be restored character-for-character even when
        # several forms («Иванов И.И.», «Иванову Ивану Ивановичу») share one alias.
        self._occurrences: dict[str, list[str]] = {}

    def reserve_source_aliases(self, text: str) -> None:
        kinds = "|".join(re.escape(k.value) for k in EntityKind)
        for match in re.finditer(rf"(?:{kinds})\d+", text):
            self._reserved_aliases.add(match.group())

    def alias_for(
        self,
        kind: EntityKind,
        key: str,
        display_original: str | None = None,
    ) -> str:
        map_key = (kind, key)
        existing = self._key_to_alias.get(map_key)
        if existing is not None:
            return existing

        alias = self._next_free_alias(kind)
        self._key_to_alias[map_key] = alias
        original = display_original if display_original is not None else key
        self._alias_to_original[alias] = (kind, original)
        self.add_variant(alias, original)
        return alias

    def add_variant(self, alias: str, surface: str) -> None:
        bucket = self._variants.setdefault(alias, [])
        if surface and surface not in bucket:
            bucket.append(surface)

    def variants(self, alias: str) -> list[str]:
        return list(self._variants.get(alias, []))

    def set_occurrences(self, occurrences: dict[str, list[str]]) -> None:
        self._occurrences = {a: list(v) for a, v in occurrences.items()}

    def occurrences(self, alias: str) -> list[str]:
        return list(self._occurrences.get(alias, []))

    def occurrence_items(self) -> dict[str, list[str]]:
        return {a: list(v) for a, v in self._occurrences.items()}

    def all_variants(self) -> list[tuple[str, str]]:
        """``(surface, alias)`` for every masked surface form."""
        return [(v, a) for a, vs in self._variants.items() for v in vs]

    def _next_free_alias(self, kind: EntityKind) -> str:
        while True:
            self._counters[kind] += 1
            candidate = f"{kind.value}{self._counters[kind]}"
            if candidate not in self._reserved_aliases and candidate not in self._alias_to_original:
                return candidate

    def original_for(self, alias: str) -> str | None:
        entry = self._alias_to_original.get(alias)
        return entry[1] if entry else None

    def aliases(self) -> list[str]:
        return list(self._alias_to_original.keys())

    def items(self) -> list[tuple[str, EntityKind, str]]:
        return [(alias, kind, original) for alias, (kind, original) in self._alias_to_original.items()]

    def load(
        self,
        items: list[tuple[str, EntityKind, str]],
        occurrences: dict[str, list[str]] | None = None,
    ) -> None:
        """Restore mappings from a saved project. Clears existing state first."""
        self._counters.clear()
        self._key_to_alias.clear()
        self._alias_to_original.clear()
        self._reserved_aliases.clear()
        self._variants.clear()
        self._occurrences = {a: list(v) for a, v in (occurrences or {}).items()}
        for alias, kind, original in items:
            self._alias_to_original[alias] = (kind, original)
            self.add_variant(alias, original)
            self._key_to_alias[(kind, original)] = alias
            # Keep the per-kind counter ahead of the highest numeric suffix we've seen
            # so newly-added aliases don't collide with restored ones.
            suffix = alias[len(kind.value):]
            if suffix.isdigit():
                self._counters[kind] = max(self._counters[kind], int(suffix))

    def drop_alias(self, alias: str) -> None:
        """Remove a single mapping. Used when the user unchecks an entity."""
        entry = self._alias_to_original.pop(alias, None)
        self._variants.pop(alias, None)
        self._occurrences.pop(alias, None)
        if entry is not None:
            kind, _ = entry
            key_to_drop = next(
                (k for k, a in self._key_to_alias.items() if a == alias and k[0] == kind),
                None,
            )
            if key_to_drop is not None:
                del self._key_to_alias[key_to_drop]

    def __len__(self) -> int:
        return len(self._alias_to_original)
