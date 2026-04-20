from collections import defaultdict

from anonymizer.core.entities import EntityKind


class MappingStore:
    def __init__(self) -> None:
        self._counters: dict[EntityKind, int] = defaultdict(int)
        self._original_to_alias: dict[tuple[EntityKind, str], str] = {}
        self._alias_to_original: dict[str, tuple[EntityKind, str]] = {}

    def alias_for(self, kind: EntityKind, original: str) -> str:
        key = (kind, original)
        existing = self._original_to_alias.get(key)
        if existing is not None:
            return existing
        self._counters[kind] += 1
        alias = f"{kind.value}{self._counters[kind]}"
        self._original_to_alias[key] = alias
        self._alias_to_original[alias] = key
        return alias

    def original_for(self, alias: str) -> str | None:
        entry = self._alias_to_original.get(alias)
        return entry[1] if entry else None

    def aliases(self) -> list[str]:
        return list(self._alias_to_original.keys())

    def __len__(self) -> int:
        return len(self._alias_to_original)
