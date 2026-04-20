from anonymizer.core.mapping import MappingStore


def restore(text: str, store: MappingStore) -> str:
    out = text
    for alias in sorted(store.aliases(), key=len, reverse=True):
        original = store.original_for(alias)
        if original is None:
            continue
        out = out.replace(alias, original)
    return out
