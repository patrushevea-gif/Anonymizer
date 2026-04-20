import pytest

from anonymizer.core.detectors.validators import inn_ok, luhn_ok, ogrn_ok, snils_ok


@pytest.mark.parametrize(
    "card,ok",
    [
        ("4111111111111111", True),
        ("4242424242424242", True),
        ("5555555555554444", True),
        ("4111111111111112", False),
        ("1234567890123456", False),
        ("", False),
        ("abcd", False),
    ],
)
def test_luhn(card: str, ok: bool) -> None:
    assert luhn_ok(card) is ok


@pytest.mark.parametrize(
    "inn,ok",
    [
        ("7707083893", True),
        ("500100732259", True),
        ("7707083892", False),
        ("500100732250", False),
        ("12345", False),
    ],
)
def test_inn(inn: str, ok: bool) -> None:
    assert inn_ok(inn) is ok


@pytest.mark.parametrize(
    "snils,ok",
    [
        ("112-233-445 95", True),
        ("11223344595", True),
        ("112-233-445 96", False),
        ("112-233-445", False),
    ],
)
def test_snils(snils: str, ok: bool) -> None:
    assert snils_ok(snils) is ok


@pytest.mark.parametrize(
    "ogrn,ok",
    [
        ("1027700132195", True),
        ("304500116000157", True),
        ("1027700132196", False),
        ("304500116000158", False),
        ("12345", False),
    ],
)
def test_ogrn(ogrn: str, ok: bool) -> None:
    assert ogrn_ok(ogrn) is ok
