import re
from collections import defaultdict

from anonymizer.core.entities import EntityKind


class MappingStore:
    def __init__(self) -> None:
        self._counters: dict[EntityKind, int] = defaultdict(int)
        self._key_to_alias: dict[tuple[EntityKind, str], str] = {}
        self._alias_to_original: dict[str, tuple[EntityKind, str]] = {}
        self._reserved_aliases: set[str] = set()

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
        self._alias_to_original[alias] = (kind, display_original if display_original is not None else key)
        return alias

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

    def __len__(self) -> int:
        return len(self._alias_to_original)
