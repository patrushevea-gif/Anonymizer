import re
from collections.abc import Callable
from dataclasses import dataclass

from anonymizer.core.detectors.validators import (
    bic_ok,
    digits_only,
    driver_license_ok,
    iban_ok,
    inn_ok,
    luhn_ok,
    ogrn_ok,
    oms_ok,
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

# IPv4 — four octets 0-255.
_IP = re.compile(
    r"(?<![\d.])"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)){3}"
    r"(?![\d.])"
)

# URL with scheme. We intentionally keep this conservative to avoid matching
# everything that contains a dot.
_URL = re.compile(
    r"(?<![A-Za-z])https?://[A-Za-z0-9.\-]+(?::\d+)?(?:/[^\s<>\"]*)?",
    re.IGNORECASE,
)

# IBAN: 2 letters + 2 digits + up to 30 alphanum, optionally with spaces in groups of 4.
_IBAN = re.compile(
    r"(?<![A-Z0-9])[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){10,30}(?![A-Z0-9])",
    re.IGNORECASE,
)

# БИК — 9 digits starting with 04 (Russia).
_BIC = re.compile(r"(?<!\d)04\d{7}(?!\d)")

# Russian car plates (state registration).
#   A 123 AB 77  /  А123АВ77  / E001KX777
# Allowed letters: ABEKMHOPCTYX (both Latin and Cyrillic look-alikes).
_PLATE_LETTERS = "АВЕКМНОРСТУХABEKMHOPCTYX"
_CAR_PLATE = re.compile(
    rf"(?<![A-Za-z\u0400-\u04FF\d])"
    rf"[{_PLATE_LETTERS}]\s?\d{{3}}\s?[{_PLATE_LETTERS}]{{2}}\s?\d{{2,3}}"
    rf"(?![A-Za-z\u0400-\u04FF\d])"
)

# Russian driving licence: "12 34 567890" or "1234 567890".
_DRIVER_LICENSE = re.compile(
    r"(?<!\d)\d{2}[\s\-]?[0-9А-ЯA-Z]{2}[\s\-]?\d{6}(?!\d)"
)

# ОМС (полис обязательного медицинского страхования) — 16 digits.
_OMS = re.compile(r"(?<!\d)\d{16}(?!\d)")


def _normalize_url(text: str) -> str:
    return text.rstrip(".,;:)!?").lower()


def _normalize_ip(text: str) -> str:
    return text


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
    RegexRule(EntityKind.URL, _URL, priority=95, normalizer=_normalize_url),
    RegexRule(EntityKind.EMAIL, _EMAIL, priority=90, normalizer=_normalize_email),
    RegexRule(EntityKind.PHONE, _RUSSIAN_PHONE, priority=80, normalizer=_normalize_phone),
    RegexRule(
        EntityKind.IBAN, _IBAN, priority=75,
        validator=lambda v: iban_ok(v),
        normalizer=lambda v: v.replace(" ", "").upper(),
    ),
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
    RegexRule(EntityKind.KPP, _KPP, priority=47, normalizer=_normalize_digits),
    RegexRule(
        EntityKind.BIC, _BIC, priority=46,
        validator=lambda v: bic_ok(digits_only(v)),
        normalizer=_normalize_digits,
    ),
    RegexRule(EntityKind.PASSPORT, _PASSPORT_RF, priority=40, normalizer=_normalize_digits),
    RegexRule(
        EntityKind.OMS, _OMS, priority=38,
        validator=lambda v: oms_ok(v),
        normalizer=_normalize_digits,
    ),
    RegexRule(EntityKind.CAR_PLATE, _CAR_PLATE, priority=37, normalizer=lambda v: v.upper().replace(" ", "")),
    RegexRule(
        EntityKind.DRIVER_LICENSE, _DRIVER_LICENSE, priority=35,
        validator=lambda v: driver_license_ok(v),
        normalizer=lambda v: v.upper().replace(" ", "").replace("-", ""),
    ),
    RegexRule(EntityKind.DOB, _DOB, priority=30),
    RegexRule(EntityKind.IP, _IP, priority=25, normalizer=_normalize_ip),
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
