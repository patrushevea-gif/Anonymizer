from dataclasses import dataclass, field

from anonymizer.core.entities import EntitySpan
from anonymizer.core.mapping import MappingStore
from anonymizer.core.masking import apply_mask


@dataclass
class AnonymizationResult:
    masked_text: str
    spans: list[EntitySpan] = field(default_factory=list)


def anonymize(text: str, store: MappingStore) -> AnonymizationResult:
    spans: list[EntitySpan] = []
    masked = apply_mask(text, spans, store)
    return AnonymizationResult(masked_text=masked, spans=spans)
