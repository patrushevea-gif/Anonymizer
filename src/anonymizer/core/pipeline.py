from collections import Counter
from dataclasses import dataclass, field

from anonymizer.core.detectors.base import Detector
from anonymizer.core.detectors.ner_detector import NatashaDetector
from anonymizer.core.detectors.regex_detector import RegexDetector
from anonymizer.core.entities import EntityKind, EntitySpan
from anonymizer.core.mapping import MappingStore
from anonymizer.core.masking import apply_mask
from anonymizer.core.resolve import resolve_overlaps


@dataclass
class AnonymizationResult:
    masked_text: str
    spans: list[EntitySpan] = field(default_factory=list)
    counts: Counter[EntityKind] = field(default_factory=Counter)


@dataclass
class Pipeline:
    detectors: list[Detector] = field(default_factory=list)

    @classmethod
    def default(cls, *, use_ner: bool = True) -> "Pipeline":
        detectors: list[Detector] = [RegexDetector()]
        if use_ner:
            detectors.append(NatashaDetector())
        return cls(detectors=detectors)

    def run(self, text: str, store: MappingStore) -> AnonymizationResult:
        if not text:
            return AnonymizationResult(masked_text=text)

        store.reserve_source_aliases(text)

        raw: list[EntitySpan] = []
        for detector in self.detectors:
            raw.extend(detector.find(text))

        resolved = resolve_overlaps(raw)
        masked = apply_mask(text, resolved, store)
        counts = Counter(span.kind for span in resolved)
        return AnonymizationResult(masked_text=masked, spans=resolved, counts=counts)


def anonymize(text: str, store: MappingStore, *, use_ner: bool = True) -> AnonymizationResult:
    return Pipeline.default(use_ner=use_ner).run(text, store)
