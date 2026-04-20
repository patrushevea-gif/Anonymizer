from anonymizer.core.detectors.regex_detector import RegexDetector
from anonymizer.core.entities import EntityKind


def _kinds(text: str) -> list[tuple[EntityKind, str]]:
    spans = RegexDetector().find(text)
    return [(s.kind, s.text) for s in spans]


def test_phone_detection() -> None:
    text = "Call +7 999 111-22-33 or 8 (495) 123 45 67 please."
    found = _kinds(text)
    phones = [t for k, t in found if k is EntityKind.PHONE]
    assert len(phones) == 2


def test_phone_normalization_consistent() -> None:
    detector = RegexDetector()
    a = detector.find("+7 999 111-22-33")[0]
    b = detector.find("8 999 111 22 33")[0]
    assert a.normalized_key == b.normalized_key


def test_email_case_insensitive_key() -> None:
    detector = RegexDetector()
    [span_upper] = detector.find("Contact: IVAN@Example.COM")
    [span_lower] = detector.find("contact: ivan@example.com")
    assert span_upper.normalized_key == span_lower.normalized_key


def test_inn_valid_vs_invalid() -> None:
    found = _kinds("Real ИНН 7707083893 and fake 1234567890.")
    inns = [t for k, t in found if k is EntityKind.INN]
    assert inns == ["7707083893"]


def test_snils_detection() -> None:
    found = _kinds("СНИЛС 112-233-445 95")
    assert any(k is EntityKind.SNILS for k, _ in found)


def test_card_luhn_filters_garbage() -> None:
    found = _kinds("Card 4111 1111 1111 1111, garbage 1234 5678 9012 3456.")
    cards = [t for k, t in found if k is EntityKind.CARD]
    assert cards == ["4111 1111 1111 1111"]


def test_ogrn_detection() -> None:
    found = _kinds("ОГРН 1027700132195, ОГРНИП 304500116000157.")
    ogrn = [t for k, t in found if k is EntityKind.OGRN]
    assert set(ogrn) == {"1027700132195", "304500116000157"}


def test_dob_detection() -> None:
    found = _kinds("Дата рождения 01.02.1990, также 15/07/1985.")
    dobs = [t for k, t in found if k is EntityKind.DOB]
    assert len(dobs) == 2


def test_passport_detection() -> None:
    found = _kinds("Паспорт 45 11 123456 выдан отделом.")
    passports = [t for k, t in found if k is EntityKind.PASSPORT]
    assert passports == ["45 11 123456"]
