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
# Receives (full_text, start, end) of the match; False drops the match.
ContextCheck = Callable[[str, int, int], bool]


@dataclass(frozen=True)
class RegexRule:
    kind: EntityKind
    pattern: re.Pattern[str]
    priority: int
    validator: Validator | None = None
    normalizer: Normalizer | None = None
    context: ContextCheck | None = None


_RUSSIAN_PHONE = re.compile(
    r"(?<![\d+])(?:\+7|8)[ \u00a0\-]?\(?\d{3}\)?[ \u00a0\-]?\d{3}[ \u00a0\-]?\d{2}[ \u00a0\-]?\d{2}(?!\d)"
)

# Local number with an area code in parentheses: (495) 123-45-67, (3412) 12-34-56.
_LOCAL_PHONE = re.compile(
    r"(?<![\d)])(?<!\d[ \u00a0\-])(?<!\+7)\(\d{3,5}\)[ \u00a0]?\d{1,3}[ \u00a0\-]?\d{2}[ \u00a0\-]?\d{2}(?!\d)"
)

# Any other international number: +375 29 123-45-67, +49 30 1234567.
_INTL_PHONE = re.compile(
    r"(?<![\d+])\+(?!7[ \u00a0\-]?\(?\d{3})\d{1,3}(?:[ \u00a0\-]?\(?\d{1,5}\)?){2,5}(?!\d)"
)

_EMAIL = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)

_INN = re.compile(r"(?<!\d)\d{10}(?!\d)|(?<!\d)\d{12}(?!\d)")

_SNILS = re.compile(r"(?<!\d)\d{3}[\- ]\d{3}[\- ]\d{3}[\- ]\d{2}(?!\d)|(?<!\d)\d{11}(?!\d)")

_OGRN = re.compile(r"(?<!\d)\d{13}(?!\d)|(?<!\d)\d{15}(?!\d)")

_KPP = re.compile(r"(?<![\dA-Z])\d{4}[A-Z0-9]{2}\d{3}(?![\dA-Z])")

_PASSPORT_RF = re.compile(r"(?<!\d)\d{2}\s?\d{2}\s\d{6}(?!\d)")

_CARD = re.compile(r"(?<!\d)(?:\d{4}[\s\-]?){3}\d{4}(?!\d)|(?<!\d)\d{16}(?!\d)")

_ACCOUNT = re.compile(r"(?<!\d)\d{20}(?!\d)")

_DOB = re.compile(
    r"(?<!\d)(?:0?[1-9]|[12]\d|3[01])[./\-](?:0?[1-9]|1[0-2])[./\-](?:19|20)\d{2}(?!\d)"
    r"|(?<![А-ЯЁа-яё\d])(?:0?[1-9]|[12]\d|3[01])\s+"
    r"(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)"
    r"\s+(?:19|20)\d{2}(?:\s*г(?:ода|\.)?)?(?![А-ЯЁа-яё\d])"
    r"|(?<![\d.])(?:19|20)\d{2}\s*г\.\s?р\.",
    re.IGNORECASE,
)

# IPv4 — four octets 0-255.
_IP = re.compile(
    r"(?<![\d.])"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)){3}"
    r"(?![\d.])"
)

# Bare domain names without a scheme: www.example.ru, rossilber.рф, mail.company.com.
_DOMAIN = re.compile(
    r"(?<![\w@.\-/])(?:www\.)?(?:[A-Za-z0-9\u0430-\u044f\u0451](?:[A-Za-z0-9\u0430-\u044f\u0451\-]{0,61}[A-Za-z0-9\u0430-\u044f\u0451])?\.)+"
    r"(?:ru|su|рф|com|org|net|info|biz|io|me|pro|online|site|tech|dev|app|ai|cloud|ua|by|kz|uz|de|uk|eu|us|cn|moscow|spb)"
    r"(?![\w\-]|\.[A-Za-z0-9])",
    re.IGNORECASE,
)

