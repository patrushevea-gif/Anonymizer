from anonymizer.core.entities import EntitySpan
from anonymizer.core.mapping import MappingStore


def apply_mask(text: str, spans: list[EntitySpan], store: MappingStore) -> str:
    out = text
    for span in sorted(spans, key=lambda s: s.start, reverse=True):
        alias = store.alias_for(span.kind, span.key, display_original=span.text)
        out = out[: span.start] + alias + out[span.end :]
    return out
