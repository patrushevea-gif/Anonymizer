"""Tests for Iter 4 detectors: API keys, chemical formulas and substances."""
from anonymizer.core.detectors.regex_detector import RegexDetector
from anonymizer.core.entities import EntityKind


def _kinds(text: str) -> list[tuple[EntityKind, str]]:
    return [(s.kind, s.text) for s in RegexDetector().find(text)]


def test_api_key_openai() -> None:
    found = _kinds(
        "Используйте ключ sk-proj-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOP для API."
    )
    assert any(k is EntityKind.API_KEY for k, _ in found)


def test_api_key_anthropic() -> None:
    found = _kinds(
        "Токен: sk-ant-api03-AbCdEfGhIjKlMnOpQrStUvWxYz1234567890"
    )
    assert any(k is EntityKind.API_KEY for k, _ in found)


def test_api_key_github_pat() -> None:
    found = _kinds("ghp_abcdefghijklmnopqrstuvwxyz0123456789")
    assert any(k is EntityKind.API_KEY for k, _ in found)


def test_api_key_aws() -> None:
    found = _kinds("AKIAIOSFODNN7EXAMPLE и секрет отдельно.")
    assert any(k is EntityKind.API_KEY and "AKIA" in t for k, t in found)


def test_api_key_stripe() -> None:
    # Obviously-fake fixture — GitHub push protection rejects anything
    # that resembles a real Stripe token, so we use a synthetic pattern.
    found = _kinds("sk_test_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
    assert any(k is EntityKind.API_KEY for k, _ in found)


def test_formula_water() -> None:
    found = _kinds("Взяли 50 мл H2O и добавили.")
    assert any(k is EntityKind.FORMULA and "H2O" in t for k, t in found)


def test_formula_glucose() -> None:
    found = _kinds("Раствор C6H12O6 приготовили заранее.")
    assert any(k is EntityKind.FORMULA and "C6H12O6" in t for k, t in found)


def test_formula_ignores_single_letters() -> None:
    # Sentences like "A B C" should NOT be picked up as formulas.
    found = _kinds("A B C отдельно — это аббревиатуры.")
    assert not any(k is EntityKind.FORMULA for k, _ in found)


def test_chemical_substance_ethanol() -> None:
    found = _kinds("Добавили 10 мл этанола в колбу.")
    assert any(k is EntityKind.CHEMICAL and "этанол" in t.lower() for k, t in found)


def test_chemical_substance_sulfuric_acid() -> None:
    found = _kinds("Концентрированная серная кислота используется осторожно.")
    assert any(k is EntityKind.CHEMICAL for k, _ in found)


def test_chemical_does_not_match_partial_word() -> None:
    # "Метанольный" should NOT match (it contains "метанол" but is a different word)
    found = _kinds("Метанольный раствор.")
    # No partial match — word boundary means "метанол" surrounded by Cyrillic fails
    matches = [t for k, t in found if k is EntityKind.CHEMICAL]
    assert all(m.lower() != "метанол" for m in matches)