# URL with scheme. We intentionally keep this conservative to avoid matching
# everything that contains a dot.
_URL = re.compile(
    r"(?<![A-Za-z])(?:https?|ftp)://(?:[^\s/@<>\"]+@)?[A-Za-z0-9\u0430-\u044f\u0451\u0410-\u042f\u0401.\-]+(?::\d+)?"
    r"(?:[/?#][^\s<>\"«»]*[^\s<>\"«».,;:!?)\]])?",
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

# API tokens from well-known services. Each alternative is anchored with a
# fixed prefix to drastically cut false positives.
_API_KEY = re.compile(
    r"(?:"
    # OpenAI classic + project keys
    r"sk-(?:proj-)?[A-Za-z0-9_\-]{20,}"
    # Anthropic
    r"|sk-ant-(?:api|sid|adm)[0-9]{2}-[A-Za-z0-9_\-]{20,}"
    # GitHub: PAT, OAuth, server, user, refresh, fine-grained
    r"|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|github_pat_[A-Za-z0-9_]{70,}"
    # AWS access key id + secret
    r"|AKIA[0-9A-Z]{16}"
    r"|ASIA[0-9A-Z]{16}"
    # Google API
    r"|AIza[0-9A-Za-z_\-]{35}"
    # Slack
    r"|xox[abpsr]-[A-Za-z0-9\-]{10,}"
    # Stripe
    r"|(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{20,}"
    # Yandex
    r"|y[0-9]_[A-Za-z0-9_\-]{40,}"
    # Telegram bot token
    r"|\d{8,12}:[A-Za-z0-9_\-]{30,}"
    # JSON Web Token
    r"|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"
    # PEM private keys (whole block)
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"
    # Generic prefixed secrets: sk-…, pk-…, rk-… with enough entropy
    r"|(?<![A-Za-z0-9])(?:sk|pk|rk)-[A-Za-z0-9][A-Za-z0-9_\-]{15,}"
    r")",
)

# Chemical formulas like H2O, H₂SO₄, C6H12O6, Na2SO4, (NH4)2SO4, K[Fe(CN)6],
# CuSO₄·5H₂O. The whole formula — subscripts, groups and the hydrate part —
# is one entity: partial matches would leave meaningless fragments behind.
_ELEMENT = r"(?:He|Li|Be|Ne|Na|Mg|Al|Si|Cl|Ar|Ca|Sc|Ti|Cr|Mn|Fe|Co|Ni|Cu|Zn|Ga|Ge|As|Se|Br|Kr|Rb|Sr|Zr|Nb|Mo|Tc|Ru|Rh|Pd|Ag|Cd|In|Sn|Sb|Te|Xe|Cs|Ba|La|Ce|Pr|Nd|Pm|Sm|Eu|Gd|Tb|Dy|Ho|Er|Tm|Yb|Lu|Hf|Ta|Re|Os|Ir|Pt|Au|Hg|Tl|Pb|Bi|Po|At|Rn|Fr|Ra|Ac|Th|Pa|Np|Pu|Am|Cm|Bk|Cf|Es|Fm|Md|No|Lr|H|B|C|N|O|F|P|S|K|V|Y|I|W|U)"
_SUB = r"(?:\d+|[₀-₉]+)"
_ATOM = rf"{_ELEMENT}{_SUB}?"
_GROUP = rf"(?:{_ATOM}|\((?:{_ATOM})+\){_SUB}?|\[(?:{_ATOM}|\((?:{_ATOM})+\){_SUB}?)+\]{_SUB}?)"
_FORMULA = re.compile(
    rf"(?<![A-Za-z0-9_₀-₉])"
    rf"(?:{_GROUP}){{2,}}"
    rf"(?:[·•∙⋅*]\s?(?:\d+|[₀-₉]+)?(?:{_GROUP})+)*"
    rf"(?![A-Za-z0-9_₀-₉])"
)
# Common formulas that consist only of single-letter elements without digits.
_FORMULA_UPPER_OK = frozenset({"KOH", "HCN", "KCN", "HF", "HI", "KI", "KF", "NaOH"})
# Abbreviations that happen to parse as element sequences.
_FORMULA_DENY = frozenset({"SPb", "NaN"})


def _formula_ok(value: str) -> bool:
    """Reject abbreviations (IP, CO, NO, SPB…) that merely look like formulas."""
    core = value.replace(" ", "")
    if core in _FORMULA_DENY:
        return False
    if any(ch.isdigit() or "₀" <= ch <= "₉" for ch in core):
        return True
    if any(ch.islower() for ch in core):
        return True
    return core in _FORMULA_UPPER_OK


# A minimal dictionary of chemical substances — both lab reagents and a few
# common controlled precursors that typically appear in protected research.
# Matched as whole words, case-insensitive.
_CHEMICAL_TERMS = (
    "ацетон", "ацетонитрил", "метанол", "этанол", "изопропанол", "пропанол",
    "гексан", "пентан", "бензол", "толуол", "ксилол", "хлороформ",
    "дихлорметан", "диэтиловый эфир", "этилацетат", "уксусная кислота",
    "серная кислота", "соляная кислота", "азотная кислота", "плавиковая кислота",
    "фосфорная кислота", "перхлорная кислота",
    "гидроксид натрия", "гидроксид калия", "аммиак",
    "перекись водорода", "пероксид водорода",
    "нитрат серебра", "нитрат аммония", "сульфат меди", "хлорид натрия",
    "йодистый калий", "бромистый калий", "перманганат калия",
    "дихромат калия", "тиосульфат натрия",
    "формальдегид", "глицерин", "фенол", "анилин", "пиридин", "диоксан",
    "дмсо", "диметилсульфоксид", "диметилформамид", "дмф",
    "тетрагидрофуран", "тгф",
    "натрий боргидрид", "литий алюмогидрид",
    "palladium", "платина", "родий", "иридий", "осмий",
)


def _build_chemical_re() -> re.Pattern[str]:
    terms = sorted(_CHEMICAL_TERMS, key=len, reverse=True)
    alt = "|".join(re.escape(t) for t in terms)
    # Allow up to 3 trailing Cyrillic letters so we pick up Russian declensions
    # ("этанола", "этаноловый" → "этанолов"), but reject compound words that
    # extend further ("метанольный" has 4+ tail chars and must stay unmatched).
    # The alternation MUST live inside a non-capturing group, otherwise the
    # lookbehind/lookahead only apply to the first/last branch.
    return re.compile(
        rf"(?<![А-ЯЁа-яёA-Za-z])(?:{alt})[а-яё]{{0,3}}(?![А-ЯЁа-яёA-Za-z])",
        re.IGNORECASE,
    )


_CHEMICAL = _build_chemical_re()


def _bic_context(text: str, start: int, end: int) -> bool:
    return not _label_before(text, start, "КПП")


def _kpp_context(text: str, start: int, end: int) -> bool:
    if _label_before(text, start, "БИК"):
        return False
    value = text[start:end]
    # A bare 9-digit number that is a valid Russian BIK is a BIK, not a KPP,
    # unless it is explicitly labelled as КПП.
    return not (value.isdigit() and bic_ok(value) and not _label_before(text, start, "КПП"))


def _label_before(text: str, start: int, label: str, window: int = 16) -> bool:
    before = text[max(0, start - window):start]
    return re.search(rf"(?<![А-ЯЁа-яё]){label}(?![А-ЯЁа-яё])", before, re.IGNORECASE) is not None


def _dob_context(text: str, start: int, end: int) -> bool:
    from anonymizer.core.detectors.context_detector import has_birth_context

    if text[start:end].lower().rstrip().endswith("р."):
        return True
    return has_birth_context(text, start, end)


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
    RegexRule(EntityKind.URL, _DOMAIN, priority=26, normalizer=_normalize_url),
    RegexRule(EntityKind.EMAIL, _EMAIL, priority=90, normalizer=_normalize_email),
    RegexRule(EntityKind.PHONE, _RUSSIAN_PHONE, priority=80, normalizer=_normalize_phone),
    RegexRule(EntityKind.PHONE, _LOCAL_PHONE, priority=79, normalizer=_normalize_phone),
    RegexRule(
        EntityKind.PHONE, _INTL_PHONE, priority=78,
        validator=lambda v: 9 <= len(digits_only(v)) <= 15,
        normalizer=_normalize_phone,
    ),
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
    RegexRule(EntityKind.KPP, _KPP, priority=47, normalizer=_normalize_digits, context=_kpp_context),
    RegexRule(
        EntityKind.BIC, _BIC, priority=46,
        validator=lambda v: bic_ok(digits_only(v)),
        normalizer=_normalize_digits,
        context=_bic_context,
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
    # Dates are masked as ДАТАРОЖД only when labelled as a birth date —
    # contract dates and deadlines must survive untouched.
    RegexRule(
        EntityKind.DOB, _DOB, priority=30,
        normalizer=lambda v: " ".join(v.lower().split()),
        context=_dob_context,
    ),
    RegexRule(EntityKind.IP, _IP, priority=25, normalizer=_normalize_ip),
    # Top priority — API keys look too much like phone numbers / accounts if
    # found after those; anchor them first.
    RegexRule(EntityKind.API_KEY, _API_KEY, priority=98),
    RegexRule(EntityKind.FORMULA, _FORMULA, priority=22, validator=_formula_ok),
    RegexRule(EntityKind.CHEMICAL, _CHEMICAL, priority=20, normalizer=lambda v: v.lower()),
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
                if rule.context is not None and not rule.context(
                    text, match.start(), match.end()
                ):
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
