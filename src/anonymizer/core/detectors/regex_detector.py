import re
from collections.abc import Callable
from dataclasses import dataclass

from anonymizer.core.detectors.validators import (
    digits_only,
    inn_ok,
    luhn_ok,
    ogrn_ok,
    snils_ok,
)
from anonymizer.core.entities import EntityKind, EntitySpan

Validator = Callable[[str], bool]
Normalizer = Callable[[str], str]


@dataclass(frozen=True)
class RegexRule:
    kind: EntityKind
    pattern: re.Pattern[str]
    priority: int
    validator: Validator | None = None
    normalizer: Normalizer | None = None


_RUSSIAN_PHONE = re.compile(
    r"(?<!\d)(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"
)

_EMAIL = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)

_INN = re.compile(r"(?<!\d)\d{10}(?!\d)|(?<!\d)\d{12}(?!\d)")

_SNILS = re.compile(r"(?<!\d)\d{3}[\- ]\d{3}[\- ]\d{3}[\- ]\d{2}(?!\d)|(?<!\d)\d{11}(?!\d)")

_OGRN = re.compile(r"(?<!\d)\d{13}(?!\d)|(?<!\d)\d{15}(?!\d)")

_KPP = re.compile(r"(?<!\d)\d{4}[A-Z0-9]{2}\d{3}(?!\d)")

_PASSPORT_RF = re.compile(r"(?<!\d)\d{2}\s?\d{2}\s\d{6}(?!\d)")

_CARD = re.compile(r"(?<!\d)(?:\d{4}[\s\-]?){3}\d{4}(?!\d)|(?<!\d)\d{16}(?!\d)")

_ACCOUNT = re.compile(r"(?<!\d)\d{20}(?!\d)")

_DOB = re.compile(r"(?<!\d)(0?[1-9]|[12]\d|3[01])[./](0?[1-9]|1[0-2])[./](19|20)\d{2}(?!\d)")


def _normalize_phone(text: str) -> str:
    digits = digits_only(text)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    return "+" + digits


def _normalize_digits(text: str) -> str:
    return digits_only(text)


def _normalize_email(text: str) -> str:
    return text.lower()


DEFAULT_RULES: tuple[RegexRule, ...] = (
    RegexRule(EntityKind.EMAIL, _EMAIL, priority=90, normalizer=_normalize_email),
    RegexRule(EntityKind.PHONE, _RUSSIAN_PHONE, priority=80, normalizer=_normalize_phone),
    RegexRule(EntityKind.ACCOUNT, _ACCOUNT, priority=70, normalizer=_normalize_digits),
    RegexRule(
        EntityKind.OGRN, _OGRN, priority=65,
        validator=lambda v: ogrn_ok(digits_only(v)),
        normalizer=_normalize_digits,
    ),
    RegexRule(
        EntityKind.CARD, _CARD, priority=60,
        validator=lambda v: luhn_ok(digits_only(v)),
        normalizer=_normalize_digits,
    ),
    RegexRule(
        EntityKind.SNILS, _SNILS, priority=55,
        validator=lambda v: snils_ok(v),
        normalizer=_normalize_digits,
    ),
    RegexRule(
        EntityKind.INN, _INN, priority=50,
        validator=lambda v: inn_ok(digits_only(v)),
        normalizer=_normalize_digits,
    ),
    RegexRule(EntityKind.KPP, _KPP, priority=45, normalizer=_normalize_digits),
    RegexRule(EntityKind.PASSPORT, _PASSPORT_RF, priority=40, normalizer=_normalize_digits),
    RegexRule(EntityKind.DOB, _DOB, priority=30),
)


class RegexDetector:
    def __init__(self, rules: tuple[RegexRule, ...] = DEFAULT_RULES) -> None:
        self._rules = rules

    def find(self, text: str) -> list[EntitySpan]:
        spans: list[EntitySpan] = []
        for rule in self._rules:
            for match in rule.pattern.finditer(text):
                matched = match.group()
                if rule.validator is not None and not rule.validator(matched):
                    continue
                spans.append(
                    EntitySpan(
                        kind=rule.kind,
                        start=match.start(),
                        end=match.end(),
                        text=matched,
                        normalized_key=rule.normalizer(matched) if rule.normalizer else None,
                        priority=rule.priority,
                    )
                )
        return spans
