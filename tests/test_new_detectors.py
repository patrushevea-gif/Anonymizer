"""Tests for the new Iter 3 detectors: IP/URL/IBAN/BIC/plates/licence/OMS/positions."""
from anonymizer.core.detectors.regex_detector import RegexDetector
from anonymizer.core.entities import EntityKind


def _kinds_in(text: str) -> set[EntityKind]:
    return {s.kind for s in RegexDetector().find(text)}


def test_ip_detection() -> None:
    kinds = _kinds_in("Сервер отвечает на 192.168.1.100 и 10.0.0.1.")
    assert EntityKind.IP in kinds


def test_ip_rejects_invalid_octets() -> None:
    # 999.999.999.999 must NOT be detected.
    spans = RegexDetector().find("Неверный: 999.999.999.999")
    assert not any(s.kind is EntityKind.IP for s in spans)


def test_url_detection() -> None:
    kinds = _kinds_in("Документация на https://docs.example.com/page, спасибо.")
    assert EntityKind.URL in kinds


def test_iban_detection() -> None:
    # DE89370400440532013000 is a published textbook IBAN.
    kinds = _kinds_in("IBAN: DE89 3704 0044 0532 0130 00")
    assert EntityKind.IBAN in kinds


def test_bic_detection() -> None:
    kinds = _kinds_in("Расчётный БИК 044525225 Сбербанка")
    assert EntityKind.BIC in kinds


def test_car_plate_detection() -> None:
    kinds = _kinds_in("Автомобиль А123ВС77 выехал утром")
    assert EntityKind.CAR_PLATE in kinds


def test_driver_license_detection() -> None:
    kinds = _kinds_in("Водительское удостоверение 12 АВ 345678")
    assert EntityKind.DRIVER_LICENSE in kinds


def test_position_detection() -> None:
    from anonymizer.core.detectors.position_detector import PositionDetector

    spans = PositionDetector().find(
        "Генеральный директор подписал. Главный бухгалтер согласовала."
    )
    kinds = {s.kind for s in spans}
    assert EntityKind.POSITION in kinds
    assert len(spans) >= 2
