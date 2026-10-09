"""Label-driven detector: «ИНН: …», «р/с …», «паспорт серия … № …», «пароль: …».

Format-only detectors validate checksums to avoid false positives on random
numbers, which means a mistyped INN or an unusual account number would slip
through. When the value is explicitly labelled, the label is the proof: the
value is masked and classified by the label even if its checksum fails.
The label itself stays in the text so the AI still understands the context.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from anonymizer.core.detectors.validators import digits_only
from anonymizer.core.entities import EntityKind, EntitySpan

CONTEXT_PRIORITY = 85

_SEP = r"[\s:№#\-–—=]*"


@dataclass(frozen=True)
class _LabelRule:
    kind: EntityKind
    pattern: re.Pattern[str]
    normalizer: Callable[[str], str]
    digits: tuple[int, ...] = ()


def _lbl(label: str, value: str, sep: str = _SEP) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![А-ЯЁа-яёA-Za-z])(?:{label}){sep}(?P<v>{value})",
        re.IGNORECASE,
    )


def _phone_norm(v: str) -> str:
    d = digits_only(v)
    if len(d) == 11 and d.startswith("8"):
        d = "7" + d[1:]
    return "+" + d


def _compact(v: str) -> str:
    return re.sub(r"[\s\-]", "", v).upper()


_RULES: tuple[_LabelRule, ...] = (
    _LabelRule(EntityKind.INN, _lbl(r"ИНН", r"\d{10}(?:\d{2})?(?!\d)"), digits_only),
    _LabelRule(EntityKind.KPP, _lbl(r"КПП", r"\d{4}[\dA-Z]{2}\d{3}(?!\d)"), digits_only),
    _LabelRule(EntityKind.OGRN, _lbl(r"ОГРНИП|ОГРН", r"\d{13}(?:\d{2})?(?!\d)"), digits_only),
    _LabelRule(EntityKind.BIC, _lbl(r"БИК", r"\d{9}(?!\d)"), digits_only),
    _LabelRule(
        EntityKind.ACCOUNT,
        _lbl(
            r"р\s?/\s?с(?:ч)?\.?|к\s?/\s?с(?:ч)?\.?|расч[её]тн\w*\s+сч[её]т\w*|корр?\.?\s*сч[её]т\w*"
            r"|корреспондентск\w*\s+сч[её]т\w*|лицев\w*\s+сч[её]т\w*|сч[её]т\w*",
            r"\d{5}[\s.]?\d{3}[\s.]?\d[\s.]?\d{4}[\s.]?\d{7}(?!\d)|\d{20}(?!\d)",
        ),
        digits_only,
    ),
    _LabelRule(
        EntityKind.SNILS,
        _lbl(r"СНИЛС", r"\d{3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}(?!\d)"),
        digits_only,
    ),
    _LabelRule(
        EntityKind.PASSPORT,
        _lbl(
            r"паспорт\w*(?:\s+(?:РФ|гражданина\s+(?:РФ|Российской\s+Федерации)))?(?:\s+серии|\s+серия|\s+сер\.)?",
            r"\d{2}\s?\d{2}(?:\s*(?:№|номер|N|н\.)\s*|\s+)\d{6}(?!\d)",
        ),
        digits_only,
    ),
    _LabelRule(
        EntityKind.OMS,
        _lbl(r"(?:полис\w*\s+)?ОМС|полис\w*", r"\d{4}\s?\d{4}\s?\d{4}\s?\d{4}(?!\d)"),
        digits_only,
    ),
    _LabelRule(
        EntityKind.DRIVER_LICENSE,
        _lbl(
            r"водительск\w*\s+удостоверени\w*|в/у|ВУ",
            r"\d{2}\s?[\dА-ЯA-Z]{2}\s?\d{6}(?!\d)",
        ),
        _compact,
    ),
    _LabelRule(
        EntityKind.PHONE,
        _lbl(
            r"тел\.?|телефон\w*|моб\.?|мобильн\w*|факс|whatsapp|telegram|viber|phone|tel\.?",
            r"\+?\d[\d\s\-().]{5,18}\d(?!\d)",
        ),
        _phone_norm,
    ),
    _LabelRule(
        EntityKind.API_KEY,
        _lbl(
            r"парол\w*|password|passwd|pwd|pin-?код|пин-?код|token|токен\w*|secret|секрет\w*"
            r"|api[\s_-]?key|ключ\w*\s+api|ключ\w*\s+доступа|access[\s_-]?key|client[\s_-]?secret",
            r"[^\s,;\"'«»<>]{6,}",
            # Secrets need an explicit «:» or «=» — «токен доступа» is prose.
            sep=r"\s*[:=]\s*",
        ),
        lambda v: v,
    ),
)

_BIRTH_LABEL = re.compile(
    r"(?:дат\w*\s+рожд\w*|д\.\s?р\.|рожд[её]н\w*|родил\w*|г\.\s?р\.|год\w*\s+рожд\w*|DOB|date\s+of\s+birth|born)",
    re.IGNORECASE,
)


class ContextDetector:
    def find(self, text: str) -> list[EntitySpan]:
        spans: list[EntitySpan] = []
        for rule in _RULES:
            for m in rule.pattern.finditer(text):
                value = m.group("v").rstrip(".,;:)")
                if not value:
                    continue
                if rule.kind is EntityKind.PHONE and len(digits_only(value)) < 6:
                    continue
                if rule.kind is EntityKind.API_KEY and not re.search(r"[\dA-Za-z]", value):
                    continue
                start = m.start("v")
                spans.append(
                    EntitySpan(
                        kind=rule.kind,
                        start=start,
                        end=start + len(value),
                        text=value,
                        normalized_key=rule.normalizer(value),
                        priority=CONTEXT_PRIORITY,
                    )
                )
        return spans


def has_birth_context(text: str, start: int, end: int) -> bool:
    """True when a date at ``text[start:end]`` is labelled as a birth date."""
    before = text[max(0, start - 60):start]
    after = text[end:end + 12]
    line_before = before.rsplit("\n", 1)[-1]
    return bool(_BIRTH_LABEL.search(line_before)) or bool(
        re.match(r"\s*(?:г\.?\s*)?(?:г\.\s?р\.|года\s+рождения|д\.\s?р\.)", after, re.IGNORECASE)
    )
