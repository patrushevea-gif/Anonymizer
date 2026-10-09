"""Web service layer: JSON-friendly wrappers around the anonymizer engine.

The web API is stateless: the alias table (``mapping``) is returned to the
browser and sent back with every follow-up request (re-masking after the
user unchecks an entity, DOCX export, restore). The server keeps no
documents and no personal data between requests, so it can run behind any
number of workers and nothing sensitive accumulates on disk or in memory.

All detection, DOCX processing, leak control and restore logic is the same
code the desktop application uses.
"""
from __future__ import annotations

import base64
import binascii
import threading
from collections import Counter
from pathlib import Path

from anonymizer.core.detectors.ner_detector import NatashaDetector
from anonymizer.core.entities import EntityKind, EntitySpan
from anonymizer.core.mapping import MappingStore
from anonymizer.core.masking import apply_mask
from anonymizer.core.pipeline import Pipeline
from anonymizer.core.postprocess import finalize_spans
from anonymizer.core.resolve import resolve_overlaps
from anonymizer.core.reverse import restore

SUPPORTED_UPLOADS = (".docx", ".txt", ".xlsx", ".pdf")


class ServiceError(ValueError):
    """Client error with a user-facing Russian message."""

    def __init__(self, message: str, status: int = 400, payload: dict | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload or {}


class AnonymizerService:
    def __init__(self, *, use_ner: bool = True) -> None:
        self.ner_available = use_ner and _natasha_installed()
        self._ner = NatashaDetector() if self.ner_available else None
        # Natasha models are not guaranteed to be thread-safe: detection runs
        # under one lock, everything else (I/O, DOCX export) runs in parallel.
        self._lock = threading.Lock()

    def preload(self) -> None:
        if self._ner is not None:
            self._ner.preload()

    # ------------------------------------------------------------ helpers
    def _pipeline(self, options: dict) -> Pipeline:
        use_ner = bool(options.get("use_ner", True)) and self.ner_available
        disabled = {k for k in options.get("disabled_kinds", []) if k in _KIND_VALUES}
        enabled = {k for k in EntityKind if k.value not in disabled}
        allowlist = [str(t) for t in options.get("allowlist", []) if str(t).strip()]
        return Pipeline.default(
            use_ner=use_ner,
            ner_detector=self._ner if use_ner else None,
            enabled_kinds=enabled,
            allowlist=allowlist,
        )

    def capabilities(self) -> dict:
        return {
            "ner": self.ner_available,
            "kinds": [k.value for k in EntityKind],
            "uploads": list(SUPPORTED_UPLOADS),
        }

    # ------------------------------------------------------------ text
    def anonymize(self, text: str, options: dict) -> dict:
        _require_text(text)
        store = MappingStore()
        pipeline = self._pipeline(options)
        with self._lock:
            result = pipeline.run(text, store)
        manual = _manual_spans(options.get("manual") or [], text)
        if not manual:
            return _result_payload(result.masked_text, result.spans, store)
        # Manual markings always win and, like detected values, are masked at
        # every occurrence (same behaviour as the desktop application).
        store = MappingStore()
        store.reserve_source_aliases(text)
        spans = finalize_spans(list(result.spans) + manual, text, pipeline.allowlist)
        enabled = pipeline.enabled_kinds or set(EntityKind)
        spans = [s for s in spans if s.kind in enabled or s.priority >= 999]
        return _result_payload(apply_mask(text, spans, store), spans, store)

    def remask(self, text: str, spans: list[dict], mapping: dict, disabled: list[str]) -> dict:
        """Re-render after the user unchecked entities (aliases in *disabled*)."""
        store = MappingStore.from_dict(mapping)
        all_spans = _spans_from_payload(spans, text)
        for alias in disabled:
            store.drop_alias(alias)
        alias_of = dict(store._key_to_alias)  # noqa: SLF001
        active = resolve_overlaps([s for s in all_spans if (s.kind, s.key) in alias_of])
        masked = apply_mask(text, active, store)
        return _result_payload(masked, active, store)

    def restore_text(self, text: str, mapping: dict) -> dict:
        store = MappingStore.from_dict(mapping)
        return {"text": restore(text, store)}

    # ------------------------------------------------------------ files
    def open_file(self, filename: str, data: bytes) -> dict:
        suffix = Path(filename or "").suffix.lower()
        if suffix not in SUPPORTED_UPLOADS:
            raise ServiceError(
                f"Формат «{suffix or 'без расширения'}» не поддерживается. "
                "Поддерживаются: " + ", ".join(SUPPORTED_UPLOADS)
            )
        if suffix == ".docx":
            from anonymizer.io.ooxml import DocxDocument

            try:
                doc = DocxDocument(data)
            except ValueError as exc:
                raise ServiceError(str(exc)) from exc
            except Exception as exc:
                raise ServiceError("Не удалось прочитать документ Word: файл повреждён") from exc
            return {"text": doc.text, "format": "docx"}
        import tempfile

        from anonymizer.io import read_text

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"upload{suffix}"
            path.write_bytes(data)
            try:
                text = read_text(path)
            except Exception as exc:
                raise ServiceError(f"Не удалось прочитать файл: {exc}") from exc
        return {"text": text, "format": suffix.lstrip(".")}

    def export_docx(self, data: bytes, spans: list[dict], mapping: dict) -> dict:
        from anonymizer.io.ooxml import DocxDocument

        doc = DocxDocument(data)
        store = MappingStore.from_dict(mapping)
        active = _spans_from_payload(spans, doc.text)
        out, report = doc.anonymize(active, store)
        report_payload = {
            "replaced": report.replaced,
            "parts_changed": report.parts_changed,
            "metadata_removed": report.metadata_removed,
            "leaks_fixed": [list(x) for x in report.leaks_fixed],
            "leaks": [list(x) for x in report.leaks],
            "warnings": report.warnings,
        }
        if report.leaks:
            raise ServiceError(
                "Контроль утечек не пройден: в файле остались исходные данные. "
                "Файл не выдан.",
                status=422,
                payload={"report": report_payload},
            )
        return {"file": _b64(out), "report": report_payload}

    def restore_docx(self, data: bytes, mapping: dict) -> dict:
        from anonymizer.io.ooxml import DocxDocument

        try:
            doc = DocxDocument(data)
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc
        out, count = doc.restore(MappingStore.from_dict(mapping))
        return {"file": _b64(out), "restored": count}


# ---------------------------------------------------------------- helpers
_KIND_VALUES = {k.value for k in EntityKind}


def _natasha_installed() -> bool:
    try:
        import natasha  # noqa: F401
    except ImportError:
        return False
    return True


def _require_text(text: str) -> None:
    if not isinstance(text, str) or not text.strip():
        raise ServiceError("Нет текста для обезличивания")


def _manual_spans(raw: list, text: str) -> list[EntitySpan]:
    out: list[EntitySpan] = []
    for item in raw:
        try:
            kind = EntityKind(item["kind"])
            start, end = int(item["start"]), int(item["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ServiceError("Некорректная ручная разметка") from exc
        if not (0 <= start < end <= len(text)) or not text[start:end].strip():
            raise ServiceError("Ручная разметка не совпадает с текстом. Пометьте фрагмент заново.")
        surface = text[start:end]
        out.append(EntitySpan(kind, start, end, surface, surface.lower().strip(), priority=1000))
    return out


def _result_payload(masked: str, spans: list[EntitySpan], store: MappingStore) -> dict:
    alias_of = store._key_to_alias  # noqa: SLF001
    return {
        "masked_text": masked,
        "spans": [
            {
                "kind": s.kind.value,
                "start": s.start,
                "end": s.end,
                "text": s.text,
                "key": s.key,
                "priority": s.priority,
                "alias": alias_of.get((s.kind, s.key)),
            }
            for s in spans
        ],
        "counts": dict(Counter(s.kind.value for s in spans)),
        "mapping": store.to_dict(),
    }


def _spans_from_payload(spans: list[dict], text: str) -> list[EntitySpan]:
    out: list[EntitySpan] = []
    for raw in spans:
        try:
            kind = EntityKind(raw["kind"])
            start, end = int(raw["start"]), int(raw["end"])
            surface = str(raw["text"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ServiceError("Некорректный список сущностей") from exc
        if not (0 <= start < end <= len(text)) or text[start:end] != surface:
            raise ServiceError(
                "Позиции сущностей не совпадают с текстом документа. "
                "Повторите обезличивание."
            )
        out.append(
            EntitySpan(
                kind=kind, start=start, end=end, text=surface,
                normalized_key=str(raw.get("key", surface)),
                priority=int(raw.get("priority", 0)),
            )
        )
    return out


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def decode_file(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise ServiceError("Файл передан в неверном формате") from exc
