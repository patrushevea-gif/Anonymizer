import logging
from collections import Counter
from dataclasses import dataclass, field

from anonymizer.core.detectors.base import Detector
from anonymizer.core.detectors.ner_detector import NatashaDetector
from anonymizer.core.detectors.regex_detector import RegexDetector
from anonymizer.core.entities import EntityKind, EntitySpan
from anonymizer.core.mapping import MappingStore
from anonymizer.core.masking import apply_mask
from anonymizer.core.resolve import resolve_overlaps

_log = logging.getLogger(__name__)


@dataclass
class AnonymizationResult:
    masked_text: str
    spans: list[EntitySpan] = field(default_factory=list)
    counts: Counter[EntityKind] = field(default_factory=Counter)


@dataclass
class Pipeline:
    detectors: list[Detector] = field(default_factory=list)

    @classmethod
    def default(
        cls,
        *,
        use_ner: bool = True,
        ner_detector: NatashaDetector | None = None,
    ) -> "Pipeline":
        detectors: list[Detector] = [RegexDetector()]
        if use_ner:
            detectors.append(ner_detector or NatashaDetector())
        return cls(detectors=detectors)

    def run(self, text: str, store: MappingStore) -> AnonymizationResult:
        if not text:
            return AnonymizationResult(masked_text=text)

        _log.info("Pipeline.run: text len=%d, detectors=%d", len(text), len(self.detectors))
        store.reserve_source_aliases(text)

        raw: list[EntitySpan] = []
        for detector in self.detectors:
            cls_name = type(detector).__name__
            _log.info("  running %s…", cls_name)
            found = detector.find(text)
            _log.info("  %s returned %d spans", cls_name, len(found))
            raw.extend(found)

        _log.info("  resolve_overlaps over %d raw spans…", len(raw))
        resolved = resolve_overlaps(raw)
        _log.info("  apply_mask over %d resolved spans…", len(resolved))
        masked = apply_mask(text, resolved, store)
        counts = Counter(span.kind for span in resolved)
        _log.info("Pipeline.run: done, counts=%s", dict(counts))
        return AnonymizationResult(masked_text=masked, spans=resolved, counts=counts)


def anonymize(
    text: str,
    store: MappingStore,
    *,
    use_ner: bool = True,
    ner_detector: NatashaDetector | None = None,
) -> AnonymizationResult:
    return Pipeline.default(use_ner=use_ner, ner_detector=ner_detector).run(text, store)
